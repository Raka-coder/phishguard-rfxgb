"""Fitur host-only untuk eksperimen Model C: tanpa skema, path, query, atau fragmen."""

import ipaddress
from urllib.parse import urlsplit

import pandas as pd

HOST_FEATURES = [
    "HostLength",
    "HostLetterCount",
    "HostDigitCount",
    "HostSpecialCount",
    "HostLetterRatio",
    "HostDigitRatio",
    "NoOfSubDomain",
    "TLDLength",
    "IsDomainIP",
    "TLDLegitimateProb",
]
DEFAULT_TLD_PROB = 0.5


def host_of(url: str, strip_www: bool = False) -> str:
    """Host lowercase tanpa port; bila strip_www, awalan www. dibuang."""
    url = (url or "").strip()
    try:
        host = (urlsplit(url if "://" in url else f"http://{url}").hostname or "").lower()
    except ValueError:
        return ""
    if strip_www and host.startswith("www."):
        host = host[4:]
    return host


def tld_of_host(host: str) -> str:
    """TLD lowercase (label terakhir host); "" bila host tidak punya titik."""
    return host.rsplit(".", 1)[-1] if "." in host else ""


def _is_ip(host: str) -> int:
    try:
        ipaddress.ip_address(host)
        return 1
    except ValueError:
        return 0


def extract_host_features(
    url: str,
    tld_probs: dict[str, float] | None = None,
    default_tld_prob: float = DEFAULT_TLD_PROB,
    strip_www: bool = False,
) -> dict[str, float]:
    """10 fitur yang hanya bergantung pada host; skema/path/query tidak berpengaruh."""
    host = host_of(url, strip_www=strip_www)
    labels = host.split(".") if host else []
    n = len(host)
    denom = n or 1
    letters = sum(c.isalpha() for c in host)
    digits = sum(c.isdigit() for c in host)
    specials = sum(not (c.isalnum() or c == ".") for c in host)
    tld = tld_of_host(host)

    return {
        "HostLength": float(n),
        "HostLetterCount": float(letters),
        "HostDigitCount": float(digits),
        "HostSpecialCount": float(specials),
        "HostLetterRatio": letters / denom,
        "HostDigitRatio": digits / denom,
        "NoOfSubDomain": float(max(len(labels) - 2, 0)),
        "TLDLength": float(len(labels[-1])) if labels else 0.0,
        "IsDomainIP": float(_is_ip(host)),
        "TLDLegitimateProb": float((tld_probs or {}).get(tld, default_tld_prob)),
    }


def to_host_frame(
    urls: str | list[str],
    tld_probs: dict[str, float] | None = None,
    default_tld_prob: float = DEFAULT_TLD_PROB,
    strip_www: bool = False,
) -> pd.DataFrame:
    """DataFrame satu baris per URL, kolom urut sesuai HOST_FEATURES."""
    if isinstance(urls, str):
        urls = [urls]
    rows = [extract_host_features(u, tld_probs, default_tld_prob, strip_www=strip_www) for u in urls]
    return pd.DataFrame(rows, columns=HOST_FEATURES, dtype=float)
