"""Inference Model B: URL string -> label, probabilitas, dan top-5 fitur (tanpa jaringan)."""

import json
import sys
import time
from pathlib import Path
from urllib.parse import urlsplit

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # agar `import src.*` jalan sebagai skrip

import joblib
import numpy as np
import pandas as pd

from src.config import (
    LABEL_LEGIT,
    LABEL_PHISH,
    MODEL_B_PATH,
    STATS_PATH,
    THRESHOLD,
    TLD_PROBS_PATH,
    URL_FEATURES,
)
from src.feature_utils import extract_features

_ALLOWED_SCHEMES = {"http", "https"}
_ARTIFACTS: tuple | None = None


def _load() -> tuple:
    """Muat pipeline + lookup TLD + stats sekali (lazy singleton)."""
    global _ARTIFACTS
    if _ARTIFACTS is None:
        if not MODEL_B_PATH.exists():
            raise RuntimeError(f"Model belum ada: {MODEL_B_PATH}. Jalankan `uv run python src/train.py` dulu.")
        pipe = joblib.load(MODEL_B_PATH)
        tld = json.loads(TLD_PROBS_PATH.read_text(encoding="utf-8")) if TLD_PROBS_PATH.exists() else {"default": 0.5, "map": {}}
        stats = json.loads(STATS_PATH.read_text(encoding="utf-8")) if STATS_PATH.exists() else {}
        _ARTIFACTS = (pipe, tld, stats)
    return _ARTIFACTS


def _validate(url: str) -> str:
    if not isinstance(url, str):
        raise ValueError("URL tidak valid: harus berupa string")
    url = url.strip()
    if not url:
        raise ValueError("URL tidak valid: input kosong")
    try:
        parts = urlsplit(url)
    except ValueError:
        raise ValueError("URL tidak valid: format tidak dapat diurai") from None
    if parts.scheme.lower() not in _ALLOWED_SCHEMES:
        raise ValueError("URL tidak valid: scheme harus http atau https")
    if not parts.hostname:
        raise ValueError("URL tidak valid: host tidak ditemukan")
    return url


def _top_features(feats: dict[str, float], label: int, stats: dict) -> list[dict]:
    """Fitur paling mendorong keputusan: importance x |nilai - rata2 kelas yang diprediksi|."""
    if not stats:
        return []
    model_stats = stats.get("model_b") or {}
    means = model_stats.get("class_means") or {}
    if not means:
        return []
    phish_means, legit_means = means["phishing"], means["legit"]
    importance = dict(zip(model_stats["features"], model_stats["importances"]))
    target = phish_means if label == LABEL_PHISH else legit_means

    ranked = []
    for feature, value in feats.items():
        d_phish = abs(value - phish_means[feature])
        d_legit = abs(value - legit_means[feature])
        if abs(d_phish - d_legit) <= 0.05 * (d_phish + d_legit):
            impact = "netral"
        elif d_phish < d_legit:
            impact = "meningkatkan risiko"
        else:
            impact = "menurunkan risiko"
        ranked.append((importance.get(feature, 0.0) * abs(value - target[feature]), feature, value, impact))

    ranked.sort(reverse=True)
    return [{"feature": f, "value": float(v), "impact": i} for _, f, v, i in ranked[:5]]


def predict_url(url: str) -> dict:
    """Prediksi satu URL. Raise ValueError bila URL tidak valid (API memetakannya ke 400)."""
    url = _validate(url)
    pipe, tld, stats = _load()  # sebelum timer, agar inference_ms panggilan pertama akurat

    started = time.perf_counter()
    feats = extract_features(url, tld["map"], tld["default"])
    frame = pd.DataFrame([feats], columns=URL_FEATURES, dtype=float)
    proba = pipe.predict_proba(frame.to_numpy(dtype=np.float32))[0]
    probability = float(proba[list(pipe.classes_).index(LABEL_PHISH)])  # = kolom ke-0 selama kelas [0, 1]
    elapsed_ms = (time.perf_counter() - started) * 1000

    label = LABEL_PHISH if probability >= THRESHOLD else LABEL_LEGIT
    return {
        "url": url,
        "label": label,
        "label_name": "PHISHING" if label == LABEL_PHISH else "LEGITIMATE",
        "probability": round(probability, 4),
        "inference_ms": round(elapsed_ms, 2),
        "top_features": _top_features(feats, label, stats),
    }
