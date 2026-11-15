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
    THRESHOLD_PHISHING,
    THRESHOLD_SUSPICIOUS,
    TLD_PROBS_PATH,
    URL_FEATURES,
    VERDICT_LEGITIMATE,
    VERDICT_PHISHING,
    VERDICT_SUSPICIOUS,
)
from src.feature_utils import extract_features
from src.reputation import is_trusted

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


def _classify(probability: float, trusted: bool) -> tuple[str, str, str]:
    """Keputusan user-facing dari P(phishing) dan status allowlist."""
    if trusted:
        return (
            VERDICT_LEGITIMATE,
            "allowlist",
            "Domain berada dalam daftar domain tepercaya (offline).",
        )
    if probability >= THRESHOLD_PHISHING:
        return (
            VERDICT_PHISHING,
            "model",
            f"Skor phishing {probability:.2f} >= {THRESHOLD_PHISHING:.2f} (ambang phishing).",
        )
    if probability >= THRESHOLD_SUSPICIOUS:
        return (
            VERDICT_SUSPICIOUS,
            "uncertainty",
            f"Skor phishing {probability:.2f} berada di zona tidak pasti "
            f"({THRESHOLD_SUSPICIOUS:.2f}-{THRESHOLD_PHISHING:.2f}); perlu verifikasi manual.",
        )
    return (
        VERDICT_LEGITIMATE,
        "model",
        f"Skor phishing {probability:.2f} < {THRESHOLD_SUSPICIOUS:.2f}.",
    )
def predict_url(url: str) -> dict:
    """Prediksi satu URL. Raise ValueError bila URL tidak valid (API memetakannya ke 400).

    Alur keputusan (user-facing `verdict`):
      1. Allowlist domain tepercaya (offline) -> LEGITIMATE, decision_source="allowlist".
      2. Model XGBoost -> P(phishing); P >= 0.65 -> PHISHING (model);
         0.40 <= P < 0.65 -> SUSPICIOUS (uncertainty); P < 0.40 -> LEGITIMATE (model).

    `label` (0/1) tetap mengikuti THRESHOLD (0.5) agar kompatibel dengan
    metrik dan test lama; `verdict` adalah keputusan user-facing yang lebih kaya.
    """
    url = _validate(url)
    pipe, tld, stats = _load()  # sebelum timer, agar inference_ms panggilan pertama akurat

    started = time.perf_counter()
    host = (urlsplit(url).hostname or "").lower()

    if is_trusted(host):
        elapsed_ms = (time.perf_counter() - started) * 1000
        return {
            "url": url,
            "label": LABEL_LEGIT,
            "label_name": "LEGITIMATE",
            "verdict": VERDICT_LEGITIMATE,
            "probability": None,
            "inference_ms": round(elapsed_ms, 2),
            "top_features": [],
            "decision_source": "allowlist",
            "reason": f"Domain {host} berada dalam daftar domain tepercaya (offline).",
        }

    feats = extract_features(url, tld["map"], tld["default"])
    frame = pd.DataFrame([feats], columns=URL_FEATURES, dtype=float)
    proba = pipe.predict_proba(frame.to_numpy(dtype=np.float32))[0]
    probability = float(proba[list(pipe.classes_).index(LABEL_PHISH)])  # = kolom ke-0 selama kelas [0, 1]
    elapsed_ms = (time.perf_counter() - started) * 1000

    verdict, decision_source, reason = _classify(probability, False)

    label = LABEL_PHISH if probability >= THRESHOLD else LABEL_LEGIT
    if verdict == VERDICT_PHISHING:
        label_name = "PHISHING"
    elif verdict == VERDICT_SUSPICIOUS:
        label_name = "SUSPICIOUS"
    else:
        label_name = "LEGITIMATE"

    return {
        "url": url,
        "label": label,
        "label_name": label_name,
        "verdict": verdict,
        "probability": round(probability, 4),
        "inference_ms": round(elapsed_ms, 2),
        "top_features": _top_features(feats, label, stats),
        "decision_source": decision_source,
        "reason": reason,
    }
