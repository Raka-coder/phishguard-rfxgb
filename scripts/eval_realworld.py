"""Evaluasi set uji dunia nyata: model saja vs model + lapisan reputasi.

Positif = phishing (label 0). `SUSPICIOUS` dihitung non-phishing dan jumlahnya
dilaporkan terpisah. Metrik utama reputasi dihitung pada kelompok URL yang
domainnya TIDAK ada di allowlist. Semua angka dihitung di sini lalu ditulis ke
`docs/realworld.json`; daftar error untuk analisis manual ditulis ke
`data/realworld/errors.csv` (lokal, gitignored). Tidak ada angka metrik manual.
"""

import argparse
import csv
import json
import math
import random
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
from src.reputation import is_trusted

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CSV = ROOT / "data" / "realworld" / "urls.csv"
DEFAULT_OUT = ROOT / "docs" / "realworld.json"
DEFAULT_ERRORS = ROOT / "data" / "realworld" / "errors.csv"
_ALLOWED_SCHEMES = {"http", "https"}
_Z_95 = 1.96
_BALANCED_SEED = 42
_PRIMARY_GROUP = "not_in_allowlist"
_KNOWN_DECISION_SOURCES = ("allowlist", "model", "uncertainty")
_ERROR_FIELDS = [
    "variant",
    "error_type",
    "url",
    "label",
    "source",
    "model_probability",
    "model_prediction",
    "verdict",
    "decision_source",
    "in_allowlist",
]


def is_valid_url(url: str) -> bool:
    try:
        parts = urlsplit(url)
    except ValueError:
        return False
    return parts.scheme.lower() in _ALLOWED_SCHEMES and bool(parts.hostname)


def load_rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return [dict(row) for row in csv.DictReader(handle)]


def wilson_interval(successes: int, n: int, z: float = _Z_95) -> dict[str, float] | None:
    """Interval kepercayaan Wilson 95% untuk proporsi; None bila n = 0."""
    if n <= 0:
        return None
    p = successes / n
    denom = 1 + z * z / n
    center = (p + z * z / (2 * n)) / denom
    margin = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return {"low": round(max(0.0, center - margin), 4), "high": round(min(1.0, center + margin), 4)}


def metrics(y_true: list[int], y_pred: list[int]) -> dict[str, object]:
    """Confusion matrix + metrik dengan phishing (0) sebagai positif."""
    tp = sum(1 for t, p in zip(y_true, y_pred) if t == LABEL_PHISH and p == LABEL_PHISH)
    fp = sum(1 for t, p in zip(y_true, y_pred) if t == LABEL_LEGIT and p == LABEL_PHISH)
    fn = sum(1 for t, p in zip(y_true, y_pred) if t == LABEL_PHISH and p == LABEL_LEGIT)
    tn = sum(1 for t, p in zip(y_true, y_pred) if t == LABEL_LEGIT and p == LABEL_LEGIT)

    precision = _div(tp, tp + fp)
    recall = _div(tp, tp + fn)
    specificity = _div(tn, tn + fp)
    balanced = _div(recall + specificity, 2) if recall is not None and specificity is not None else None
    mcc_denom = (tp + fp) * (tp + fn) * (tn + fp) * (tn + fn)

    return {
        "n": len(y_true),
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "tn": tn,
        "precision": precision,
        "recall": recall,
        "f1": _div(2 * tp, 2 * tp + fp + fn),
        "specificity": specificity,
        "balanced_accuracy": balanced,
        "mcc": round((tp * tn - fp * fn) / math.sqrt(mcc_denom), 4) if mcc_denom else None,
        "fp_rate": _div(fp, fp + tn),
        "fp_rate_ci95": wilson_interval(fp, fp + tn),
        "recall_ci95": wilson_interval(tp, tp + fn),
        "predicted_phishing_pct": round((tp + fp) / len(y_true) * 100, 2) if y_true else None,
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


def _metrics_for(indices: list[int], y_true: list[int], y_pred: list[int]) -> dict[str, object]:
    return metrics([y_true[i] for i in indices], [y_pred[i] for i in indices])


def _reputation_block(
    indices: list[int],
    y_true: list[int],
    reputation_pred: list[int],
    predictions: list[dict],
    in_allowlist: list[bool],
) -> dict[str, object]:
    """Metrik reputasi: utama tanpa allowlist, plus rincian sumber dan allowlist."""
    allow_idx = [i for i in indices if in_allowlist[i]]
    not_allow_idx = [i for i in indices if not in_allowlist[i]]
    by_allowlist = {
        "in_allowlist": _metrics_for(allow_idx, y_true, reputation_pred),
        "not_in_allowlist": _metrics_for(not_allow_idx, y_true, reputation_pred),
    }
    sources = sorted(set(_KNOWN_DECISION_SOURCES) | {predictions[i]["decision_source"] for i in indices})
    by_decision_source = {
        source: _metrics_for(
            [i for i in indices if predictions[i]["decision_source"] == source],
            y_true,
            reputation_pred,
        )
        for source in sources
    }
    all_metrics = _metrics_for(indices, y_true, reputation_pred)
    return {
        "primary_group": _PRIMARY_GROUP,
        "primary": by_allowlist[_PRIMARY_GROUP],
        "all": {
            **all_metrics,
            "suspicious": sum(1 for i in indices if predictions[i]["verdict"] == VERDICT_SUSPICIOUS),
        },
        "by_allowlist": by_allowlist,
        "by_decision_source": by_decision_source,
    }


def _balanced_block(
    y_true: list[int],
    model_pred: list[int],
    reputation_pred: list[int],
    predictions: list[dict],
    in_allowlist: list[bool],
) -> dict[str, object]:
    """Sampel phishing diturunkan (seed tetap) agar jumlah kelas seimbang."""
    phishing_idx = [i for i, label in enumerate(y_true) if label == LABEL_PHISH]
    legit_idx = [i for i, label in enumerate(y_true) if label == LABEL_LEGIT]
    if not phishing_idx or not legit_idx:
        return {"available": False, "reason": "butuh minimal satu URL phishing dan satu legitimate"}

    sampled_idx = (
        random.Random(_BALANCED_SEED).sample(phishing_idx, len(legit_idx))
        if len(phishing_idx) > len(legit_idx)
        else phishing_idx
    )
    indices = sorted(sampled_idx + legit_idx)
    return {
        "available": True,
        "seed": _BALANCED_SEED,
        "equal_classes": len(sampled_idx) == len(legit_idx),
        "n_per_class": min(len(sampled_idx), len(legit_idx)),
        "model_only": _metrics_for(indices, y_true, model_pred),
        "with_reputation": _reputation_block(indices, y_true, reputation_pred, predictions, in_allowlist),
    }


def _collect_errors(
    rows: list[dict[str, str]],
    urls: list[str],
    probabilities: list[float],
    predictions: list[dict],
    model_pred: list[int],
    reputation_pred: list[int],
    in_allowlist: list[bool],
) -> list[dict[str, object]]:
    """FP/FN pada set penuh untuk analisis manual; tidak masuk JSON publik."""
    errors: list[dict[str, object]] = []
    for i, url in enumerate(urls):
        label = int(rows[i]["label"])
        for variant, prediction in (("model_only", model_pred[i]), ("with_reputation", reputation_pred[i])):
            if prediction == label:
                continue
            errors.append(
                {
                    "variant": variant,
                    "error_type": "FP" if label == LABEL_LEGIT else "FN",
                    "url": url,
                    "label": label,
                    "source": (rows[i].get("source") or "unknown").strip() or "unknown",
                    "model_probability": round(probabilities[i], 4),
                    "model_prediction": "PHISHING" if model_pred[i] == LABEL_PHISH else "LEGITIMATE",
                    "verdict": predictions[i]["verdict"],
                    "decision_source": predictions[i]["decision_source"],
                    "in_allowlist": in_allowlist[i],
                }
            )
    return errors


def evaluate(rows: list[dict[str, str]], csv_path: Path) -> tuple[dict, list[dict[str, object]]]:
    valid = [row for row in rows if is_valid_url((row.get("url") or "").strip())]
    skipped = len(rows) - len(valid)
    urls = [row["url"].strip() for row in valid]
    y_true = [int(row["label"]) for row in valid]

    probabilities = score_model_only(urls)
    model_pred = [LABEL_PHISH if p >= THRESHOLD else LABEL_LEGIT for p in probabilities]
    predictions = [predict_url(url) for url in urls]
    reputation_pred = [binary_from_verdict(item["verdict"]) for item in predictions]
    in_allowlist = [is_trusted(urlsplit(url).hostname or "") for url in urls]

    sources: dict[str, int] = {}
    for row in valid:
        key = (row.get("source") or "unknown").strip() or "unknown"
        sources[key] = sources.get(key, 0) + 1
    collected = sorted(row.get("collected_at") or "" for row in valid)
    try:
        dataset_path = csv_path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        dataset_path = csv_path.as_posix()

    indices = list(range(len(valid)))
    data = {
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
            "primary_group": "metrik utama reputasi dihitung pada kelompok not_in_allowlist",
            "intervals": "Wilson 95% untuk fp_rate dan recall",
        },
        "thresholds": {
            "model_label": THRESHOLD,
            "phishing": THRESHOLD_PHISHING,
            "suspicious": THRESHOLD_SUSPICIOUS,
        },
        "variants": {
            "full": {
                "model_only": _metrics_for(indices, y_true, model_pred),
                "with_reputation": _reputation_block(
                    indices, y_true, reputation_pred, predictions, in_allowlist
                ),
            },
            "balanced": _balanced_block(y_true, model_pred, reputation_pred, predictions, in_allowlist),
        },
    }
    errors = _collect_errors(valid, urls, probabilities, predictions, model_pred, reputation_pred, in_allowlist)
    return data, errors


def write_json(data: dict, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def write_errors(errors: list[dict[str, object]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=_ERROR_FIELDS)
        writer.writeheader()
        writer.writerows(errors)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Evaluasi set uji dunia nyata")
    parser.add_argument("--csv", default=str(DEFAULT_CSV), help="CSV dari build_realworld_set.py")
    parser.add_argument("--out", default=str(DEFAULT_OUT), help="JSON keluaran (agregat)")
    parser.add_argument("--errors", default=str(DEFAULT_ERRORS), help="CSV FP/FN lokal (gitignored)")
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
        data, errors = evaluate(rows, csv_path)
    except RuntimeError as exc:
        print(f"Artefak model belum siap: {exc}")
        return 1

    out_path = Path(args.out)
    errors_path = Path(args.errors)
    write_json(data, out_path)
    write_errors(errors, errors_path)
    print(f"Ditulis: {out_path}")
    print(f"Error lokal: {errors_path} ({len(errors)} baris)")
    for scope in ("full", "balanced"):
        block = data["variants"][scope]
        if scope == "balanced" and not block.get("available"):
            continue
        for name in ("model_only", "with_reputation"):
            values = block[name]
            if "primary" in values:
                values = values["primary"]
            print(
                f"{scope}.{name}: precision={values['precision']} recall={values['recall']} "
                f"f1={values['f1']} specificity={values['specificity']} "
                f"mcc={values['mcc']} FP={values['fp']} FN={values['fn']}"
            )
    return 0


if __name__ == "__main__":
    sys.exit(main())
