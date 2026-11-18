"""Kontrak Layer 0 Google Safe Browsing: short-circuit, fail-safe, dan opt-in."""

from unittest.mock import Mock

import httpx
import pytest

from src import config as cfg
from src import google_sb
from src.predict import predict_url

PHISHING_URL = "http://testsafebrowsing.appspot.com/s/phishing.html"


class FakeResponse:
    def __init__(self, data: dict, status_code: int = 200):
        self._data = data
        self.status_code = status_code

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            request = httpx.Request("POST", google_sb.GOOGLE_SB_ENDPOINT)
            raise httpx.HTTPStatusError("error", request=request, response=httpx.Response(self.status_code))

    def json(self) -> dict:
        return self._data


def _enable(monkeypatch) -> None:
    monkeypatch.setattr(cfg, "USE_GOOGLE", True)
    monkeypatch.setattr(cfg, "GOOGLE_API_KEY", "dummy-key")


def _match_payload() -> dict:
    return {"matches": [{"threatType": "SOCIAL_ENGINEERING", "platformType": "ANY_PLATFORM"}]}


def test_match_short_circuits_to_phishing(monkeypatch):
    _enable(monkeypatch)
    monkeypatch.setattr(google_sb.httpx, "post", lambda *a, **k: FakeResponse(_match_payload()))

    result = predict_url(PHISHING_URL)

    assert result["verdict"] == "PHISHING"
    assert result["risk_level"] == "tinggi"
    assert result["decision_source"] == "google_safe_browsing"
    assert result["probability"] is None
    assert result["trail"] == [
        {"layer": "google_sb", "result": "phishing", "detail": "SOCIAL_ENGINEERING"}
    ]


def test_no_match_continues_to_offline_layers(monkeypatch):
    _enable(monkeypatch)
    monkeypatch.setattr(google_sb.httpx, "post", lambda *a, **k: FakeResponse({}))
    monkeypatch.setattr("src.predict._load", Mock(side_effect=RuntimeError("reached_model")))

    with pytest.raises(RuntimeError, match="reached_model"):
        predict_url("https://example.com")


def test_timeout_is_failsafe(monkeypatch):
    _enable(monkeypatch)

    def _timeout(*args, **kwargs):
        raise httpx.TimeoutException("timeout")

    monkeypatch.setattr(google_sb.httpx, "post", _timeout)
    monkeypatch.setattr("src.predict._load", Mock(side_effect=RuntimeError("reached_model")))

    with pytest.raises(RuntimeError, match="reached_model"):
        predict_url("https://example.com")


def test_disabled_does_not_call_google(monkeypatch):
    called = Mock()
    monkeypatch.setattr("src.predict.check_google_safe_browsing", called)
    monkeypatch.setattr("src.predict._load", Mock(side_effect=RuntimeError("reached_model")))

    with pytest.raises(RuntimeError, match="reached_model"):
        predict_url("https://example.com")

    called.assert_not_called()


def test_request_uses_five_second_timeout_and_expected_threat_types(monkeypatch):
    _enable(monkeypatch)
    post = Mock(return_value=FakeResponse({}))
    monkeypatch.setattr(google_sb.httpx, "post", post)

    assert google_sb.check_google_safe_browsing("https://example.com") is None

    kwargs = post.call_args.kwargs
    assert kwargs["timeout"] == 5.0
    assert kwargs["params"] == {"key": "dummy-key"}
    assert kwargs["json"]["threatInfo"]["threatTypes"] == ["MALWARE", "SOCIAL_ENGINEERING"]
