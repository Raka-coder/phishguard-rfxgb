"""Layer 0: Google Safe Browsing (opsional, fail-safe, default mati).

Hanya dipanggil bila `PHISHGUARD_USE_GOOGLE` aktif dan API key tersedia.
Error/timeout apa pun dianggap "tidak ada match" agar lapisan offline berikutnya
tetap berjalan.
"""

import logging
from typing import Any

import httpx

from src import config

logger = logging.getLogger(__name__)

GOOGLE_SB_ENDPOINT = "https://safebrowsing.googleapis.com/v4/threatMatches:find"
TIMEOUT_SECONDS = 5.0
THREAT_TYPES = ["MALWARE", "SOCIAL_ENGINEERING"]


def google_enabled() -> bool:
    """Aktif hanya bila flag dinyalakan dan API key diisi."""
    return bool(config.USE_GOOGLE and config.GOOGLE_API_KEY)


def _payload(url: str) -> dict[str, Any]:
    return {
        "client": {"clientId": "phishguard", "clientVersion": "0.1.0"},
        "threatInfo": {
            "threatTypes": THREAT_TYPES,
            "platformTypes": ["ANY_PLATFORM"],
            "threatEntryTypes": ["URL"],
            "threatEntries": [{"url": url}],
        },
    }


def check_google_safe_browsing(url: str) -> dict | None:
    """Return {'threat_type', 'platform_type'} bila terdeteksi; None bila aman/gagal."""
    if not google_enabled():
        return None
    try:
        response = httpx.post(
            GOOGLE_SB_ENDPOINT,
            params={"key": config.GOOGLE_API_KEY},
            json=_payload(url),
            timeout=TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        data = response.json()
    except Exception as exc:  # noqa: BLE001 - fail-safe: jangan gagalkan inference
        logger.warning("Google Safe Browsing gagal (dianggap aman): %s", exc)
        return None

    matches = data.get("matches") if isinstance(data, dict) else None
    if not matches:
        return None
    first = matches[0]
    return {
        "threat_type": str(first.get("threatType", "")),
        "platform_type": str(first.get("platformType", "")),
    }
