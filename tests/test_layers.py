"""Kontrak per lapisan L0-L4 yang belum tercakup tes lama (T30).

Tes lama sudah menutup: GSB cocok, timeout, flag mati, denylist ok/basi/hilang,
allowlist github, band model nyata, dan determinisme. File ini hanya mengisi
celah: trail saat GSB tidak cocok/gagal/off, zona band deterministik dengan
pipeline palsu, varian allowlist, dan shortener.
"""

import os
import subprocess
import sys
from pathlib import Path

import httpx
import numpy as np
import pytest

import src.google_sb as google_sb
import src.predict as predict
from src import config as cfg
from src.denylist import reset_cache

ROOT = Path(__file__).resolve().parents[1]


class _FakePipe:
    """Pipeline palsu: skor P(phishing) konstan, tanpa artefak nyata."""

    classes_ = np.array([0, 1])

    def __init__(self, probability: float) -> None:
        self.probability = probability

    def predict_proba(self, frame) -> np.ndarray:
        rows = len(frame)
        return np.tile([self.probability, 1 - self.probability], (rows, 1))


def _fake_model(monkeypatch, probability: float) -> None:
    monkeypatch.setattr(predict, "_load", lambda: (_FakePipe(probability), {"map": {}, "default": 0.5}, {}))
    monkeypatch.setattr(predict, "_load_model_c", lambda: None)


def _enable_google(monkeypatch) -> None:
    monkeypatch.setattr(cfg, "USE_GOOGLE", True)
    monkeypatch.setattr(cfg, "GOOGLE_API_KEY", "dummy-key")


class _NoMatch:
    status_code = 200

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict:
        return {}


# --- L0: Google Safe Browsing -------------------------------------------------
def test_google_no_match_is_recorded_then_offline_layers_run(monkeypatch):
    _enable_google(monkeypatch)
    monkeypatch.setattr(google_sb.httpx, "post", lambda *a, **k: _NoMatch())
    _fake_model(monkeypatch, 0.10)

    result = predict.predict_url("https://example.com")

    assert result["decision_source"] != "google_safe_browsing"
    assert result["trail"][0]["layer"] == "google_sb"
    assert result["trail"][0]["result"] == "tidak cocok"
    assert result["trail"][1]["layer"] == "denylist"


def test_google_http_error_is_failsafe(monkeypatch):
    _enable_google(monkeypatch)

    def _boom(*args, **kwargs):
        request = httpx.Request("POST", google_sb.GOOGLE_SB_ENDPOINT)
        raise httpx.HTTPStatusError("500", request=request, response=httpx.Response(500, request=request))

    monkeypatch.setattr(google_sb.httpx, "post", _boom)
    _fake_model(monkeypatch, 0.10)

    assert google_sb.check_google_safe_browsing("https://example.com") is None
    result = predict.predict_url("https://example.com")
    assert result["trail"][0]["result"] == "tidak cocok"
    assert result["verdict"] != "PHISHING"


def test_google_disabled_leaves_no_trail_entry(monkeypatch):
    _fake_model(monkeypatch, 0.10)

    result = predict.predict_url("https://example.com")

    assert all(item["layer"] != "google_sb" for item in result["trail"])


def test_google_flag_on_without_key_is_not_called(monkeypatch):
    monkeypatch.setattr(cfg, "USE_GOOGLE", True)
    monkeypatch.setattr(cfg, "GOOGLE_API_KEY", "")
    _fake_model(monkeypatch, 0.10)

    assert google_sb.google_enabled() is False
    result = predict.predict_url("https://example.com")
    assert all(item["layer"] != "google_sb" for item in result["trail"])


def test_google_off_by_default_without_env():
    """Produksi tanpa env: L0 mati walau .env di mesin berisi flag true."""
    env = {**os.environ, "PHISHGUARD_USE_GOOGLE": "", "PHISHGUARD_GOOGLE_API_KEY": ""}
    code = "from src import config; print(config.USE_GOOGLE, bool(config.GOOGLE_API_KEY))"
    out = subprocess.run(
        [sys.executable, "-c", code], cwd=ROOT, env=env, capture_output=True, text=True, timeout=180
    )
    assert out.returncode == 0, out.stderr
    assert out.stdout.strip() == "False False"


def test_trail_order_with_google_enabled(monkeypatch):
    _enable_google(monkeypatch)
    monkeypatch.setattr(google_sb.httpx, "post", lambda *a, **k: _NoMatch())
    _fake_model(monkeypatch, 0.10)

    result = predict.predict_url("https://example.com")

    assert [item["layer"] for item in result["trail"]] == [
        "google_sb",
        "denylist",
        "allowlist",
        "model_b",
        "model_c",
        "shortener",
    ]
    for item in result["trail"]:
        assert set(item) == {"layer", "result", "detail"}
        assert item["detail"]


def test_deterministic_with_google_mocked(monkeypatch):
    _enable_google(monkeypatch)
    monkeypatch.setattr(google_sb.httpx, "post", lambda *a, **k: _NoMatch())
    _fake_model(monkeypatch, 0.30)

    first = predict.predict_url("https://example.com/path?q=1")
    second = predict.predict_url("https://example.com/path?q=1")

    first.pop("inference_ms")
    second.pop("inference_ms")
    assert first == second


# --- L1: denylist -------------------------------------------------------------
def test_stale_feed_is_skipped_with_trail_entry(tmp_path, monkeypatch):
    feed = tmp_path / "openphish-stale.txt"
    feed.write_text("https://evil.example/phish\n", encoding="utf-8")
    old = 0  # 1970: pasti basi
    os.utime(feed, (old, old))
    monkeypatch.setenv("PHISHGUARD_FEED_DIR", str(tmp_path))
    monkeypatch.setenv("PHISHGUARD_FEED_MAX_AGE_HOURS", "24")
    reset_cache()
    _fake_model(monkeypatch, 0.10)

    try:
        result = predict.predict_url("https://evil.example/phish")
    finally:
        reset_cache()

    assert result["verdict"] != "PHISHING"
    entry = next(item for item in result["trail"] if item["layer"] == "denylist")
    assert entry["result"] == "dilewati"


# --- L2: allowlist ------------------------------------------------------------
@pytest.mark.parametrize("url", ["https://github.com/x", "https://www.github.com/x"])
def test_allowlist_accepts_www_variant(monkeypatch, url):
    _fake_model(monkeypatch, 0.90)  # model tidak boleh dipakai

    result = predict.predict_url(url)

    assert result["decision_source"] == "allowlist"
    assert result["verdict"] == "LEGITIMATE"
    assert result["probability"] is None
    assert [item["layer"] for item in result["trail"]] == ["denylist", "allowlist"]


@pytest.mark.parametrize(
    "url",
    [
        "https://gist.github.com/x",
        "https://evil-github.com/x",
        "https://foo.vercel.app/x",
        "https://phishing-test.vercel.app/login",
    ],
)
def test_allowlist_rejects_lookalikes_and_user_content(monkeypatch, url):
    _fake_model(monkeypatch, 0.10)

    result = predict.predict_url(url)

    assert result["decision_source"] != "allowlist"
    entry = next(item for item in result["trail"] if item["layer"] == "allowlist")
    assert entry["result"] == "tidak cocok"


# --- L3: Model B + C dan zona band -------------------------------------------
@pytest.mark.parametrize(
    ("probability", "verdict", "risk_level", "label"),
    [
        (0.70, "SUSPICIOUS", "tinggi", 0),
        (0.65, "SUSPICIOUS", "tinggi", 0),
        (0.50, "SUSPICIOUS", "sedang", 0),
        (0.40, "SUSPICIOUS", "sedang", 1),
        (0.39, "LEGITIMATE", "rendah", 1),
        (0.10, "LEGITIMATE", "rendah", 1),
    ],
)
def test_model_band_zones_and_label_threshold(monkeypatch, probability, verdict, risk_level, label):
    _fake_model(monkeypatch, probability)

    result = predict.predict_url("https://example.com")

    assert (result["verdict"], result["risk_level"]) == (verdict, risk_level)
    assert result["decision_source"] == "model"
    assert result["label"] == label  # label tetap dari THRESHOLD 0.5
    assert result["verdict"] != "PHISHING"  # model tidak pernah memvonis PHISHING


# --- L4: shortener ------------------------------------------------------------
@pytest.mark.parametrize("url", ["https://bit.ly/abc123", "https://tinyurl.com/xyz"])
def test_shortener_raises_legitimate_to_suspicious(monkeypatch, url):
    _fake_model(monkeypatch, 0.10)

    result = predict.predict_url(url)

    assert (result["verdict"], result["risk_level"]) == ("SUSPICIOUS", "sedang")
    assert result["decision_source"] == "shortener"
    entry = next(item for item in result["trail"] if item["layer"] == "shortener")
    assert entry["result"] == "cocok"


def test_shortener_does_not_downgrade_high_risk(monkeypatch):
    _fake_model(monkeypatch, 0.90)

    result = predict.predict_url("https://bit.ly/abc123")

    assert (result["verdict"], result["risk_level"]) == ("SUSPICIOUS", "tinggi")
    assert result["decision_source"] == "model"
