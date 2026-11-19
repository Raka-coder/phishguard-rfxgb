"""Kontrak skrip evaluasi lapisan (T30): guard anti-melingkar dan paritas vonis."""

import csv
from pathlib import Path

import numpy as np
import pytest

import src.predict as predict
from scripts.test_layers import is_valid_url, load_realworld, overlap_guard, stage_verdict


class _FakePipe:
    classes_ = np.array([0, 1])

    def __init__(self, probability: float) -> None:
        self.probability = probability

    def predict_proba(self, frame) -> np.ndarray:
        return np.tile([self.probability, 1 - self.probability], (len(frame), 1))


def test_overlap_guard_passes_on_different_snapshot():
    guard = overlap_guard(["https://a.example/x", "https://b.example/y"], {"c.example/z"})
    assert guard["overlap_urls"] == 0
    assert guard["ok"] is True


def test_overlap_guard_blocks_circular_feed():
    urls = ["https://a.example/x", "https://a.example/y"]
    guard = overlap_guard(urls, {"a.example/x", "a.example/y"})
    assert guard["overlap_urls"] == 2
    assert guard["overlap_pct_of_test"] == 100.0
    assert guard["ok"] is False


def test_load_realworld_skips_invalid_rows(tmp_path):
    path = tmp_path / "urls.csv"
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["url", "label", "source"])
        writer.writeheader()
        writer.writerow({"url": "https://ok.example/x", "label": "0", "source": "openphish"})
        writer.writerow({"url": "https://legit.example", "label": "1", "source": "manual"})
        writer.writerow({"url": "ftp://bad.example", "label": "0", "source": "openphish"})
        writer.writerow({"url": "https://x.example", "label": "9", "source": "openphish"})

    rows, skipped = load_realworld(path)

    assert skipped == 2
    assert [(row["label"], row["url"]) for row in rows] == [
        (0, "https://ok.example/x"),
        (1, "https://legit.example"),
    ]


def test_is_valid_url_rejects_non_http():
    assert is_valid_url("https://a.example") is True
    assert is_valid_url("ftp://a.example") is False
    assert is_valid_url("https://") is False


@pytest.mark.parametrize(
    "url",
    ["https://example.com/path", "https://bit.ly/abc123", "https://github.com/x"],
)
def test_full_stage_matches_predict_url(monkeypatch, url):
    """Tingkatan L1..L4 harus identik dengan predict_url agar skrip tidak menyimpang."""
    monkeypatch.setattr(predict, "_load", lambda: (_FakePipe(0.10), {"map": {}, "default": 0.5}, {}))
    monkeypatch.setattr(predict, "_load_model_c", lambda: None)

    expected = predict.predict_url(url)["verdict"]
    actual = stage_verdict(url, ["L1", "L2", "L3", "L4"], 0.10, None, gsb_match=False, feed_ok=True)

    assert actual == expected
