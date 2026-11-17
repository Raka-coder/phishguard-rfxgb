"""Denylist offline dari snapshot feed phishing (T19).

Hanya `scripts/sync_feeds.py` yang boleh memakai jaringan. Modul ini memuat
snapshot terbaru dari `FEED_DIR`, menormalisasi URL, dan mencocokkan secara
offline (URL persis setelah normalisasi + domain+path). Tanpa feed atau feed
basi (lewat `FEED_MAX_AGE_HOURS`), lapisan dilewati dengan aman.
"""

import os
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit

from src.config import FEED_DIR, FEED_MAX_AGE_HOURS


def normalize_url(url: str) -> str | None:
    """Normalisasi URL menjadi kunci pencocokan (host+path, lowercase).

    Mengembalikan None bila URL tidak valid (bukan http/https atau tanpa host).
    Query dan fragment dibuang agar domain+path yang sama tetap cocok.
    """
    if not isinstance(url, str):
        return None
    url = url.strip()
    if not url:
        return None
    if "://" not in url:
        url = "http://" + url
    try:
        parts = urlsplit(url)
    except ValueError:
        return None
    scheme = parts.scheme.lower()
    if scheme not in {"http", "https"}:
        return None
    host = (parts.hostname or "").lower().rstrip(".")
    if not host or any(c.isspace() for c in host):
        return None
    path = parts.path or "/"
    # rapikan slash ganda, pertahankan root "/"
    while "//" in path:
        path = path.replace("//", "/")
    if path != "/" and path.endswith("/"):
        path = path.rstrip("/")
    if not path:
        path = "/"
    return f"{host}{path}"


def _snapshot_files(feed_dir: Path) -> list[Path]:
    if not feed_dir.exists() or not feed_dir.is_dir():
        return []
    files = [p for p in feed_dir.iterdir() if p.is_file() and p.suffix.lower() in {".txt", ".csv"}]
    files.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return files


def _parse_feed(path: Path) -> set[str]:
    keys: set[str] = set()
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return keys
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        # dukung CSV sederhana: ambil kolom pertama
        if "," in line:
            line = line.split(",", 1)[0].strip()
        key = normalize_url(line)
        if key is not None:
            keys.add(key)
    return keys


# Cache singleton: (mtime_path, set, path, loaded_at)
_CACHE: dict = {"path": None, "mtime": None, "keys": set(), "loaded_at": None}


def _feed_dir() -> Path:
    return Path(os.getenv("PHISHGUARD_FEED_DIR", str(FEED_DIR)))


def feed_status() -> tuple[str, Path | None, str]:
    """Status feed terbaru: ('ok'|'missing'|'stale', path_atau_None, alasan)."""
    d = _feed_dir()
    files = _snapshot_files(d)
    if not files:
        return "missing", None, "Tidak ada snapshot feed di folder denylist."
    latest = files[0]
    try:
        age_hours = (time.time() - latest.stat().st_mtime) / 3600.0
    except OSError:
        return "missing", None, "Snapshot feed tidak dapat dibaca."
    max_age = int(os.getenv("PHISHGUARD_FEED_MAX_AGE_HOURS", str(FEED_MAX_AGE_HOURS)))
    if age_hours > max_age:
        return "stale", latest, f"Snapshot feed basi ({age_hours:.1f} jam > {max_age} jam)."
    return "ok", latest, f"Feed dimuat dari {latest.name} ({age_hours:.1f} jam lalu)."


def load_feed() -> set[str]:
    """Muat snapshot terbaru ke cache singleton; kosong bila tidak tersedia/basi."""
    global _CACHE
    status, path, _ = feed_status()
    if status != "ok" or path is None:
        _CACHE = {"path": None, "mtime": None, "keys": set(), "loaded_at": None}
        return set()
    try:
        mtime = path.stat().st_mtime
    except OSError:
        _CACHE = {"path": None, "mtime": None, "keys": set(), "loaded_at": None}
        return set()
    if _CACHE.get("path") == path and _CACHE.get("mtime") == mtime:
        return _CACHE["keys"]
    keys = _parse_feed(path)
    _CACHE = {"path": path, "mtime": mtime, "keys": keys, "loaded_at": datetime.now(timezone.utc)}
    return keys


def is_denied(url: str) -> bool:
    """True bila URL ada di snapshot feed (cocok offline)."""
    keys = load_feed()
    if not keys:
        return False
    key = normalize_url(url)
    return key is not None and key in keys


def reset_cache() -> None:
    """Pakai di tes: kosongkan cache agar env/path berubah terbaca."""
    global _CACHE
    _CACHE = {"path": None, "mtime": None, "keys": set(), "loaded_at": None}