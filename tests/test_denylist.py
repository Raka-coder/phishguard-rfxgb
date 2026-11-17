"""Kontrak denylist offline: normalisasi, status feed, cache, dan pencocokan."""

import os
import time
from pathlib import Path

import pytest

from src import denylist
from src.denylist import feed_status, is_denied, load_feed, normalize_url, reset_cache


def test_normalize_url_basic():
    assert normalize_url("https://Example.com/Foo/?q=1#x") == "example.com/Foo"
    assert normalize_url("HTTP://example.com") == "example.com/"
    assert normalize_url("example.com/path//x/") == "example.com/path/x"
    assert normalize_url("not a url") is None
    assert normalize_url("") is None
    assert normalize_url("ftp://example.com") is None


def test_feed_missing(tmp_path, monkeypatch):
    monkeypatch.setenv("PHISHGUARD_FEED_DIR", str(tmp_path))
    monkeypatch.delenv("PHISHGUARD_FEED_MAX_AGE_HOURS", raising=False)
    reset_cache()
    status, path, detail = feed_status()
    assert status == "missing"
    assert path is None
    assert load_feed() == set()
    assert is_denied("https://evil.example/x") is False


def test_feed_stale(tmp_path, monkeypatch):
    d = tmp_path / "feeds"
    d.mkdir()
    f = d / "openphish-1.txt"
    f.write_text("https://evil.example/x\n", encoding="utf-8")
    # buat file terlihat basi: mtime jauh di masa lalu
    old = time.time() - 100 * 3600
    os.utime(f, (old, old))
    monkeypatch.setenv("PHISHGUARD_FEED_DIR", str(d))
    monkeypatch.setenv("PHISHGUARD_FEED_MAX_AGE_HOURS", "24")
    reset_cache()
    status, path, detail = feed_status()
    assert status == "stale"
    assert path == f
    assert load_feed() == set()
    assert is_denied("https://evil.example/x") is False


def test_feed_ok_match(tmp_path, monkeypatch):
    d = tmp_path / "feeds"
    d.mkdir()
    f = d / "openphish-1.txt"
    f.write_text("https://evil.example/x\nhttps://other.example/y?q=1\n# komentar\n", encoding="utf-8")
    monkeypatch.setenv("PHISHGUARD_FEED_DIR", str(d))
    monkeypatch.setenv("PHISHGUARD_FEED_MAX_AGE_HOURS", "24")
    reset_cache()
    status, path, detail = feed_status()
    assert status == "ok"
    assert is_denied("https://evil.example/x") is True
    # query berbeda tapi host+path sama -> cocok
    assert is_denied("http://other.example/y?foo=bar") is True
    assert is_denied("https://example.com/safe") is False


def test_cache_reloads_on_mtime_change(tmp_path, monkeypatch):
    d = tmp_path / "feeds"
    d.mkdir()
    f = d / "openphish-1.txt"
    f.write_text("https://a.example/x\n", encoding="utf-8")
    monkeypatch.setenv("PHISHGUARD_FEED_DIR", str(d))
    monkeypatch.setenv("PHISHGUARD_FEED_MAX_AGE_HOURS", "24")
    reset_cache()
    assert is_denied("https://a.example/x") is True
    # ubah isi + mtime -> cache harus reload tanpa reset_cache
    future = time.time() + 10
    f.write_text("https://b.example/y\n", encoding="utf-8")
    os.utime(f, (future, future))
    assert is_denied("https://a.example/x") is False
    assert is_denied("https://b.example/y") is True
    reset_cache()
    assert is_denied("https://b.example/y") is True