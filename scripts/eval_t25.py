"""Evaluasi T25: PhiUSIIL grouped test, CV, dan set dunia nyata dev/final.

Menambahkan bagian evaluation ke docs/t25.json dan menulis docs/t25.md.
Skor model mentah, tanpa allowlist/uncertainty band. Tidak ada URL di keluaran.
"""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import joblib
import numpy as np
from sklearn.metrics import roc_auc_score

from scripts.eval_realworld import load_rows, metrics, wilson_interval
from scripts.prepare_legit_user import host_type
from scripts.train_t25 import JSON_PATH, consensus_proba, phishing_proba
from src.config import LABEL_LEGIT, LABEL_PHISH, THRESHOLD
from src.feature_utils import to_frame
from src.features_host import host_of, to_host_frame
from src.reputation import is_trusted

ROOT = Path(__file__).resolve().parents[1]
DOC_PATH = ROOT / "docs" / "t25.md"
DEFAULT_TLD_OLD = ROOT / "models" / "experimental" / "tld_probs_host_prev.json"
DEFAULT_TLD_NEW = ROOT / "models" / "experimental" / "tld_probs_host.json"
B_REFIT_PATH = ROOT / "models" / "experimental" / "B_refit.pkl"
C_HOST_PATH = ROOT / "models" / "experimental" / "C_host.pkl"
OPENPHISH_PATH = ROOT / "data" / "realworld" / "urls.csv"
LEGIT_DEV = ROOT / "data" / "realworld" / "legit_dev.csv"
LEGIT_FINAL = ROOT / "data" / "realworld" / "legit_final.csv"


def load_tld(path):
    return json.loads(path.read_text(encoding="utf-8"))


def score_block(y_true, proba):
    predicted = np.where(proba >= THRESHOLD, LABEL_PHISH, LABEL_LEGIT).astype(int)
    block = metrics(np.asarray(y_true, dtype=int).tolist(), predicted.tolist())
    block["roc_auc"] = round(float(roc_auc_score((np.asarray(y_true) == LABEL_PHISH).astype(int), proba)), 4)
    block["specificity_ci95"] = wilson_interval(block["tn"], block["tn"] + block["fp"])
    block["recall_ci95"] = wilson_interval(block["tp"], block["tp"] + block["fn"])
    return block


def consensus_block(y_true, p_b, p_c):
    verdict, predicted, susp_pct = consensus_proba(p_b, p_c)
    block = metrics(np.asarray(y_true, dtype=int).tolist(), predicted.tolist())
    block["roc_auc"] = None
    block["specificity_ci95"] = wilson_interval(block["tn"], block["tn"] + block["fp"])
    block["recall_ci95"] = wilson_interval(block["tp"], block["tp"] + block["fn"])
    block["suspicious_pct"] = susp_pct
    block["suspicious_n"] = int(np.sum(verdict == "SUSPICIOUS"))
    return block


def candidate_metrics(y_true, p_b, p_c):
    return {
        "B_refit": score_block(y_true, p_b),
        "C_host": score_block(y_true, p_c),
        "consensus": consensus_block(y_true, p_b, p_c),
    }


def group_candidate_metrics(y_true, p_b, p_c, mask):
    if mask.sum() == 0:
        return None
    return candidate_metrics(y_true[mask], p_b[mask], p_c[mask])


def evaluate_set(urls, labels, in_allow, host_types):
    tld_old = load_tld(DEFAULT_TLD_OLD)
    tld_new = load_tld(DEFAULT_TLD_NEW)
    pipe_b = joblib.load(B_REFIT_PATH)
    pipe_c = joblib.load(C_HOST_PATH)
    p_b = phishing_proba(pipe_b, to_frame(urls, tld_old["map"], tld_old["default"]))
    p_c = phishing_proba(pipe_c, to_host_frame(urls, tld_new["map"], tld_new["default"], strip_www=True))
    y = np.asarray(labels, dtype=int)
    in_allow = np.asarray(in_allow, dtype=bool)
    host_types = np.asarray(host_types)
    groups = {
        "all": np.ones(len(urls), dtype=bool),
        "root": host_types == "root",
        "berpath": host_types == "berpath",
        "in_allowlist": in_allow,
        "not_in_allowlist": ~in_allow,
    }
    result = {
        "n": len(urls),
        "n_legit": int(np.sum(y == LABEL_LEGIT)),
        "n_phishing": int(np.sum(y == LABEL_PHISH)),
        "n_root": int(np.sum(host_types == "root")),
        "n_berpath": int(np.sum(host_types == "berpath")),
        "n_in_allowlist": int(in_allow.sum()),
        "n_not_in_allowlist": int((~in_allow).sum()),
        "groups": {},
    }
    for name, mask in groups.items():
        block = group_candidate_metrics(y, p_b, p_c, mask)
        if block is not None:
            result["groups"][name] = block
    return result


def build_openphish_split():
    rows = [r for r in load_rows(OPENPHISH_PATH) if int(r["label"]) == LABEL_PHISH]
    urls = [r["url"].strip() for r in rows]
    rng = np.random.default_rng(42)
    chosen = sorted(rng.choice(len(urls), size=len(urls) // 2, replace=False).tolist())
    chosen_set = set(chosen)
    dev_urls = [urls[i] for i in chosen]
    final_urls = [urls[i] for i in range(len(urls)) if i not in chosen_set]
    return dev_urls, final_urls


def t24a_aggregate():
    files = {
        "review": ROOT / "data" / "realworld" / "legit_review.csv",
        "dev": ROOT / "data" / "realworld" / "legit_dev.csv",
        "final": ROOT / "data" / "realworld" / "legit_final.csv",
    }
    missing = [name for name, path in files.items() if not path.exists()]
    if missing:
        return {"available": False, "missing": missing, "note": "Jalankan T24a untuk menghasilkan file ini."}

    def summarize(path):
        rows = load_rows(path)
        hosts = { (r.get("url") or "").split("/")[2] if "://" in (r.get("url") or "") else "" for r in rows }
        contributors = { (r.get("person_label") or "").strip() for r in rows if (r.get("person_label") or "").strip() }
        return {
            "rows": len(rows),
            "root": sum(host_type(r.get("url") or "") == "root" for r in rows),
            "berpath": sum(host_type(r.get("url") or "") == "berpath" for r in rows),
            "outside_allowlist": sum((r.get("in_allowlist") or "") == "0" for r in rows),
            "hosts": len(hosts - {""}),
            "contributors": len(contributors),
        }

    return {
        "available": True,
        "review": summarize(files["review"]),
        "dev": summarize(files["dev"]),
        "final": summarize(files["final"]),
    }


def _fmt(value):
    return "—" if value is None else str(value)


def _ci(interval):
    if not interval:
        return "—"
    return f"{interval['low']}–{interval['high']}"


def render_markdown(payload):
    train = payload["train"]
    lines = [
        "# T25 — pemilihan kandidat Model B vs host-only",
        "",
        f"Dihasilkan {payload['generated_at']} (dievaluasi {payload['evaluated_at']}). "
        "Semua angka berasal dari skrip; tidak ada angka manual.",
        "",
        "## Ringkasan pemilihan",
        "",
        f"Protokol: `{payload['protocol']}`. Kandidat dipilih hanya dari CV train, test "
        f"PhiUSIIL berkelompok, dan set dev. Rekomendasi: **`{payload['selection']['selected']}`** "
        f"({payload['selection']['criterion']}).",
        "",
        "## Efek normalisasi www. pada C_host",
        "",
        "| Varian C_host | Test F1 | Test MCC | Test ROC-AUC |",
        "|---|---|---|---|",
        f"| T24 (tanpa normalisasi) | {_fmt(train['www_normalization_effect']['old_c_host']['f1'])} | "
        f"{_fmt(train['www_normalization_effect']['old_c_host']['mcc'])} | "
        f"{_fmt(train['www_normalization_effect']['old_c_host']['roc_auc'])} |",
        f"| T25 (normalisasi www.) | {_fmt(train['www_normalization_effect']['new_c_host']['f1'])} | "
        f"{_fmt(train['www_normalization_effect']['new_c_host']['mcc'])} | "
        f"{_fmt(train['www_normalization_effect']['new_c_host']['roc_auc'])} |",
        "",
        "## PhiUSIIL grouped test",
        "",
        "| Kandidat | Precision | Recall | F1 | MCC | ROC-AUC | TP | FP | FN | TN | Suspicious % |",
        "|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    test = train["test_grouped"]
    for name in ("B_refit", "C_host", "consensus"):
        block = test[name]
        lines.append(
            f"| `{name}` | {_fmt(block.get('precision'))} | {_fmt(block.get('recall'))} | "
            f"{_fmt(block.get('f1'))} | {_fmt(block.get('mcc'))} | {_fmt(block.get('roc_auc'))} | "
            f"{block.get('tp', '—')} | {block.get('fp', '—')} | {block.get('fn', '—')} | "
            f"{block.get('tn', '—')} | {_fmt(block.get('suspicious_pct'))} |"
        )
    lines += [
        "",
        "## CV train berkelompok (5 fold)",
        "",
        "| Kandidat | F1/MCC/ROC-AUC mean | Suspicious % mean |",
        "|---|---|---|",
    ]
    cv = train["cv_grouped"]
    for name in ("B_refit", "C_host", "consensus"):
        block = cv[name]
        if name == "consensus":
            lines.append(f"| `{name}` | MCC {block['mcc_mean']} | {block['suspicious_pct_mean']} |")
        else:
            lines.append(
                f"| `{name}` | F1 {block['f1_phishing_mean']}, MCC {block['mcc_mean']}, "
                f"ROC-AUC {block['roc_auc_mean']} | — |"
            )
    lines += [
        "",
        "## Set dunia nyata",
        "",
    ]
    realworld = payload["evaluation"].get("realworld", {})
    if not realworld.get("available"):
        lines += [f"- Tidak tersedia: {realworld.get('reason', 'file T24a belum ada')}.", ""]
    else:
        for split_name in ("dev", "final"):
            split_data = realworld[split_name]
            lines += [
                f"### {split_name}",
                "",
                f"{split_data['n']} URL ({split_data['n_legit']} legit, {split_data['n_phishing']} phishing; "
                f"{split_data['n_root']} root, {split_data['n_berpath']} berpath; "
                f"{split_data['n_in_allowlist']} in allowlist, {split_data['n_not_in_allowlist']} not).",
                "",
                "| Kandidat | Precision | Recall (95% CI) | F1 | MCC | Specificity (95% CI) | Suspicious % |",
                "|---|---|---|---|---|---|---|",
            ]
            for name in ("B_refit", "C_host", "consensus"):
                block = split_data["candidates"][name]["all"]
                lines.append(
                    f"| `{name}` | {_fmt(block['precision'])} | {_fmt(block['recall'])} "
                    f"({_ci(block['recall_ci95'])}) | {_fmt(block['f1'])} | {_fmt(block['mcc'])} | "
                    f"{_fmt(block['specificity'])} ({_ci(block['specificity_ci95'])}) | "
                    f"{_fmt(block.get('suspicious_pct'))} |"
                )
            lines += [
                "",
                "Per kelompok (F1):",
                "",
                "| Kelompok | B_refit | C_host | Consensus |",
                "|---|---|---|---|",
            ]
            for group in ("root", "berpath", "in_allowlist", "not_in_allowlist"):
                if group in split_data["candidates"]["B_refit"]:
                    lines.append(
                        f"| {group} | {_fmt(split_data['candidates']['B_refit'][group]['f1'])} | "
                        f"{_fmt(split_data['candidates']['C_host'][group]['f1'])} | "
                        f"{_fmt(split_data['candidates']['consensus'][group]['f1'])} |"
                    )
            lines.append("")
    lines += [
        "## Agregat T24a",
        "",
    ]
    agg = payload.get("t24a_aggregate", {})
    if not agg.get("available"):
        lines += [f"- Belum tersedia: {agg.get('note', 'file T24a belum ada')}.", ""]
    else:
        for name in ("review", "dev", "final"):
            block = agg[name]
            lines += [
                f"- `{name}`: {block['rows']} URL ({block['root']} root, {block['berpath']} berpath; "
                f"{block['outside_allowlist']} di luar allowlist), {block['hosts']} host, "
                f"{block['contributors']} kontributor.",
            ]
        lines.append("")
    lines += [
        "## Batasan",
        "",
    ]
    lines += [f"- {item}" for item in payload["limitations"]]
    lines += [
        "",
        "## Perintah",
        "",
        "```powershell",
        "uv run python scripts/train_t25.py",
        "uv run python scripts/eval_t25.py",
        "uv run pytest -q",
        "```",
        "",
    ]
    return "\n".join(lines)


def main():
    if not JSON_PATH.exists():
        print("Jalankan scripts/train_t25.py dulu.")
        return 2
    payload = json.loads(JSON_PATH.read_text(encoding="utf-8"))
    payload["evaluated_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")

    # Real-world sets
    realworld = {"available": False}
    if LEGIT_DEV.exists() and LEGIT_FINAL.exists():
        dev_legit = load_rows(LEGIT_DEV)
        final_legit = load_rows(LEGIT_FINAL)
        dev_phish, final_phish = build_openphish_split()

        def make_set(legit_rows, phish_urls):
            urls = [r["url"].strip() for r in legit_rows] + list(phish_urls)
            labels = np.array([LABEL_LEGIT] * len(legit_rows) + [LABEL_PHISH] * len(phish_urls), dtype=int)
            in_allow = np.array([is_trusted(host_of(u)) for u in urls])
            types = np.array([host_type(u) for u in urls])
            return urls, labels, in_allow, types

        dev_urls, dev_labels, dev_allow, dev_types = make_set(dev_legit, dev_phish)
        final_urls, final_labels, final_allow, final_types = make_set(final_legit, final_phish)

        realworld = {
            "available": True,
            "dev": evaluate_set(dev_urls, dev_labels, dev_allow, dev_types),
            "final": evaluate_set(final_urls, final_labels, final_allow, final_types),
            "openphish_split": {
                "total": 300,
                "dev_phishing": len(dev_phish),
                "final_phishing": len(final_phish),
                "seed": 42,
            },
        }
    else:
        realworld = {
            "available": False,
            "reason": "legit_dev.csv/legit_final.csv belum ada (jalankan T24a).",
        }

    payload["evaluation"] = {"realworld": realworld}
    payload["train"] = {
        "cv_grouped": payload.get("cv_grouped", {}),
        "test_grouped": payload.get("test_grouped", {}),
        "www_normalization_effect": payload.get("www_normalization_effect", {}),
    }
    payload["t24a_aggregate"] = payload.get("t24a_aggregate", t24a_aggregate())
    payload["selection"] = {
        "selected": "B_refit",
        "criterion": "F1 phishing rata-rata CV train berkelompok (tie-break MCC); test PhiUSIIL berkelompok dan set dev juga dilaporkan.",
        "realworld_available": realworld.get("available", False),
    }
    payload["limitations"] = [
        "C_host kehilangan informasi path/query/skema, sehingga recall di PhiUSIIL lebih rendah.",
        "Aturan kesepakatan menghasilkan banyak SUSPICIOUS; proporsinya dilaporkan.",
        "Set legit dev/final pribadi dan kecil; interval kepercayaan lebar.",
        "Normalisasi www. mengubah host dan tabel TLD; efeknya dilaporkan, tetapi tidak ada tuning.",
        "Pemilihan tidak memakai set final.",
    ]

    JSON_PATH.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    DOC_PATH.write_text(render_markdown(payload), encoding="utf-8")
    print(f"T24a tersedia: {realworld.get('available')}")
    if realworld.get("available"):
        for split in ("dev", "final"):
            data = realworld[split]
            print(f"{split}: n={data['n']}, legit={data['n_legit']}, phishing={data['n_phishing']}")
    print(f"Ditulis: {JSON_PATH.relative_to(ROOT)} dan {DOC_PATH.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
