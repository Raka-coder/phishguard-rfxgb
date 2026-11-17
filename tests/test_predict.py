"""Kontrak inference Model B: arah label, validasi input, bentuk output, dan determinisme."""

import os

import pytest

import src.predict as predict
from src.config import LABEL_LEGIT, LABEL_PHISH, THRESHOLD, URL_FEATURES
from src.denylist import reset_cache
from src.feature_utils import extract_features, to_frame
from src.reputation import is_trusted, is_user_content

PHISHING_IP_URL = "http://192.168.0.1/paypal-login-verify.xyz"
LEGIT_URL = "https://www.wikipedia.org"


def _p_phishing(url: str) -> float:
    """P(phishing) langsung dari pipeline, untuk memverifikasi arah kolom probabilitas."""
    pipe, tld, _ = predict._load()
    frame = to_frame(url, tld["map"], tld["default"])
    return float(pipe.predict_proba(frame.to_numpy(dtype="float32"))[0][0])


def test_label_constants():
    assert LABEL_PHISH == 0
    assert LABEL_LEGIT == 1


def test_probability_is_first_proba_column():
    result = predict.predict_url(PHISHING_IP_URL)
    assert result["probability"] == pytest.approx(_p_phishing(PHISHING_IP_URL), abs=1e-4)


def test_ip_host_phishing_url():
    result = predict.predict_url(PHISHING_IP_URL)
    assert result["probability"] > 0.8
    assert result["label"] == LABEL_PHISH
    assert result["label_name"] == "SUSPICIOUS"
    assert result["verdict"] == "SUSPICIOUS"
    assert result["risk_level"] == "tinggi"
    assert result["decision_source"] == "model"


def test_wikipedia_is_legitimate():
    result = predict.predict_url(LEGIT_URL)
    assert result["verdict"] == "LEGITIMATE"
    assert result["decision_source"] == "allowlist"
    assert result["risk_level"] == "rendah"
    assert result["probability"] is None
    assert result["top_features"] == []
    assert result["label"] == LABEL_LEGIT
    assert result["label_name"] == "LEGITIMATE"
    assert [item["layer"] for item in result["trail"]] == ["denylist", "allowlist"]


def test_model_path_legitimate_url():
    result = predict.predict_url("https://www.bbc.com")
    assert result["verdict"] == "LEGITIMATE"
    assert result["decision_source"] == "model"
    assert result["risk_level"] == "rendah"
    assert result["probability"] is not None
    assert result["probability"] < 0.2
    assert result["label"] == LABEL_LEGIT


def test_empty_url_raises():
    for value in ("", "   "):
        with pytest.raises(ValueError):
            predict.predict_url(value)


def test_non_string_raises():
    for value in (None, 123, 4.5, b"https://example.com"):
        with pytest.raises(ValueError):
            predict.predict_url(value)


def test_missing_scheme_raises():
    with pytest.raises(ValueError):
        predict.predict_url("www.example.com")


def test_ftp_scheme_raises():
    with pytest.raises(ValueError):
        predict.predict_url("ftp://example.com/file")


def test_empty_host_raises():
    with pytest.raises(ValueError):
        predict.predict_url("https://")


def test_very_long_url_does_not_crash():
    result = predict.predict_url("https://example.com/" + "a" * 2000)
    assert result["label"] in (LABEL_PHISH, LABEL_LEGIT)
    assert 0 <= result["probability"] <= 1


def test_unicode_url_does_not_crash():
    result = predict.predict_url("https://exämple.com/path?q=ü&x=1")
    assert result["label"] in (LABEL_PHISH, LABEL_LEGIT)
    assert 0 <= result["probability"] <= 1


def test_short_normal_url_output_contract():
    result = predict.predict_url("https://example.com")
    assert set(result) == {
        "url",
        "label",
        "label_name",
        "verdict",
        "risk_level",
        "probability",
        "inference_ms",
        "top_features",
        "decision_source",
        "reason",
        "trail",
    }
    assert result["url"] == "https://example.com"
    assert result["label"] == (LABEL_PHISH if result["probability"] >= THRESHOLD else LABEL_LEGIT)
    assert result["label_name"] in {"PHISHING", "SUSPICIOUS", "LEGITIMATE"}
    assert result["risk_level"] in {"tinggi", "sedang", "rendah"}


def test_trail_contract():
    result = predict.predict_url("https://www.bbc.com")
    assert [item["layer"] for item in result["trail"]] == [
        "denylist",
        "allowlist",
        "model_b",
        "model_c",
        "shortener",
    ]
    for item in result["trail"]:
        assert set(item) == {"layer", "result", "detail"}
        assert item["detail"]


def test_no_phishing_verdict_from_models():
    for url in (PHISHING_IP_URL, "https://bit.ly/abc123", "http://example.com/login?id=1"):
        assert predict.predict_url(url)["verdict"] != "PHISHING"


def test_shortener_trail_marks_cocok():
    result = predict.predict_url("https://bit.ly/abc123")
    entry = next(item for item in result["trail"] if item["layer"] == "shortener")
    assert entry["result"] == "cocok"
    assert result["verdict"] == "SUSPICIOUS"


def test_model_c_missing_falls_back_to_model_b(monkeypatch):
    monkeypatch.setattr(predict, "_MODEL_C", None)
    monkeypatch.setattr(predict, "_MODEL_C_TRIED", True)
    result = predict.predict_url(PHISHING_IP_URL)
    assert result["verdict"] == "SUSPICIOUS"
    assert result["risk_level"] == "tinggi"
    entry = next(item for item in result["trail"] if item["layer"] == "model_c")
    assert entry["result"] == "tidak tersedia"


def test_model_c_load_is_safe_when_artifact_missing(monkeypatch, tmp_path):
    monkeypatch.setattr(predict, "MODEL_C_PATH", tmp_path / "tidak-ada.pkl")
    monkeypatch.setattr(predict, "TLD_PROBS_HOST_PATH", tmp_path / "tidak-ada.json")
    monkeypatch.setattr(predict, "_MODEL_C", None)
    monkeypatch.setattr(predict, "_MODEL_C_TRIED", False)
    assert predict._load_model_c() is None


def test_band_and_decide_rules():
    assert predict._band(0.70) == "tinggi"
    assert predict._band(0.50) == "sedang"
    assert predict._band(0.30) == "rendah"

    assert predict._decide(0.90, 0.80, False)[:2] == ("SUSPICIOUS", "tinggi")
    assert predict._decide(0.10, 0.20, False)[:2] == ("LEGITIMATE", "rendah")
    verdict, risk, source, reason = predict._decide(0.90, 0.20, False)
    assert (verdict, risk, source) == ("SUSPICIOUS", "sedang", "model")
    assert "tidak dapat memastikan" in reason
    assert predict._decide(0.90, 0.80, True)[:2] == ("SUSPICIOUS", "tinggi")
    assert predict._decide(0.10, 0.20, True)[:3] == ("SUSPICIOUS", "sedang", "shortener")
    assert predict._decide(0.10, None, False)[:2] == ("LEGITIMATE", "rendah")
    assert predict._decide(0.90, None, False)[:2] == ("SUSPICIOUS", "tinggi")


def test_denylist_layer_returns_phishing(tmp_path, monkeypatch):
    d = tmp_path / "feeds"
    d.mkdir()
    (d / "openphish-1.txt").write_text("https://evil.example/phish\n", encoding="utf-8")
    monkeypatch.setenv("PHISHGUARD_FEED_DIR", str(d))
    monkeypatch.setenv("PHISHGUARD_FEED_MAX_AGE_HOURS", "24")
    reset_cache()
    result = predict.predict_url("https://evil.example/phish")
    assert result["verdict"] == "PHISHING"
    assert result["decision_source"] == "denylist"
    assert result["risk_level"] == "tinggi"
    assert result["probability"] is None
    assert result["trail"][0]["layer"] == "denylist"
    assert result["trail"][0]["result"] == "cocok"


def test_top_features_contract():
    result = predict.predict_url(PHISHING_IP_URL)
    assert 0 < len(result["top_features"]) <= 5
    for item in result["top_features"]:
        assert set(item) == {"feature", "value", "impact"}
        assert item["feature"] in URL_FEATURES
        assert isinstance(item["value"], float)
        assert item["impact"] in {"meningkatkan risiko", "menurunkan risiko", "netral"}


def test_probability_in_unit_range():
    for url in (PHISHING_IP_URL, "https://www.bbc.com", "http://example.com/login?id=1"):
        result = predict.predict_url(url)
        if result["probability"] is not None:
            assert 0 <= result["probability"] <= 1


def test_inference_ms_measured():
    assert predict.predict_url(LEGIT_URL)["inference_ms"] > 0


def test_extract_features_is_deterministic():
    assert extract_features(PHISHING_IP_URL) == extract_features(PHISHING_IP_URL)


def test_predict_url_is_deterministic():
    first = predict.predict_url(PHISHING_IP_URL)
    second = predict.predict_url(PHISHING_IP_URL)
    assert first["probability"] == second["probability"]
    assert first["label"] == second["label"]
    assert first["top_features"] == second["top_features"]
    assert first["trail"] == second["trail"]


def test_allowlist_github():
    result = predict.predict_url("https://github.com/Raka-coder/phishguard-rfxgb")
    assert result["decision_source"] == "allowlist"
    assert result["verdict"] == "LEGITIMATE"
    assert result["probability"] is None
    assert result["top_features"] == []
    assert result["label"] == LABEL_LEGIT


def test_vercel_user_content_not_allowlisted():
    assert not is_trusted("phishing-test.vercel.app")
    assert is_user_content("phishing-test.vercel.app")
    result = predict.predict_url("https://phishing-test.vercel.app/login")
    assert result["decision_source"] != "allowlist"


def test_missing_stats_keeps_prediction_working(monkeypatch, tmp_path):
    monkeypatch.setattr(predict, "STATS_PATH", tmp_path / "stats-hilang.json")
    monkeypatch.setattr(predict, "_ARTIFACTS", None)
    result = predict.predict_url("https://www.bbc.com")
    assert result["top_features"] == []
    assert result["label"] in (LABEL_PHISH, LABEL_LEGIT)
