"""Unduh feed OpenPhish ke data/feeds/ sebagai snapshot bertanggal (satu-satunya skrip jaringan).

Penggunaan:
    uv run python scripts/sync_feeds.py

Setiap snapshot disimpan terpisah (`openphish-YYYYMMDD-HHMMSS.txt`) dan tidak
menimpa snapshot lama, sehingga evaluasi denylist bisa membandingkan dua waktu.
Feed TIDAK boleh didistribusikan ulang (lisensi/syarat pakai OpenPhish).
"""

import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import urlopen

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.config import FEED_DIR

FEED_URL = "https://openphish.com/feed.txt"
TIMEOUT_SECONDS = 60


def main() -> int:
    feed_dir = FEED_DIR
    feed_dir.mkdir(parents=True, exist_ok=True)

    print(f"Mengunduh feed OpenPhish dari {FEED_URL} (butuh internet)...")
    try:
        with urlopen(FEED_URL, timeout=TIMEOUT_SECONDS) as resp:
            data = resp.read()
    except Exception as exc:  # noqa: BLE001 - pesan ramah, bukan traceback
        print(f"Gagal mengunduh feed: {exc}")
        print("Coba lagi nanti, atau simpan feed manual ke data/feeds/.")
        return 1

    try:
        text = data.decode("utf-8", errors="replace")
    except Exception as exc:  # noqa: BLE001
        print(f"Gagal membaca feed: {exc}")
        return 1

    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    target = feed_dir / f"openphish-{stamp}.txt"
    target.write_text(text, encoding="utf-8")

    n_urls = sum(1 for line in text.splitlines() if line.strip() and not line.strip().startswith("#"))
    print(f"Snapshot disimpan: {target}")
    print(f"Jumlah URL: {n_urls}")
    print("Jangan distribusikan ulang file ini (lisensi OpenPhish).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())