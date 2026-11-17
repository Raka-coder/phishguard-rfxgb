"""Evaluasi denylist: bangun dari snapshot A, uji pada snapshot B dan pada A sendiri.

Penggunaan (butuh >=2 snapshot di data/feeds/):
    uv run python scripts/eval_denylist.py
    uv run python scripts/eval_denylist.py --snapshot-a data/feeds/x.txt --snapshot-b data/feeds/y.txt

Hasil ditulis ke docs/denylist.json (tanpa URL). Tingkat tangkapan dilaporkan dengan
CI Wilson 95%. Snapshot A pada dirinya sendiri adalah batas atas yang tidak bermakna.
"""

import argparse
import csv
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.config import DOCS_DIR, FEED_DIR
from src.denylist import _parse_feed, normalize_url

Z_95 = 1.959963984540054


def wilson_ci(k: int, n: int, z: float = Z_95) -> list[float]:
    """CI Wilson 95% untuk proporsi k/n."""
    if n <= 0:
        return [0.0, 0.0]
    p = k / n
    denom = 1 + z * z / n
    centre = p + z * z / (2 * n)
    half = z * ((p * (1 - p) + z * z / (4 * n)) / n) ** 0.5
    lo = (centre - half) / denom
    hi = (centre + half) / denom
    return [max(0.0, lo), min(1.0, hi)]


def read_urls(path: Path) -> list[str]:
    if path.suffix.lower() == ".csv":
        urls: list[str] = []
        with path.open(encoding="utf-8", newline="") as fh:
            reader = csv.DictReader(fh)
            for row in reader:
                u = (row.get("url") or "").strip()
                if u:
                    urls.append(u)
        return urls
    urls = []
    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw.strip()
        if line and not line.startswith("#"):
            if "," in line:
                line = line.split(",", 1)[0].strip()
            urls.append(line)
    return urls


def latest_two_snapshots(feed_dir: Path) -> tuple[Path, Path]:
    candidates: list[Path] = []
    if feed_dir.exists():
        candidates += [p for p in feed_dir.iterdir() if p.is_file() and p.suffix.lower() in {".txt", ".csv"}]
    # snapshot lama dari set uji dunia nyata (jika ada) agar perbandingan bermakna
    legacy = Path("data/realworld/openphish.txt")
    if legacy.exists():
        candidates.append(legacy)
    candidates = sorted(set(candidates), key=lambda p: p.stat().st_mtime)
    if len(candidates) < 2:
        raise SystemExit(
            f"Perlu >=2 snapshot. Jalankan `uv run python scripts/sync_feeds.py` minimal dua kali "
            "(atau sediakan data/realworld/openphish.txt) lalu ulangi."
        )
    return candidates[0], candidates[-1]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--snapshot-a", type=Path, default=None)
    parser.add_argument("--snapshot-b", type=Path, default=None)
    parser.add_argument("--legit-dev", type=Path, default=Path("data/realworld/legit_dev.csv"))
    parser.add_argument("--legit-final", type=Path, default=Path("data/realworld/legit_final.csv"))
    parser.add_argument("--out", type=Path, default=DOCS_DIR / "denylist.json")
    args = parser.parse_args()

    if args.snapshot_a is None or args.snapshot_b is None:
        a, b = latest_two_snapshots(FEED_DIR)
    else:
        a, b = args.snapshot_a, args.snapshot_b

    if not a.exists() or not b.exists():
        raise SystemExit(f"Snapshot tidak ditemukan: {a} / {b}")

    deny_set = _parse_feed(a)
    urls_a = read_urls(a)
    urls_b = read_urls(b)

    set_a_keys = {normalize_url(u) for u in urls_a if normalize_url(u) is not None}
    new_in_b = [u for u in urls_b if normalize_url(u) not in set_a_keys]

    # capture pada URL baru di B
    k_new = sum(1 for u in new_in_b if normalize_url(u) in deny_set)
    n_new = len(new_in_b)

    # capture pada A sendiri (batas atas, trivial)
    k_a = sum(1 for u in urls_a if normalize_url(u) in deny_set)
    n_a = len(urls_a)

    # overlap A/B (informasi)
    keys_b = {normalize_url(u) for u in urls_b if normalize_url(u) is not None}
    n_overlap = len(set_a_keys & keys_b)

    # FP pada legit
    def fp_count(path: Path) -> tuple[int, int]:
        if not path.exists():
            return 0, 0
        urls = read_urls(path)
        tested = len(urls)
        fp = sum(1 for u in urls if normalize_url(u) in deny_set)
        return tested, fp

    dev_tested, dev_fp = fp_count(args.legit_dev)
    final_tested, final_fp = fp_count(args.legit_final)

    result = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "snapshot_a": a.name,
        "snapshot_b": b.name,
        "n_a": n_a,
        "n_b": len(urls_b),
        "n_overlap_a_b": n_overlap,
        "n_new_in_b": n_new,
        "capture_on_new_in_b": {
            "n": k_new,
            "total": n_new,
            "rate": (k_new / n_new) if n_new else 0.0,
            "wilson_ci_95": wilson_ci(k_new, n_new),
        },
        "capture_on_a_upper_bound": {
            "n": k_a,
            "total": n_a,
            "rate": (k_a / n_a) if n_a else 0.0,
            "label": "batas atas (trivial, tidak bermakna): denylist dievaluasi pada data yang membentuknya",
        },
        "false_positives": {
            "legit_dev": {"n_tested": dev_tested, "n_fp": dev_fp},
            "legit_final": {"n_tested": final_tested, "n_fp": final_fp},
        },
    }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(result, indent=2, ensure_ascii=False))
    print(f"\nDitulis ke {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())