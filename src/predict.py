"""Inference berlapis: denylist (belum ada) -> allowlist -> Model B+C -> shortener.

Model tunggal tidak pernah memvonis PHISHING; PHISHING hanya dari denylist.
Setiap panggilan mengembalikan `trail` {layer, result, detail} dan `risk_level`.
"""

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
    ROOT,
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
from src.features_host import to_host_frame
from src.reputation import is_shortener, is_trusted

_ALLOWED_SCHEMES = {"http", "https"}
_ARTIFACTS: tuple | None = None

# Artefak Model C dibuat ulang oleh `uv run python scripts/train_t25.py` (gitignored).
# Bila tidak ada, lapisan C dilewati dan vonis memakai band Model B saja.
MODEL_C_PATH = ROOT / "models" / "experimental" / "C_host.pkl"
TLD_PROBS_HOST_PATH = ROOT / "models" / "experimental" / "tld_probs_host.json"

_MODEL_C: tuple | None = None
_MODEL_C_TRIED = False


def _load() -> tuple:
    """Muat pipeline Model B + lookup TLD + stats sekali (lazy singleton)."""
    global _ARTIFACTS
    if _ARTIFACTS is None:
        if not MODEL_B_PATH.exists():
            raise RuntimeError(f"Model belum ada: {MODEL_B_PATH}. Jalankan `uv run python src/train.py` dulu.")
        pipe = joblib.load(MODEL_B_PATH)
        tld = json.loads(TLD_PROBS_PATH.read_text(encoding="utf-8")) if TLD_PROBS_PATH.exists() else {"default": 0.5, "map": {}}
        stats = json.loads(STATS_PATH.read_text(encoding="utf-8")) if STATS_PATH.exists() else {}
        _ARTIFACTS = (pipe, tld, stats)
    return _ARTIFACTS


def _load_model_c() -> tuple | None:
    """Muat Model C + tabel TLD host sekali; None bila artefak tidak ada/rusak."""
    global _MODEL_C, _MODEL_C_TRIED
    if not _MODEL_C_TRIED:
        _MODEL_C_TRIED = True
        try:
            pipe = joblib.load(MODEL_C_PATH)
            tld = json.loads(TLD_PROBS_HOST_PATH.read_text(encoding="utf-8"))
            _MODEL_C = (pipe, tld)
        except Exception:  # artefak hilang/rusak: lapisan C opsional, jangan gagalkan request
            _MODEL_C = None
    return _MODEL_C


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


def _model_c_probability(url: str) -> float | None:
    loaded = _load_model_c()
    if loaded is None:
        return None
    pipe, tld = loaded
    frame = to_host_frame(url, tld.get("map") or {}, float(tld.get("default", 0.5)), strip_www=True)
    proba = pipe.predict_proba(frame.to_numpy(dtype=np.float32))[0]
    return float(proba[list(pipe.classes_).index(LABEL_PHISH)])


def _band(probability: float) -> str:
    """Zona skor yang sama untuk Model B dan Model C."""
    if probability >= THRESHOLD_PHISHING:
        return "tinggi"
    if probability < THRESHOLD_SUSPICIOUS:
        return "rendah"
    return "sedang"


def _apply_shortener(verdict: str, risk_level: str, reason: str, shortener: bool) -> tuple[str, str, str, str]:
    """Shortener hanya menaikkan LEGITIMATE; tidak menurunkan SUSPICIOUS tinggi."""
    if shortener and verdict == VERDICT_LEGITIMATE:
        return (
            VERDICT_SUSPICIOUS,
            "sedang",
            "shortener",
            "Host adalah layanan pemendek URL; tujuan aslinya tidak diperiksa. Model tidak dapat memastikan.",
        )
    return verdict, risk_level, "model", reason


def _decide(p_b: float, p_c: float | None, shortener: bool) -> tuple[str, str, str, str]:
    """Vonis user-facing dari dua skor model: (verdict, risk_level, decision_source, reason)."""
    band_b = _band(p_b)
    band_c = _band(p_c) if p_c is not None else None

    if band_c is None:
        reason = f"Model C tidak tersedia; skor phishing Model B {p_b:.2f}."
        if band_b == "tinggi":
            return _apply_shortener(VERDICT_SUSPICIOUS, "tinggi", reason, shortener)
        if band_b == "sedang":
            return _apply_shortener(VERDICT_SUSPICIOUS, "sedang", reason, shortener)
        return _apply_shortener(VERDICT_LEGITIMATE, "rendah", reason, shortener)

    if band_b == band_c == "tinggi":
        reason = f"Model B ({p_b:.2f}) dan Model C ({p_c:.2f}) sama-sama tinggi; model tidak dapat memastikan."
        return _apply_shortener(VERDICT_SUSPICIOUS, "tinggi", reason, shortener)
    if band_b == band_c == "rendah":
        reason = f"Model B ({p_b:.2f}) dan Model C ({p_c:.2f}) sama-sama rendah."
        return _apply_shortener(VERDICT_LEGITIMATE, "rendah", reason, shortener)
    reason = f"Model B ({p_b:.2f}) dan Model C ({p_c:.2f}) berbeda; model tidak dapat memastikan."
    return _apply_shortener(VERDICT_SUSPICIOUS, "sedang", reason, shortener)


def predict_url(url: str) -> dict:
    """Prediksi satu URL. Raise ValueError bila URL tidak valid (API memetakannya ke 400).

    Alur vonis (berhenti di lapisan pertama yang memutuskan):
      1. Denylist feed -> PHISHING (belum diimplementasikan, dilaporkan "dilewati").
      2. Allowlist domain tepercaya -> LEGITIMATE.
      3. Model B + Model C: keduanya tinggi -> SUSPICIOUS/tinggi; keduanya rendah ->
         LEGITIMATE/rendah; selain itu SUSPICIOUS/sedang.
      4. Shortener -> SUSPICIOUS/sedang bila langkah 3 masih LEGITIMATE.

    `label` (0/1) tetap mengikuti THRESHOLD (0.5) pada skor Model B agar kompatibel
    dengan metrik dan test lama; `verdict` adalah keputusan user-facing.
    """
    url = _validate(url)
    pipe, tld, stats = _load()  # sebelum timer, agar inference_ms panggilan pertama akurat

    started = time.perf_counter()
    host = (urlsplit(url).hostname or "").lower()
    trail = [
        {
            "layer": "denylist",
            "result": "dilewati",
            "detail": "Feed denylist belum tersedia (T19 belum dikerjakan).",
        }
    ]

    if is_trusted(host):
        trail.append({"layer": "allowlist", "result": "cocok", "detail": f"Domain {host} ada di allowlist tepercaya."})
        elapsed_ms = (time.perf_counter() - started) * 1000
        return {
            "url": url,
            "label": LABEL_LEGIT,
            "label_name": VERDICT_LEGITIMATE,
            "verdict": VERDICT_LEGITIMATE,
            "risk_level": "rendah",
            "probability": None,
            "inference_ms": round(elapsed_ms, 2),
            "top_features": [],
            "decision_source": "allowlist",
            "reason": f"Domain {host} berada dalam daftar domain tepercaya (offline).",
            "trail": trail,
        }

    trail.append({"layer": "allowlist", "result": "tidak cocok", "detail": "Domain tidak ada di allowlist."})

    feats = extract_features(url, tld["map"], tld["default"])
    frame = pd.DataFrame([feats], columns=URL_FEATURES, dtype=float)
    proba = pipe.predict_proba(frame.to_numpy(dtype=np.float32))[0]
    probability = float(proba[list(pipe.classes_).index(LABEL_PHISH)])  # = kolom ke-0 selama kelas [0, 1]
    trail.append({"layer": "model_b", "result": _band(probability), "detail": f"Skor phishing Model B {probability:.2f}."})

    prob_c = _model_c_probability(url)
    if prob_c is None:
        trail.append(
            {
                "layer": "model_c",
                "result": "tidak tersedia",
                "detail": "Artefak Model C tidak dimuat; vonis memakai Model B saja.",
            }
        )
    else:
        trail.append({"layer": "model_c", "result": _band(prob_c), "detail": f"Skor phishing Model C {prob_c:.2f}."})

    shortener = is_shortener(host)
    trail.append(
        {
            "layer": "shortener",
            "result": "cocok" if shortener else "tidak cocok",
            "detail": f"Host {host} ada di daftar shortener." if shortener else "Host bukan layanan pemendek URL.",
        }
    )

    verdict, risk_level, decision_source, reason = _decide(probability, prob_c, shortener)
    elapsed_ms = (time.perf_counter() - started) * 1000

    label = LABEL_PHISH if probability >= THRESHOLD else LABEL_LEGIT

    return {
        "url": url,
        "label": label,
        "label_name": verdict,
        "verdict": verdict,
        "risk_level": risk_level,
        "probability": round(probability, 4),
        "inference_ms": round(elapsed_ms, 2),
        "top_features": _top_features(feats, label, stats),
        "decision_source": decision_source,
        "reason": reason,
        "trail": trail,
    }
