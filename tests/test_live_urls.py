"""Kontrak scripts/test_live_urls.py: parsing, error handling, determinisme."""

import io
import sys
from contextlib import redirect_stdout
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import scripts.test_live_urls as live


def test_load_urls_ignores_comments_and_blanks(tmp_path):
    fixture = tmp_path / "urls.txt"
    fixture.write_text(
        "# komentar\n\nhttps://a.com\n  # indented\nhttp://b.net\n",
        encoding="utf-8",
    )
    assert live.load_urls(fixture) == ["https://a.com", "http://b.net"]


def test_run_captures_value_error(monkeypatch):
    def fake_predict(url):
        if url == "bad":
            raise ValueError("URL tidak valid: input kosong")
        return {"url": url, "label": 1, "label_name": "LEGITIMATE", "probability": 0.1, "inference_ms": 1.0, "top_features": []}

    monkeypatch.setattr(live, "predict_url", fake_predict)
    results = live.run(["ok", "bad"])
    assert len(results) == 2
    assert not isinstance(results[0][1], Exception)
    assert isinstance(results[1][1], ValueError)


def test_console_output_contains_all_urls(monkeypatch, capsys):
    def fake_predict(url):
        return {"url": url, "label": 1, "label_name": "LEGITIMATE", "probability": 0.1, "inference_ms": 1.0, "top_features": []}

    monkeypatch.setattr(live, "predict_url", fake_predict)
    live.print_console(live.run(["https://a.com", "https://b.net"]))
    out = capsys.readouterr().out
    assert "https://a.com" in out
    assert "https://b.net" in out
    assert "Ringkasan:" in out


def test_markdown_output_is_deterministic(monkeypatch, capsys):
    def fake_predict(url):
        return {"url": url, "label": 0, "label_name": "PHISHING", "probability": 0.9, "inference_ms": 2.0, "top_features": [{"feature": "IsHTTPS", "value": 0.0, "impact": "meningkatkan risiko"}]}

    monkeypatch.setattr(live, "predict_url", fake_predict)
    live.print_markdown(live.run(["https://x.com"]))
    first = capsys.readouterr().out
    live.print_markdown(live.run(["https://x.com"]))
    second = capsys.readouterr().out
    assert first == second
    assert "top-3 fitur" in first
