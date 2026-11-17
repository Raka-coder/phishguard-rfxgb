"""Kontrak API: POST /check, GET /health, error 400, dan CORS."""

import os

from fastapi.testclient import TestClient

from api.main import app
from src.denylist import reset_cache

client = TestClient(app)

PHISHING_IP_URL = "http://192.168.0.1/paypal-login-verify.xyz"
LEGIT_URL = "https://www.wikipedia.org"


def test_health_reports_model_loaded():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "model_loaded": True}


def test_check_legitimate_200():
    response = client.post("/check", json={"url": LEGIT_URL})
    assert response.status_code == 200
    body = response.json()
    assert body["label"] == 1
    assert body["label_name"] == "LEGITIMATE"
    assert body["verdict"] == "LEGITIMATE"
    assert body["risk_level"] == "rendah"
    assert body["decision_source"] == "allowlist"
    assert body["probability"] is None
    assert body["top_features"] == []
    assert [item["layer"] for item in body["trail"]] == ["denylist", "allowlist"]
    assert isinstance(body["reason"], str)
    assert isinstance(body["inference_ms"], (int, float))
    assert set(body) == {
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


def test_check_model_path_legitimate_200():
    response = client.post("/check", json={"url": "https://www.bbc.com"})
    assert response.status_code == 200
    body = response.json()
    assert body["label_name"] == "LEGITIMATE"
    assert body["verdict"] == "LEGITIMATE"
    assert body["risk_level"] == "rendah"
    assert body["decision_source"] == "model"
    assert body["probability"] is not None
    assert 0 <= body["probability"] <= 1


def test_check_suspicious_200():
    response = client.post("/check", json={"url": PHISHING_IP_URL})
    assert response.status_code == 200
    body = response.json()
    assert body["label"] == 0
    assert body["label_name"] == "SUSPICIOUS"
    assert body["verdict"] == "SUSPICIOUS"
    assert body["risk_level"] == "tinggi"
    assert body["decision_source"] == "model"
    assert body["probability"] > 0.8
    assert 0 <= body["probability"] <= 1
    assert isinstance(body["reason"], str)
    assert isinstance(body["inference_ms"], (int, float))


def test_trail_entries_shape():
    body = client.post("/check", json={"url": PHISHING_IP_URL}).json()
    assert [item["layer"] for item in body["trail"]] == [
        "denylist",
        "allowlist",
        "model_b",
        "model_c",
        "shortener",
    ]
    for item in body["trail"]:
        assert set(item) == {"layer", "result", "detail"}
        assert isinstance(item["result"], str)
        assert isinstance(item["detail"], str)


def test_model_never_returns_phishing():
    for url in (PHISHING_IP_URL, "https://bit.ly/abc123", "https://www.bbc.com"):
        assert client.post("/check", json={"url": url}).json()["verdict"] != "PHISHING"


def test_denylist_returns_phishing(tmp_path, monkeypatch):
    d = tmp_path / "feeds"
    d.mkdir()
    (d / "openphish-1.txt").write_text("https://evil.example/phish\n", encoding="utf-8")
    monkeypatch.setenv("PHISHGUARD_FEED_DIR", str(d))
    monkeypatch.setenv("PHISHGUARD_FEED_MAX_AGE_HOURS", "24")
    reset_cache()
    response = client.post("/check", json={"url": "https://evil.example/phish"})
    assert response.status_code == 200
    body = response.json()
    assert body["verdict"] == "PHISHING"
    assert body["decision_source"] == "denylist"
    assert body["risk_level"] == "tinggi"
    assert body["probability"] is None


def test_check_top_features_shape():
    body = client.post("/check", json={"url": PHISHING_IP_URL}).json()
    assert 0 < len(body["top_features"]) <= 5
    for item in body["top_features"]:
        assert set(item) == {"feature", "value", "impact"}


def test_missing_url_field_400():
    response = client.post("/check", json={})
    assert response.status_code == 400
    assert "url" in response.json()["detail"]


def test_non_string_url_400():
    response = client.post("/check", json={"url": 123})
    assert response.status_code == 400


def test_empty_url_400_keeps_original_message():
    response = client.post("/check", json={"url": ""})
    assert response.status_code == 400
    assert response.json()["detail"] == "URL tidak valid: input kosong"


def test_invalid_scheme_400_keeps_original_message():
    response = client.post("/check", json={"url": "ftp://example.com/file"})
    assert response.status_code == 400
    assert response.json()["detail"] == "URL tidak valid: scheme harus http atau https"


def test_empty_host_400():
    response = client.post("/check", json={"url": "https://"})
    assert response.status_code == 400
    assert response.json()["detail"] == "URL tidak valid: host tidak ditemukan"


def test_cors_preflight_allows_reflex_origin():
    response = client.options(
        "/check",
        headers={"Origin": "http://localhost:3000", "Access-Control-Request-Method": "POST"},
    )
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:3000"


def test_vercel_user_content_not_allowlisted():
    body = client.post("/check", json={"url": "https://phishing-test.vercel.app/login"}).json()
    assert body["decision_source"] != "allowlist"
    response = client.options(
        "/check",
        headers={"Origin": "http://evil.example", "Access-Control-Request-Method": "POST"},
    )
    assert "access-control-allow-origin" not in response.headers
