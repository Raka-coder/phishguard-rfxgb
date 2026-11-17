"""Reputasi offline: allowlist kurasi, suffix user-content, dan daftar shortener.

Tanpa jaringan, tanpa Whois/DNS. Lapisan denylist feed (T19) belum ada; bila
ditambahkan, ia dievaluasi SEBELUM allowlist dengan `decision_source="denylist"`.
Saat ini `predict_url` memakai "allowlist", "model", dan "shortener".
"""

import json
from pathlib import Path

from src.config import TRUSTED_DOMAINS_PATH

# Host di bawah public suffix ini user-controlled: JANGAN auto-trust root-nya.
USER_CONTENT_HOSTS = [
    "vercel.app",
    "github.io",
    "pages.dev",
    "netlify.app",
    "web.app",
    "herokuapp.com",
    "sites.google.com",
]

# Shortener tidak boleh di-allowlist (mudah disalahgunakan).
URL_SHORTENERS = [
    "tinyurl.com",
    "bit.ly",
    "t.co",
    "goo.gl",
    "ow.ly",
    "is.gd",
    "buff.ly",
    "adf.ly",
]

_trusted_cache: set[str] | None = None


def _normalize_host(host: str) -> str:
    host = (host or "").strip().lower().rstrip(".")
    if host.startswith("www."):
        host = host[4:]
    return host


def load_trusted() -> set[str]:
    """Muat daftar domain tepercaya sekali (singleton). Fallback set() jika file hilang."""
    global _trusted_cache
    if _trusted_cache is not None:
        return _trusted_cache
    try:
        data = json.loads(TRUSTED_DOMAINS_PATH.read_text(encoding="utf-8"))
        domains = data.get("domains", []) if isinstance(data, dict) else []
        _trusted_cache = {_normalize_host(d) for d in domains if isinstance(d, str)}
    except (OSError, ValueError, TypeError):
        _trusted_cache = set()
    return _trusted_cache


def is_trusted(host: str) -> bool:
    """Exact match saja: host == entri (www. diperlakukan setara)."""
    return _normalize_host(host) in load_trusted()


def is_user_content(host: str) -> bool:
    """True bila host berada di bawah public suffix user-controlled."""
    host = _normalize_host(host)
    return any(host == suffix or host.endswith("." + suffix) for suffix in USER_CONTENT_HOSTS)


def is_shortener(host: str) -> bool:
    return _normalize_host(host) in {s.lower() for s in URL_SHORTENERS}


def reset_cache() -> None:
    """Untuk test: paksa reload."""
    global _trusted_cache
    _trusted_cache = None
