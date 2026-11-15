"""Kontrak reputasi offline: exact match, normalisasi www, user-content, shortener, fallback."""

import json
from pathlib import Path

import pytest

from src import reputation
from src.config import TRUSTED_DOMAINS_PATH


def test_exact_and_www_match():
    assert reputation.is_trusted("github.com")
    assert reputation.is_trusted("www.github.com")
    assert reputation.is_trusted("GITHUB.COM")


def test_subdomain_not_auto_trusted():
    assert not reputation.is_trusted("gist.github.com")
    assert not reputation.is_trusted("evil-github.com")
    assert not reputation.is_trusted("github.com.evil.io")


def test_user_content_hosts():
    assert reputation.is_user_content("foo.vercel.app")
    assert reputation.is_user_content("bar.github.io")
    assert reputation.is_user_content("x.pages.dev")
    assert not reputation.is_user_content("vercel.com")
    assert not reputation.is_user_content("github.com")


def test_shorteners_not_trusted():
    for host in ("tinyurl.com", "bit.ly", "t.co"):
        assert not reputation.is_trusted(host)


def test_missing_file_fallback(monkeypatch, tmp_path):
    import src.reputation as r

    r._trusted_cache = None
    r.TRUSTED_DOMAINS_PATH = tmp_path / "missing.json"
    assert r.load_trusted() == set()
    assert r.is_trusted("github.com") is False
    r._trusted_cache = None
    # restore original path for other tests
    from src.config import TRUSTED_DOMAINS_PATH as original

    r.TRUSTED_DOMAINS_PATH = original
    r._trusted_cache = None


def test_no_user_content_or_shortener_in_allowlist():
    data = json.loads(TRUSTED_DOMAINS_PATH.read_text(encoding="utf-8"))
    domains = {d.lower() for d in data["domains"]}
    for host in reputation.USER_CONTENT_HOSTS + reputation.URL_SHORTENERS:
        assert host.lower() not in domains
    # tidak ada wildcard
    assert all("*" not in d for d in domains)
    assert all(not d.startswith(".") for d in domains)
