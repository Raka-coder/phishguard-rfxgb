"""Bangun set uji dunia nyata dari snapshot feed phishing lokal + URL legit kurasi pemilik.

Skrip ini TIDAK membuka jaringan. Unduh snapshot feed sekali secara manual (mis.
`https://openphish.com/feed.txt` -> `data/realworld/openphish.txt`), lalu jalankan:

    uv run python scripts/build_realworld_set.py

Keluaran: `data/realworld/urls.csv` dengan kolom `url,label,source,collected_at`.
Label mengikuti dataset: 0 = phishing, 1 = legitimate.
"""

import argparse
import csv
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.config import LABEL_LEGIT, LABEL_PHISH

ROOT = Path(__file__).resolve().parents[1]
REALWORLD_DIR = ROOT / "data" / "realworld"
DEFAULT_PHISHING = REALWORLD_DIR / "openphish.txt"
DEFAULT_LEGIT = REALWORLD_DIR / "legit.csv"
DEFAULT_OUT = REALWORLD_DIR / "urls.csv"

FIELDS = ["url", "label", "source", "collected_at"]
_ALLOWED_SCHEMES = {"http", "https"}


def is_valid_url(url: str) -> bool:
    """Hanya http(s) dengan host; URL rusak tidak boleh masuk set uji."""
    try:
        parts = urlsplit(url)
    except ValueError:
        return False
    return parts.scheme.lower() in _ALLOWED_SCHEMES and bool(parts.hostname)


def read_openphish(path: Path) -> list[str]:
    """Feed OpenPhish: satu URL per baris, baris kosong/komentar diabaikan."""
    urls: list[str] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if line and not line.startswith("#"):
            urls.append(line)
    return urls


def read_legit(path: Path) -> list[dict[str, str]]:
    """CSV kurasi: wajib kolom `url`, opsional `source` (default "manual")."""
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        if "url" not in (reader.fieldnames or []):
            raise ValueError(f"{path} harus punya kolom 'url'")
        return [
            {"url": (row.get("url") or "").strip(), "source": (row.get("source") or "manual").strip() or "manual"}
            for row in reader
        ]


def build_rows(
    phishing_urls: list[str],
    legit_rows: list[dict[str, str]],
    collected_at: str,
) -> tuple[list[dict[str, object]], dict[str, int]]:
    """Gabung, validasi, dan dedup; kembalikan baris + statistik untuk laporan konsol."""
    rows: list[dict[str, object]] = []
    seen: set[str] = set()
    stats = {"phishing": 0, "legit": 0, "invalid": 0, "duplicate": 0}

    def add(url: str, label: int, source: str) -> None:
        url = url.strip()
        if not url:
            stats["invalid"] += 1
            return
        if not is_valid_url(url):
            stats["invalid"] += 1
            return
        if url in seen:
            stats["duplicate"] += 1
            return
        seen.add(url)
        rows.append({"url": url, "label": label, "source": source, "collected_at": collected_at})
        stats["phishing" if label == LABEL_PHISH else "legit"] += 1

    for url in phishing_urls:
        add(url, LABEL_PHISH, "openphish")
    for entry in legit_rows:
        add(entry["url"], LABEL_LEGIT, entry["source"])
    return rows, stats


def write_csv(rows: list[dict[str, object]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Bangun set uji dunia nyata (tanpa jaringan)")
    parser.add_argument("--phishing-file", default=str(DEFAULT_PHISHING), help="snapshot feed OpenPhish (teks)")
    parser.add_argument("--legit-file", default=str(DEFAULT_LEGIT), help="CSV kurasi URL legitimate")
    parser.add_argument("--out", default=str(DEFAULT_OUT), help="CSV keluaran")
    args = parser.parse_args(argv)

    phishing_path = Path(args.phishing_file)
    legit_path = Path(args.legit_file)
    out_path = Path(args.out)

    for path, hint in (
        (phishing_path, "Unduh snapshot OpenPhish ke path ini."),
        (legit_path, "Buat CSV dengan header `url,source` berisi URL legitimate pilihan pemilik."),
    ):
        if not path.exists():
            print(f"File tidak ditemukan: {path}")
            print(hint)
            return 2

    try:
        legit_rows = read_legit(legit_path)
    except (OSError, ValueError) as exc:
        print(f"Gagal membaca {legit_path}: {exc}")
        return 2

    collected_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    rows, stats = build_rows(read_openphish(phishing_path), legit_rows, collected_at)
    if not rows:
        print("Tidak ada URL valid; periksa isi file masukan.")
        return 2

    write_csv(rows, out_path)
    print(f"Ditulis: {out_path}")
    print(
        f"Total {len(rows)} URL (phishing {stats['phishing']}, legit {stats['legit']}); "
        f"dilewati: invalid {stats['invalid']}, duplikat {stats['duplicate']}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
