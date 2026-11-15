"""Kontrak inference Model B: arah label, validasi input, bentuk output, dan determinisme."""

import pytest

import src.predict as predict
from src.config import LABEL_LEGIT, LABEL_PHISH, THRESHOLD, URL_FEATURES
from src.feature_utils import extract_features, to_frame

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
    assert result["label_name"] == "PHISHING"


def test_wikipedia_is_legitimate():
    result = predict.predict_url(LEGIT_URL)
    assert result["probability"] < 0.2
    assert result["label"] == LABEL_LEGIT
    assert result["label_name"] == "LEGITIMATE"


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
    assert set(result) == {"url", "label", "label_name", "probability", "inference_ms", "top_features"}
    assert result["url"] == "https://example.com"
    assert result["label"] == (LABEL_PHISH if result["probability"] >= THRESHOLD else LABEL_LEGIT)
    assert result["label_name"] in {"PHISHING", "LEGITIMATE"}


def test_top_features_contract():
    result = predict.predict_url(PHISHING_IP_URL)
    assert 0 < len(result["top_features"]) <= 5
    for item in result["top_features"]:
        assert set(item) == {"feature", "value", "impact"}
        assert item["feature"] in URL_FEATURES
        assert isinstance(item["value"], float)
        assert item["impact"] in {"meningkatkan risiko", "menurunkan risiko", "netral"}


def test_probability_in_unit_range():
    for url in (PHISHING_IP_URL, LEGIT_URL, "http://example.com/login?id=1"):
        assert 0 <= predict.predict_url(url)["probability"] <= 1


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


def test_missing_stats_keeps_prediction_working(monkeypatch, tmp_path):
    monkeypatch.setattr(predict, "STATS_PATH", tmp_path / "stats-hilang.json")
    monkeypatch.setattr(predict, "_ARTIFACTS", None)
    result = predict.predict_url(LEGIT_URL)
    assert result["top_features"] == []
    assert result["label"] in (LABEL_PHISH, LABEL_LEGIT)
