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
from scripts.diagnose_realworld import (
    flipped_scheme,
    toggled_trailing_slash,
    with_www,
    without_path_query,
)
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
    block["roc_auc"] = round(float(roc_auc_score((np.asarray(y_true) == LABEL_PHISH).astype(int), proba)), 4) if len(set(y_true)) > 1 else None
    block["specificity_ci95"] = wilson_interval(block["tn"], block["tn"] + block["fp"])
    block["recall_ci95"] = wilson_interval(block["tp"], block["tp"] + block["fn"])
    block["specificity_strict"] = block["specificity"]
    block["specificity_loose"] = block["specificity"]
    block["recall_terjaring"] = block["recall"]
    block["legit_suspicious_pct"] = 0.0
    return block


def baseline_block(y_true, lengths, threshold):
    predicted = np.where(np.asarray(lengths) >= threshold, LABEL_PHISH, LABEL_LEGIT).astype(int)
    block = metrics(np.asarray(y_true, dtype=int).tolist(), predicted.tolist())
    block["roc_auc"] = round(
        float(roc_auc_score((np.asarray(y_true) == LABEL_PHISH).astype(int), np.asarray(lengths, dtype=float))), 4
    ) if len(set(y_true)) > 1 else None
    block["threshold"] = float(threshold)
    block["specificity_ci95"] = wilson_interval(block["tn"], block["tn"] + block["fp"])
    block["recall_ci95"] = wilson_interval(block["tp"], block["tp"] + block["fn"])
    block["specificity_strict"] = block["specificity"]
    block["specificity_loose"] = block["specificity"]
    block["recall_terjaring"] = block["recall"]
    block["legit_suspicious_pct"] = 0.0
    return block


def consensus_block(y_true, p_b, p_c):
    verdict, predicted, susp_pct = consensus_proba(p_b, p_c)
    block = metrics(np.asarray(y_true, dtype=int).tolist(), predicted.tolist())
    block["roc_auc"] = None
    block["specificity_ci95"] = wilson_interval(block["tn"], block["tn"] + block["fp"])
    block["recall_ci95"] = wilson_interval(block["tp"], block["tp"] + block["fn"])
    block["suspicious_pct"] = susp_pct
    block["suspicious_n"] = int(np.sum(verdict == "SUSPICIOUS"))
    y = np.asarray(y_true, dtype=int)
    phishing_mask = y == LABEL_PHISH
    legit_mask = ~phishing_mask
    suspicious_phishing = int(np.sum((verdict == "SUSPICIOUS") & phishing_mask))
    suspicious_legit = int(np.sum((verdict == "SUSPICIOUS") & legit_mask))
    recall_terjaring = round(float(np.mean((verdict[phishing_mask] != "LEGITIMATE"))), 4) if phishing_mask.any() else None
    specificity_strict = round(float(np.mean(verdict[legit_mask] == "LEGITIMATE")), 4) if legit_mask.any() else None
    specificity_loose = block["specificity"]
    legit_suspicious_pct = round(float(np.mean(verdict[legit_mask] == "SUSPICIOUS") * 100), 2) if legit_mask.any() else 0.0
    block["recall_terjaring"] = recall_terjaring
    block["specificity_strict"] = specificity_strict
    block["specificity_loose"] = specificity_loose
    block["legit_suspicious_pct"] = legit_suspicious_pct
    block["suspicious_phishing_n"] = suspicious_phishing
    block["suspicious_legit_n"] = suspicious_legit
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


def evaluate_set(urls, labels, in_allow, host_types, baseline_threshold):
    tld_old = load_tld(DEFAULT_TLD_OLD)
    tld_new = load_tld(DEFAULT_TLD_NEW)
    pipe_b = joblib.load(B_REFIT_PATH)
    pipe_c = joblib.load(C_HOST_PATH)
    p_b = phishing_proba(pipe_b, to_frame(urls, tld_old["map"], tld_old["default"]))
    p_c = phishing_proba(pipe_c, to_host_frame(urls, tld_new["map"], tld_new["default"], strip_www=True))
    lengths = to_frame(urls, tld_old["map"], tld_old["default"])["DomainLength"].to_numpy(dtype=float)
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
        "candidates": {},
    }
    for name, mask in groups.items():
        if mask.sum() == 0:
            continue
        block = {
            "B_refit": score_block(y[mask], p_b[mask]),
            "C_host": score_block(y[mask], p_c[mask]),
            "consensus": consensus_block(y[mask], p_b[mask], p_c[mask]),
            "baseline_DomainLength": baseline_block(y[mask], lengths[mask], baseline_threshold),
        }
        result["groups"][name] = block
    result["candidates"] = result["groups"].get("all", {})
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
        "## Aturan keputusan (T25d)",
        "",
        f"Syarat lantai recall-terjaring test PhiUSIIL grouped: {payload.get('decision_rule', {}).get('floor_recall_grouped_test', '—')}.",
        f"Lolos: {', '.join(payload.get('decision_rule', {}).get('eligible_by_floor', [])) or '—'}.",
        f"Terpilih: **`{payload.get('selection', {}).get('selected')}`**.",
        "",
        "Robustness (rata-rata perubahan skor/verdict; makin kecil makin tahan):",
        "",
        "| Kandidat | Robustness |",
        "|---|---|",
    ]
    for name in ("B_refit", "C_host", "consensus", "baseline_DomainLength"):
        value = payload.get("decision_rule", {}).get("robustness", {}).get(name, "—")
        lines.append(f"| `{name}` | {value} |")
    lines += [
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
    for name in ("B_refit", "C_host", "consensus", "baseline_DomainLength"):
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
    for name in ("B_refit", "C_host", "consensus", "baseline_DomainLength"):
        block = cv[name]
        if name == "consensus":
            lines.append(f"| `{name}` | MCC {block['mcc_mean']} | {block['suspicious_pct_mean']} |")
        elif name == "baseline_DomainLength":
            lines.append(f"| `{name}` | MCC {block['mcc_mean']}, Recall {block['recall_mean']}, Spec {block['specificity_mean']}, AUC {block['roc_auc_mean']} | — |")
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
            if split_name not in realworld:
                continue
            split_data = realworld[split_name]
            lines += [
                f"### {split_name}",
                "",
                f"{split_data['n']} URL ({split_data['n_legit']} legit, {split_data['n_phishing']} phishing; "
                f"{split_data['n_root']} root, {split_data['n_berpath']} berpath; "
                f"{split_data['n_in_allowlist']} in allowlist, {split_data['n_not_in_allowlist']} not).",
                "",
                "| Kandidat | Precision | Recall (95% CI) | F1 | MCC | Spec ketat | Spec longgar | Recall-terjaring | Legit SUSP % | Suspicious % |",
                "|---|---|---|---|---|---|---|---|---|---|",
            ]
            for name in ("B_refit", "C_host", "consensus", "baseline_DomainLength"):
                block = split_data["candidates"][name]
                lines.append(
                    f"| `{name}` | {_fmt(block['precision'])} | {_fmt(block['recall'])} "
                    f"({_ci(block['recall_ci95'])}) | {_fmt(block['f1'])} | {_fmt(block['mcc'])} | "
                    f"{_fmt(block.get('specificity_strict'))} | {_fmt(block.get('specificity_loose'))} | "
                    f"{_fmt(block.get('recall_terjaring'))} | {_fmt(block.get('legit_suspicious_pct'))} | "
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
                if group in split_data.get("groups", {}):
                    lines.append(
                        f"| {group} | {_fmt(split_data['groups'][group].get('B_refit', {}).get('f1'))} | "
                        f"{_fmt(split_data['groups'][group].get('C_host', {}).get('f1'))} | "
                        f"{_fmt(split_data['groups'][group].get('consensus', {}).get('f1'))} |"
                    )
            lines.append("")
    lines += [
        "## Agregat T24a",
        "",
    ]
    agg = payload.get("t24a_aggregate") or t24a_aggregate()
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


TRANSFORMS = {
    "no_path_query": without_path_query,
    "scheme_flip": flipped_scheme,
    "www_prefix": with_www,
    "trailing_slash": toggled_trailing_slash,
}


def transform_robustness(urls, p_b_orig, p_c_orig, verdict_orig, tld_old, tld_new, pipe_b, pipe_c):
    deltas = {"B_refit": [], "C_host": [], "consensus": []}
    for transform, fn in TRANSFORMS.items():
        values = [fn(u) for u in urls]
        pb = phishing_proba(pipe_b, to_frame(values, tld_old["map"], tld_old["default"]))
        pc = phishing_proba(pipe_c, to_host_frame(values, tld_new["map"], tld_new["default"], strip_www=True))
        deltas["B_refit"].append(float(np.mean(np.abs(pb - p_b_orig))))
        deltas["C_host"].append(float(np.mean(np.abs(pc - p_c_orig))))
        v, _, _ = consensus_proba(pb, pc)
        deltas["consensus"].append(float(np.mean(v != verdict_orig)))
    return {key: round(float(np.mean(value)), 4) for key, value in deltas.items()}


def apply_decision(dev_result, train, robustness, floor_recall):
    eligible = [
        name
        for name in ("B_refit", "C_host", "consensus", "baseline_DomainLength")
        if (train["test_grouped"].get(name, {}).get("recall_terjaring") or 0) >= floor_recall
    ]
    pool = eligible if eligible else ["B_refit", "C_host", "consensus", "baseline_DomainLength"]
    simplicity = {"baseline_DomainLength": 0, "C_host": 1, "B_refit": 2, "consensus": 3}
    mccs = {name: (dev_result["candidates"].get(name, {}).get("mcc") or -10) for name in pool}
    best_mcc = max(mccs.values())
    tied = [name for name in pool if best_mcc - (mccs[name] or -10) < 0.05]
    if len(tied) > 1:
        best = min(tied, key=lambda name: (robustness.get(name, 99), simplicity.get(name, 99)))
        tie = True
    else:
        best = max(pool, key=lambda name: (mccs[name] or -10, -robustness.get(name, 99), -simplicity.get(name, 99)))
        tie = False
    return best, eligible, pool, tied, tie


def main(argv=None):
    import argparse

    parser = argparse.ArgumentParser(description="Evaluasi T25b")
    parser.add_argument("--finalize", action="store_true", help="evaluasi set final satu kali")
    parser.add_argument("--force-final", action="store_true", help="paksa evaluasi ulang final")
    parser.add_argument("--floor-recall", type=float, default=0.95, help="syarat lantai recall PhiUSIIL grouped")
    args = parser.parse_args(argv)

    if not JSON_PATH.exists():
        print("Jalankan scripts/train_t25.py dulu.")
        return 2
    payload = json.loads(JSON_PATH.read_text(encoding="utf-8"))
    payload["evaluated_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")

    # Real-world dev evaluation
    realworld = (payload.get("evaluation") or {}).get("realworld", {"available": False})
    dev_result = None
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
        tld_old = load_tld(DEFAULT_TLD_OLD)
        tld_new = load_tld(DEFAULT_TLD_NEW)
        pipe_b = joblib.load(B_REFIT_PATH)
        pipe_c = joblib.load(C_HOST_PATH)
        p_b_dev = phishing_proba(pipe_b, to_frame(dev_urls, tld_old["map"], tld_old["default"]))
        p_c_dev = phishing_proba(pipe_c, to_host_frame(dev_urls, tld_new["map"], tld_new["default"], strip_www=True))
        verdict_dev, _, _ = consensus_proba(p_b_dev, p_c_dev)
        robustness = transform_robustness(dev_urls, p_b_dev, p_c_dev, verdict_dev, tld_old, tld_new, pipe_b, pipe_c)

        baseline_threshold = payload.get("baseline_domainlength", {}).get("threshold", payload.get("test_grouped", {}).get("baseline_DomainLength", {}).get("threshold"))
        dev_result = evaluate_set(dev_urls, dev_labels, dev_allow, dev_types, baseline_threshold)
        realworld = {
            "available": True,
            "dev": dev_result,
            "openphish_split": {
                "total": 300,
                "dev_phishing": len(dev_phish),
                "final_phishing": len(final_phish),
                "seed": 42,
            },
        }
        if "final" in (payload.get("evaluation") or {}).get("realworld", {}):
            realworld["final"] = payload["evaluation"]["realworld"]["final"]

        payload["train"] = {
            "cv_grouped": payload.get("cv_grouped", {}),
            "test_grouped": payload.get("test_grouped", {}),
            "www_normalization_effect": payload.get("www_normalization_effect", {}),
        }
        best, eligible, pool, tied, tie = apply_decision(dev_result, payload["train"], robustness, args.floor_recall)
        payload["evaluation"] = {"realworld": realworld}
        payload["decision_rule"] = {
            "floor_recall_grouped_test": args.floor_recall,
            "primary": "MCC tertinggi pada set dev dunia nyata (SUSPICIOUS dihitung ditandai)",
            "tie_threshold": 0.05,
            "eligible_by_floor": eligible,
            "pool": pool,
            "tied": tied,
            "tie": tie,
            "robustness": robustness,
        }
        payload["selection"] = {
            "selected": best,
            "criterion": (
                f"floor recall-terjaring grouped test >= {args.floor_recall}; "
                "MCC tertinggi pada set dev (SUSPICIOUS dihitung ditandai); "
                "seri jika selisih MCC dev < 0.05; tie-break ketahanan sensitivitas dan kesederhanaan"
            ),
            "realworld_available": True,
        }
        print(f"Kandidat lolos floor: {eligible}")
        print(f"Terpilih: {best}")
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
    payload["t24a_aggregate"] = payload.get("t24a_aggregate") or t24a_aggregate()

    # Final evaluation: only once unless forced
    if args.finalize:
        if "final" in payload.get("evaluation", {}).get("realworld", {}) and not args.force_final:
            print("Set final sudah dievaluasi sebelumnya; gunakan --force-final untuk mengulang.")
        elif not LEGIT_FINAL.exists():
            print(f"File tidak ditemukan: {LEGIT_FINAL}")
            return 2
        else:
            final_legit = load_rows(LEGIT_FINAL)
            _, final_phish = build_openphish_split()
            final_urls = [r["url"].strip() for r in final_legit] + list(final_phish)
            final_labels = np.array([LABEL_LEGIT] * len(final_legit) + [LABEL_PHISH] * len(final_phish), dtype=int)
            final_allow = np.array([is_trusted(host_of(u)) for u in final_urls])
            final_types = np.array([host_type(u) for u in final_urls])
            baseline_threshold = payload.get("baseline_domainlength", {}).get("threshold", payload.get("test_grouped", {}).get("baseline_DomainLength", {}).get("threshold"))
            final_result = evaluate_set(final_urls, final_labels, final_allow, final_types, baseline_threshold)
            payload["evaluation"]["realworld"]["final"] = final_result
            payload["evaluation"]["realworld"]["available"] = True
            print(f"Final dievaluasi: n={final_result['n']}")

    payload["limitations"] = [
        "C_host kehilangan informasi path/query/skema, sehingga recall di PhiUSIIL lebih rendah.",
        "Aturan kesepakatan menghasilkan banyak SUSPICIOUS; proporsinya dilaporkan.",
        "Set legit dev/final pribadi dan kecil; interval kepercayaan lebar.",
        "Normalisasi www. mengubah host dan tabel TLD; efeknya dilaporkan, tetapi tidak ada tuning.",
        "Pemilihan tidak memakai set final.",
        f"Syarat lantai recall grouped test: {args.floor_recall}.",
    ]

    JSON_PATH.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    DOC_PATH.write_text(render_markdown(payload), encoding="utf-8")
    if realworld.get("available"):
        print(f"Dev: n={realworld['dev']['n']}, legit={realworld['dev']['n_legit']}, phishing={realworld['dev']['n_phishing']}")
    print(f"T24a tersedia: {(payload.get('t24a_aggregate') or {}).get('available')}")
    print(f"Ditulis: {JSON_PATH.relative_to(ROOT)} dan {DOC_PATH.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
