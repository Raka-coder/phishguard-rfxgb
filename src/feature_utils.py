"""Ekstraksi fitur leksikal dari string URL (murni, tanpa jaringan/I/O)."""

import ipaddress
import re
from collections.abc import Iterable
from urllib.parse import urlsplit

import pandas as pd

from src.config import URL_FEATURES

_SCHEME_RE = re.compile(r"^[a-zA-Z][a-zA-Z0-9+.-]*://")
_ALNUM_RUN_RE = re.compile(r"[A-Za-z0-9]+")
_NON_ASCII_RE = re.compile(r"[^\x00-\x7f]")

# Urutan & nama mengikuti kolom dataset PhiUSIIL; nilainya dihitung dari string URL.
# shortcut: definisi idealnya identik dengan kolom dataset, tapi NoOfLettersInURL/CharContinuationRate
# tidak bisa direproduksi dari string (diuji pada 2.000 baris). Model B dilatih ulang dari fungsi ini,
# jadi konsistensi train/serve terjaga; jangan ganti definisi tanpa me-retrain model.
_SPECIAL = set(",;:%~+&*[]()!$#'\"?=/@_-")
_OBFUSCATION = set("%@\\")


def _host(url: str) -> str:
    """Host lowercase tanpa port; string rusak menghasilkan ""."""
    try:
        return (urlsplit(url if "://" in url else f"http://{url}").hostname or "").lower()
    except ValueError:
        return ""


def _is_ip(host: str) -> int:
    try:
        ipaddress.ip_address(host)
        return 1
    except ValueError:
        return 0


def extract_features(url: str) -> dict[str, float]:
    """Hitung semua fitur Model B dari satu URL; selalu mengembalikan angka, tidak pernah None."""
    url = (url or "").strip()
    host = _host(url)
    n = len(url)
    denom = n or 1

    letters = sum(c.isalpha() for c in url)
    digits = sum(c.isdigit() for c in url)
    specials = sum(c in _SPECIAL for c in url)
    longest_run = max((len(m) for m in _ALNUM_RUN_RE.findall(url)), default=0)
    obfuscated = sum(c in _OBFUSCATION for c in url) + len(_NON_ASCII_RE.findall(url))
    is_ip = _is_ip(host)
    labels = host.split(".") if host else []

    return {
        "URLLength": float(n),
        "DomainLength": float(len(host)),
        "TLDLength": float(len(labels[-1])) if labels else 0.0,
        "NoOfSubDomain": float(max(len(labels) - 2, 0)),
        "IsDomainIP": float(is_ip),
        "IsHTTPS": float(url.lower().startswith("https")),
        "NoOfLettersInURL": float(letters),
        "LetterRatioInURL": letters / denom,
        "NoOfDegitsInURL": float(digits),
        "DegitRatioInURL": digits / denom,
        "NoOfEqualsInURL": float(url.count("=")),
        "NoOfQMarkInURL": float(url.count("?")),
        "NoOfAmpersandInURL": float(url.count("&")),
        "NoOfOtherSpecialCharsInURL": float(specials),
        "SpacialCharRatioInURL": specials / denom,
        "CharContinuationRate": longest_run / denom,
        "HasObfuscation": float(bool(obfuscated or is_ip)),
        "NoOfObfuscatedChar": float(obfuscated),
        "ObfuscationRatio": obfuscated / denom,
    }


def to_frame(urls: str | Iterable[str]) -> pd.DataFrame:
    """DataFrame satu baris per URL, kolom urut sesuai URL_FEATURES (kontrak Model B)."""
    if isinstance(urls, str):
        urls = [urls]
    rows = [extract_features(u) for u in urls]
    return pd.DataFrame(rows, columns=URL_FEATURES, dtype=float)
