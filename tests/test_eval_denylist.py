"""Kontrak eval_denylist: tumpang tindih, kurva umur entri, Wilson, output tanpa URL."""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.eval_denylist import age_curve, domain_of_host, host_of_key, overlap_between, pct, read_urls, wilson_ci
from src.denylist import normalize_url


def test_host_and_domain_extraction():
    assert host_of_key("evil.example.com/phish") == "evil.example.com"
    assert host_of_key("evil.example.com") == "evil.example.com"
    assert host_of_key("sub.evil.com/a/b") == "sub.evil.com"
    assert domain_of_host("www.evil.com") == "evil.com"
    assert domain_of_host("evil.com") == "evil.com"


def test_overlap_between_counts_url_host_domain():
    keys_a = {"evil.com/phish", "good.com/ok", "other.com/x"}
    keys_b = {"evil.com/phish", "new.com/brand-new", "good.com/ok"}
    r = overlap_between(keys_a, keys_b)
    assert r["n_urls_a"] == 3
    assert r["n_urls_b"] == 3
    assert r["n_url_overlap"] == 2  # evil.com/phish + good.com/ok
    assert r["n_url_overlap_pct_of_b"] == pytest.approx(66.67, abs=0.01)
    assert r["n_new_in_b"] == 1
    assert r["n_host_overlap"] > 0
    assert r["n_domain_overlap"] > 0


def test_overlap_empty_sets():
    r = overlap_between(set(), set())
    assert r["n_url_overlap"] == 0
    assert r["n_url_overlap_pct_of_b"] == 0.0
    assert r["n_new_in_b"] == 0


def test_age_curve_pct_and_hours(tmp_path):
    f1 = tmp_path / "snap-a.txt"
    f1.write_text("https://evil.com/phish\nhttps://good.com/ok\n", encoding="utf-8")
    f2 = tmp_path / "snap-b.txt"
    f2.write_text("https://evil.com/phish\nhttps://new.com/x\n", encoding="utf-8")
    import os
    import time

    old = time.time() - 5 * 3600
    os.utime(f1, (old, old))
    os.utime(f2, (old + 2 * 3600, old + 2 * 3600))
    curve = age_curve([f1, f2])
    assert len(curve) == 1
    assert curve[0]["snapshot"] == "snap-a.txt"
    assert curve[0]["later_snapshot"] == "snap-b.txt"
    assert curve[0]["pct_still_present"] == 50.0
    assert curve[0]["hours_between_snapshots"] == pytest.approx(2.0)


def test_age_curve_needs_two_snapshots(tmp_path):
    assert age_curve([tmp_path / "only.txt"]) == []


def test_pct_zero_whole():
    assert pct(0, 0) == 0.0
    assert pct(1, 4) == 25.0


def test_wilson_ci_bounds():
    lo, hi = wilson_ci(0, 299)
    assert 0.0 <= lo <= hi
    assert hi > 0.0


def test_read_urls_ignores_comments_and_blanks(tmp_path):
    f = tmp_path / "feed.txt"
    f.write_text("# komentar\n\nhttps://a.com/x\nhttps://b.com/y\n", encoding="utf-8")
    assert read_urls(f) == ["https://a.com/x", "https://b.com/y"]


def test_generated_denylist_json_has_no_url_keys():
    data = json.loads(Path("docs/denylist.json").read_text(encoding="utf-8"))
    text = json.dumps(data)
    assert "http" not in text and "https://" not in text
    assert "full_system" in data
    assert "overlap" in data
    assert "age_curve" in data
    assert "false_positives" in data
