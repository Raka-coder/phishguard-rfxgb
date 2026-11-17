"""Evaluasi varian T24 pada set dunia nyata T18 dan sensitivitas bentuk URL.

Dipanggil setelah `scripts/train_model_c.py`. Menambahkan bagian `evaluation` ke
`docs/model_c.json` lalu menulis `docs/model_c.md`. Skor dihitung langsung dari model
(tanpa allowlist/uncertainty band) supaya perbandingan varian setara. Tidak ada URL di
keluaran publik.
"""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import joblib
import numpy as np
from sklearn.metrics import roc_auc_score

from scripts.diagnose_realworld import (
    flipped_scheme,
    toggled_trailing_slash,
    with_www,
    without_path_query,
)
from scripts.eval_realworld import is_valid_url, load_rows, metrics, wilson_interval
from scripts.train_model_c import (
    EXPERIMENT_DIR,
    JSON_PATH,
    TLD_PATH,
    VARIANTS,
    base_frame,
    phishing_proba,
)
from src.config import LABEL_LEGIT, LABEL_PHISH, THRESHOLD
from src.features_host import host_of
from src.reputation import is_trusted

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CSV = ROOT / "data" / "realworld" / "urls.csv"
DOC_PATH = ROOT / "docs" / "model_c.md"
TRANSFORMS = {
    "no_path_query": without_path_query,
    "scheme_flip": flipped_scheme,
    "www_prefix": with_www,
    "trailing_slash": toggled_trailing_slash,
}
GROUPS = ("full", "not_in_allowlist")


def variant_matrix(urls: list[str], spec: dict, table: dict, default: float):
    frame = base_frame(np.asarray(urls), spec["source"], table, default)
    drop = list(spec["drop"])
    return frame.drop(columns=drop) if drop else frame


def score_group(y_true: np.ndarray, proba: np.ndarray) -> dict[str, object]:
    """Metrik dengan phishing positif, plus ROC-AUC dan CI Wilson specificity."""
    predicted = np.where(proba >= THRESHOLD, LABEL_PHISH, LABEL_LEGIT).astype(int)
    block = metrics(np.asarray(y_true, dtype=int).tolist(), predicted.tolist())
    block["roc_auc"] = round(
        float(roc_auc_score((np.asarray(y_true) == LABEL_PHISH).astype(int), proba)), 4
    )
    block["specificity_ci95"] = wilson_interval(block["tn"], block["tn"] + block["fp"])
    return block


def evaluate_realworld(
    urls: list[str],
    labels: np.ndarray,
    in_allowlist: np.ndarray,
    models: dict,
    tld: dict,
) -> dict[str, object]:
    indices = {group: np.arange(len(urls)) for group in GROUPS}
    indices["not_in_allowlist"] = np.where(~in_allowlist)[0]
    payload: dict[str, object] = {
        "source": "data/realworld/urls.csv (set T18)",
        "n_urls": len(urls),
        "n_legit": int(np.sum(labels == LABEL_LEGIT)),
        "n_phishing": int(np.sum(labels == LABEL_PHISH)),
        "in_allowlist": int(in_allowlist.sum()),
        "note": (
            "Skor model mentah tanpa lapisan allowlist/uncertainty, memakai tabel TLD host "
            "baru untuk semua varian (termasuk B_refit); T18 tidak dipakai memilih varian."
        ),
        "groups": {
            group: {
                "n": int(len(index)),
                "n_legit": int(np.sum(labels[index] == LABEL_LEGIT)),
                "n_phishing": int(np.sum(labels[index] == LABEL_PHISH)),
            }
            for group, index in indices.items()
        },
        "variants": {},
    }
    for name, spec in VARIANTS.items():
        proba = phishing_proba(models[name], variant_matrix(urls, spec, tld["map"], tld["default"]))
        payload["variants"][name] = {
            "score_mean": round(float(proba.mean()), 4),
            "score_median": round(float(np.median(proba)), 4),
            "groups": {group: score_group(labels[index], proba[index]) for group, index in indices.items()},
        }
    return payload


def sensitivity(urls_legit: list[str], models: dict, tld: dict) -> dict[str, object]:
    """Perubahan skor legit saat bentuk URL diubah; C_host seharusnya invarian."""
    transformed = {name: [fn(url) for url in urls_legit] for name, fn in TRANSFORMS.items()}
    payload: dict[str, object] = {
        "n_legit": len(urls_legit),
        "transforms": list(TRANSFORMS),
        "variants": {},
    }
    for name, spec in VARIANTS.items():
        original = phishing_proba(
            models[name], variant_matrix(urls_legit, spec, tld["map"], tld["default"])
        )
        entry: dict[str, object] = {"original_mean": round(float(original.mean()), 4), "variants": {}}
        for transform, values in transformed.items():
            proba = phishing_proba(
                models[name], variant_matrix(values, spec, tld["map"], tld["default"])
            )
            delta = proba - original
            entry["variants"][transform] = {
                "urls_changed": int(sum(a != b for a, b in zip(values, urls_legit))),
                "mean": _num(delta.mean()),
                "median": _num(np.median(delta)),
                "max_abs": _num(np.max(np.abs(delta))),
                "increased": int((delta > 0).sum()),
                "decreased": int((delta < 0).sum()),
                "unchanged": int((delta == 0).sum()),
            }
        payload["variants"][name] = entry
    return payload


def _fmt(value) -> str:
    return "—" if value is None else str(value)


def _num(value) -> float:
    """Bulatkan 4 desimal tanpa '-0.0' yang membingungkan di dokumen publik."""
    rounded = round(float(value), 4)
    return 0.0 if rounded == 0 else rounded


def _ci(interval: dict[str, float] | None) -> str:
    if not interval:
        return "—"
    return f"{interval['low']}–{interval['high']}"


def render_markdown(payload: dict) -> str:
    data = payload["data"]
    split = payload["split"]
    variants = payload["variants"]
    evaluation = payload["evaluation"]
    realworld = evaluation["realworld"]
    sens = evaluation["sensitivity"]
    lines = [
        "# Model C — eksperimen host-only (T24)",
        "",
        f"Dihasilkan `scripts/train_model_c.py` + `scripts/eval_model_c.py` pada "
        f"{payload['generated_at']} (dievaluasi {payload['evaluated_at']}). "
        "Semua angka berasal dari kedua skrip; tidak ada angka manual.",
        "",
        "## Ringkasan",
        "",
        "| Varian | Fitur | CV F1 | Test F1 | Test MCC | Test ROC-AUC | "
        "T18 penuh F1 | T18 non-allowlist F1 | Specificity non-allowlist (95% CI) | Latih (dtk) |",
        "|---|---|---|---|---|---|---|---|---|---|",
    ]
    for name, values in variants.items():
        group = realworld["variants"][name]["groups"]["not_in_allowlist"]
        seconds = values["train_seconds"]["cv"] + values["train_seconds"]["final_fit"]
        lines.append(
            f"| `{name}` | {values['n_features']} | {values['cv_grouped']['f1_phishing_mean']} | "
            f"{_fmt(values['test_grouped']['f1'])} | {_fmt(values['test_grouped']['mcc'])} | "
            f"{_fmt(values['test_grouped']['roc_auc'])} | "
            f"{_fmt(realworld['variants'][name]['groups']['full']['f1'])} | "
            f"{_fmt(group['f1'])} | {_fmt(group['specificity'])} ({_ci(group['specificity_ci95'])}) | "
            f"{seconds} |"
        )
    selected = payload["selection"]
    lines += [
        "",
        f"Varian yang direkomendasikan: **`{selected['selected']}`** — {selected['criterion']}.",
        "",
        "## Data dan split",
        "",
        f"- Sumber: `{data['source']}`; {data['raw_rows']} baris awal, "
        f"{data['duplicate_url_rows_removed']} baris duplikat URL dibuang, "
        f"{data['rows_after_dedup']} baris dipakai ({data['labels']['legit']} legit, "
        f"{data['labels']['phishing']} phishing; {data['unique_hosts']} host unik).",
        f"- Split: {split['train_rows']} train / {split['test_rows']} test "
        f"({split['test_rows_pct']}% baris); {split['train_hosts']} / {split['test_hosts']} host; "
        f"host yang muncul di kedua sisi: {split['host_overlap']}.",
        f"- Label train: {split['train_labels']['legit']} legit, "
        f"{split['train_labels']['phishing']} phishing. Label test: "
        f"{split['test_labels']['legit']} legit, {split['test_labels']['phishing']} phishing.",
        f"- CV: {payload['parameters']['cv']} ({payload['parameters']['cv_folds']} fold), "
        f"seed {payload['parameters']['seed']}.",
        "",
        "## TLD probability",
        "",
        "| Tabel | Kunci | Kunci berfragmen path | Default | Cakupan TLD baris test |",
        "|---|---|---|---|---|",
    ]
    new = payload["tld_probability"]["new"]
    old = payload["tld_probability"]["old"]
    lines.append(
        f"| Baru (host, OOF) | {new['n_tlds']} | 0 | {new['default']} | "
        f"{new['test_rows_covered_pct']}% |"
    )
    if old.get("available"):
        lines.append(
            f"| Lama (URL penuh) | {old['n_tlds']} | {old['keys_with_path_fragment']} | "
            f"{old['default']} | {old['test_rows_covered_pct']}% |"
        )
    lines += [
        "",
        f"Rumus baru: `{new['formula']}`; default `{new['default_formula']}`. "
        f"Baris train memakai nilai {new['train_values']}; baris test memakai "
        f"{new['test_values']}.",
    ]
    if old.get("available"):
        lines.append(f"Tabel lama: {old['note']}")
    lines += [
        "",
        "## Fitur",
        "",
        "| Varian | Sumber fitur | Jumlah | Daftar |",
        "|---|---|---|---|",
    ]
    for name, values in variants.items():
        lines.append(
            f"| `{name}` | {values['source']} | {values['n_features']} | "
            + ", ".join(f"`{feature}`" for feature in values["features"])
            + " |"
        )
    lines += [
        "",
        "## CV train berkelompok",
        "",
        "| Varian | F1 phishing | MCC | ROC-AUC |",
        "|---|---|---|---|",
    ]
    for name, values in variants.items():
        cv = values["cv_grouped"]
        lines.append(
            f"| `{name}` | {cv['f1_phishing_mean']} | {cv['mcc_mean']} | {cv['roc_auc_mean']} |"
        )
    lines += [
        "",
        "## Test berkelompok (host tidak tumpang tindih dengan train)",
        "",
        "| Varian | Precision | Recall | F1 | MCC | ROC-AUC | TP | FP | FN | TN |",
        "|---|---|---|---|---|---|---|---|---|---|",
    ]
    for name, values in variants.items():
        test = values["test_grouped"]
        lines.append(
            f"| `{name}` | {_fmt(test['precision'])} | {_fmt(test['recall'])} | "
            f"{_fmt(test['f1'])} | {_fmt(test['mcc'])} | {_fmt(test['roc_auc'])} | "
            f"{test['tp']} | {test['fp']} | {test['fn']} | {test['tn']} |"
        )
    for group in GROUPS:
        title = "T18 penuh" if group == "full" else "T18 tanpa allowlist"
        info = realworld["groups"][group]
        lines += [
            "",
            f"## {title}",
            "",
            f"{info['n']} URL ({info['n_legit']} legit, {info['n_phishing']} phishing). "
            "Skor model mentah, tanpa lapisan reputasi, memakai tabel TLD host baru.",
            "",
            "| Varian | Precision | Recall | F1 | MCC | ROC-AUC | Specificity (95% CI) |",
            "|---|---|---|---|---|---|---|",
        ]
        for name in variants:
            block = realworld["variants"][name]["groups"][group]
            lines.append(
                f"| `{name}` | {_fmt(block['precision'])} | {_fmt(block['recall'])} | "
                f"{_fmt(block['f1'])} | {_fmt(block['mcc'])} | {_fmt(block['roc_auc'])} | "
                f"{_fmt(block['specificity'])} ({_ci(block['specificity_ci95'])}) |"
            )
    t18_order = sorted(
        variants,
        key=lambda name: realworld["variants"][name]["groups"]["not_in_allowlist"]["f1"] or 0,
        reverse=True,
    )
    lines += [
        "",
        "## Catatan pemilihan vs hasil akhir",
        "",
        f"Aturan tugas: varian dipilih hanya dari CV train, sehingga rekomendasi tetap "
        f"`{selected['selected']}`. Pada T18 non-allowlist urutan F1 adalah "
        + ", ".join(f"`{name}`" for name in t18_order)
        + "; angka ini dilaporkan sebagai hasil akhir dan tidak dipakai memilih ulang.",
    ]
    lines += [
        "",
        "## Sensitivitas URL legitimate",
        "",
        f"{sens['n_legit']} URL legit T18; delta skor P(phishing) terhadap URL asli.",
        "",
        "| Varian | Perubahan | URL berubah | Mean delta | Median delta | Maks | Naik | Turun |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for name, values in sens["variants"].items():
        for transform, block in values["variants"].items():
            lines.append(
                f"| `{name}` | `{transform}` | {block['urls_changed']} | {block['mean']} | "
                f"{block['median']} | {block['max_abs']} | {block['increased']} | "
                f"{block['decreased']} |"
            )
    lines += [
        "",
        "`C_host` hanya memakai host, sehingga pemotongan path/query, tukar skema, dan "
        "trailing slash seharusnya menghasilkan delta 0; `www_prefix` tetap mengubah host.",
        "",
        "## Waktu latih",
        "",
        "| Varian | CV 5-fold (dtk) | Fit akhir (dtk) |",
        "|---|---|---|",
    ]
    for name, values in variants.items():
        lines.append(
            f"| `{name}` | {values['train_seconds']['cv']} | {values['train_seconds']['final_fit']} |"
        )
    lines += [
        "",
        f"Total skrip latih: {payload['train_seconds_total']} detik. "
        "Hyperparameter sama dengan Model B (tanpa tuning).",
        "",
        "## Batasan",
        "",
    ]
    lines += [f"- {item}" for item in payload["limitations"]]
    lines += [
        "- Skor T18 dihitung tanpa allowlist/band ragu, sehingga bukan vonis produksi.",
        "- Varian sensitivitas mengubah URL asli; skornya bukan skor URL sebenarnya.",
        "- Model C tidak dapat menangkap phishing yang hanya berbeda di path/query.",
        "",
        "## Perintah",
        "",
        "```powershell",
        "uv run python scripts/train_model_c.py",
        "uv run python scripts/eval_model_c.py",
        "uv run pytest -q",
        "```",
        "",
        "Artefak model eksperimen ada di `models/experimental/` (gitignored). "
        "`src/model.pkl`, API, dan UI tidak berubah.",
        "",
    ]
    return "\n".join(lines)


def main() -> int:
    if not JSON_PATH.exists() or not TLD_PATH.exists():
        print("Jalankan `uv run python scripts/train_model_c.py` dulu.")
        return 2
    missing = [name for name in VARIANTS if not (EXPERIMENT_DIR / f"{name}.pkl").exists()]
    if missing:
        print(f"Artefak hilang: {', '.join(missing)}; jalankan ulang train_model_c.py.")
        return 2
    if not DEFAULT_CSV.exists():
        print(f"File tidak ditemukan: {DEFAULT_CSV}; jalankan scripts/build_realworld_set.py.")
        return 2

    rows = [row for row in load_rows(DEFAULT_CSV) if is_valid_url((row.get("url") or "").strip())]
    urls = [(row.get("url") or "").strip() for row in rows]
    labels = np.array([int(row["label"]) for row in rows], dtype=int)
    in_allowlist = np.array([is_trusted(host_of(url)) for url in urls])

    tld = json.loads(TLD_PATH.read_text(encoding="utf-8"))
    models = {name: joblib.load(EXPERIMENT_DIR / f"{name}.pkl") for name in VARIANTS}
    legit_urls = [urls[index] for index in np.where(labels == LABEL_LEGIT)[0]]

    payload = json.loads(JSON_PATH.read_text(encoding="utf-8"))
    payload["evaluated_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    payload["evaluation"] = {
        "realworld": evaluate_realworld(urls, labels, in_allowlist, models, tld),
        "sensitivity": sensitivity(legit_urls, models, tld),
    }
    JSON_PATH.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    DOC_PATH.write_text(render_markdown(payload), encoding="utf-8")
    print(f"Ditulis: {JSON_PATH.relative_to(ROOT)} dan {DOC_PATH.relative_to(ROOT)}")
    print(f"T18: {len(urls)} URL, {int(in_allowlist.sum())} di allowlist")
    return 0


if __name__ == "__main__":
    sys.exit(main())
