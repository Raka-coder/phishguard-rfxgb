"""Kontrak API: POST /check, GET /health, error 400, dan CORS."""

from fastapi.testclient import TestClient

from api.main import app

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
    assert 0 <= body["probability"] <= 1
    assert isinstance(body["inference_ms"], (int, float))
    assert set(body) == {"url", "label", "label_name", "probability", "inference_ms", "top_features"}


def test_check_phishing_200():
    response = client.post("/check", json={"url": PHISHING_IP_URL})
    assert response.status_code == 200
    body = response.json()
    assert body["label"] == 0
    assert body["label_name"] == "PHISHING"
    assert body["probability"] > 0.8
    assert 0 <= body["probability"] <= 1
    assert isinstance(body["inference_ms"], (int, float))


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


def test_cors_rejects_unknown_origin():
    response = client.options(
        "/check",
        headers={"Origin": "http://evil.example", "Access-Control-Request-Method": "POST"},
    )
    assert "access-control-allow-origin" not in response.headers
