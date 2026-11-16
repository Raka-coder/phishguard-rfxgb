"""Evaluasi set uji dunia nyata: model saja vs model + lapisan reputasi.

Positif = phishing (label 0). `SUSPICIOUS` dihitung non-phishing dan jumlahnya
dilaporkan terpisah. Semua angka dihitung di sini lalu ditulis ke
`docs/realworld.json`; tidak ada angka metrik yang ditulis manual.
"""

import argparse
import csv
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np

from src.config import (
    LABEL_LEGIT,
    LABEL_PHISH,
    THRESHOLD,
    THRESHOLD_PHISHING,
    THRESHOLD_SUSPICIOUS,
    VERDICT_PHISHING,
    VERDICT_SUSPICIOUS,
)
from src.feature_utils import to_frame
from src.predict import _load, predict_url

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CSV = ROOT / "data" / "realworld" / "urls.csv"
DEFAULT_OUT = ROOT / "docs" / "realworld.json"
_ALLOWED_SCHEMES = {"http", "https"}


def is_valid_url(url: str) -> bool:
    try:
        parts = urlsplit(url)
    except ValueError:
        return False
    return parts.scheme.lower() in _ALLOWED_SCHEMES and bool(parts.hostname)


def load_rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return [dict(row) for row in csv.DictReader(handle)]


def metrics(y_true: list[int], y_pred: list[int]) -> dict[str, float | int | None]:
    """Confusion matrix + precision/recall/F1 dengan phishing (0) sebagai positif."""
    tp = sum(1 for t, p in zip(y_true, y_pred) if t == LABEL_PHISH and p == LABEL_PHISH)
    fp = sum(1 for t, p in zip(y_true, y_pred) if t == LABEL_LEGIT and p == LABEL_PHISH)
    fn = sum(1 for t, p in zip(y_true, y_pred) if t == LABEL_PHISH and p == LABEL_LEGIT)
    tn = sum(1 for t, p in zip(y_true, y_pred) if t == LABEL_LEGIT and p == LABEL_LEGIT)
    precision = _div(tp, tp + fp)
    recall = _div(tp, tp + fn)
    f1 = _div(2 * tp, 2 * tp + fp + fn)
    return {
        "n": len(y_true),
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "tn": tn,
        "precision": precision,
        "recall": recall,
        "f1": f1,
    }


def _div(num: float, den: float) -> float | None:
    """Pembagian aman: denominator 0 -> None (metrik tidak terdefinisi, bukan 0)."""
    return round(num / den, 4) if den else None


def binary_from_verdict(verdict: str) -> int:
    """Hanya PHISHING yang dihitung positif; SUSPICIOUS/LEGITIMATE negatif."""
    return LABEL_PHISH if verdict == VERDICT_PHISHING else LABEL_LEGIT


def score_model_only(urls: list[str]) -> list[float]:
    """P(phishing) langsung dari Model B, melewati allowlist dan uncertainty band."""
    pipe, tld, _ = _load()
    frame = to_frame(urls, tld["map"], tld["default"])
    proba = pipe.predict_proba(frame.to_numpy(dtype=np.float32))
    column = list(pipe.classes_).index(LABEL_PHISH)
    return [float(row[column]) for row in proba]


def evaluate(rows: list[dict[str, str]], csv_path: Path) -> dict:
    valid = [row for row in rows if is_valid_url((row.get("url") or "").strip())]
    skipped = len(rows) - len(valid)
    urls = [row["url"].strip() for row in valid]
    y_true = [int(row["label"]) for row in valid]

    probabilities = score_model_only(urls)
    model_pred = [LABEL_PHISH if p >= THRESHOLD else LABEL_LEGIT for p in probabilities]

    reputation_pred = []
    suspicious = 0
    for url in urls:
        prediction = predict_url(url)
        verdict = prediction["verdict"]
        reputation_pred.append(binary_from_verdict(verdict))
        if verdict == VERDICT_SUSPICIOUS:
            suspicious += 1

    sources: dict[str, int] = {}
    for row in valid:
        key = (row.get("source") or "unknown").strip() or "unknown"
        sources[key] = sources.get(key, 0) + 1
    collected = sorted(row.get("collected_at") or "" for row in valid)
    try:
        dataset_path = csv_path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        dataset_path = csv_path.as_posix()

    return {
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "dataset": {
            "path": dataset_path,
            "n_total": len(rows),
            "n_evaluated": len(valid),
            "n_skipped_invalid": skipped,
            "n_phishing": sum(1 for label in y_true if label == LABEL_PHISH),
            "n_legit": sum(1 for label in y_true if label == LABEL_LEGIT),
            "sources": sources,
            "collected_at_min": next((value for value in collected if value), None),
            "collected_at_max": next((value for value in reversed(collected) if value), None),
        },
        "definitions": {
            "positive": "phishing (label 0)",
            "suspicious_counts_as": "non-phishing, dilaporkan terpisah",
            "model_only": f"Model B, ambang label {THRESHOLD}, tanpa allowlist",
            "with_reputation": (
                f"predict_url (allowlist + uncertainty band {THRESHOLD_SUSPICIOUS}-{THRESHOLD_PHISHING})"
            ),
        },
        "thresholds": {
            "model_label": THRESHOLD,
            "phishing": THRESHOLD_PHISHING,
            "suspicious": THRESHOLD_SUSPICIOUS,
        },
        "variants": {
            "model_only": metrics(y_true, model_pred),
            "with_reputation": {**metrics(y_true, reputation_pred), "suspicious": suspicious},
        },
    }


def write_json(data: dict, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Evaluasi set uji dunia nyata")
    parser.add_argument("--csv", default=str(DEFAULT_CSV), help="CSV dari build_realworld_set.py")
    parser.add_argument("--out", default=str(DEFAULT_OUT), help="JSON keluaran")
    args = parser.parse_args(argv)

    csv_path = Path(args.csv)
    if not csv_path.exists():
        print(f"File tidak ditemukan: {csv_path}")
        print("Jalankan `uv run python scripts/build_realworld_set.py` dulu.")
        return 2

    try:
        rows = load_rows(csv_path)
    except (OSError, KeyError, ValueError) as exc:
        print(f"Gagal membaca {csv_path}: {exc}")
        return 2
    if not rows:
        print("CSV kosong; tidak ada yang dievaluasi.")
        return 2

    try:
        data = evaluate(rows, csv_path)
    except RuntimeError as exc:
        print(f"Artefak model belum siap: {exc}")
        return 1

    out_path = Path(args.out)
    write_json(data, out_path)
    print(f"Ditulis: {out_path}")
    for name, values in data["variants"].items():
        print(
            f"{name}: precision={values['precision']} recall={values['recall']} "
            f"f1={values['f1']} FP={values['fp']} FN={values['fn']}"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
