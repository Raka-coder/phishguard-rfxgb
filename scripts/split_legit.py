"""Bagi baris keep=1 menjadi dev 70% / final 30% dikelompokkan per reg_domain (T24c)."""

import argparse
import csv
import statistics
import sys
from pathlib import Path
from urllib.parse import urlsplit

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sklearn.model_selection import GroupShuffleSplit

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REVIEW = ROOT / "data" / "realworld" / "legit_review.csv"
DEFAULT_DEV = ROOT / "data" / "realworld" / "legit_dev.csv"
DEFAULT_FINAL = ROOT / "data" / "realworld" / "legit_final.csv"
OUTPUT_COLUMNS = ["url", "reg_domain", "in_allowlist", "host_type", "person_label"]


def split_review(review_path: Path, dev_path: Path, final_path: Path, test_size: float, seed: int) -> None:
    if not review_path.exists():
        raise SystemExit(f"File tidak ditemukan: {review_path}")
    with review_path.open(encoding="utf-8", newline="") as handle:
        rows = [dict(row) for row in csv.DictReader(handle)]

    selected = [row for row in rows if (row.get("keep") or "").strip() == "1"]
    if not selected:
        raise SystemExit("Tidak ada baris dengan keep=1; isi dulu kolom 'keep'.")

    # pastikan reg_domain ada
    for row in selected:
        if not (row.get("reg_domain") or "").strip():
            row["reg_domain"] = row.get("url", "").split("/")[2] if "://" in row.get("url", "") else ""

    groups = [row["reg_domain"] for row in selected]
    labels = [0] * len(selected)
    splitter = GroupShuffleSplit(n_splits=1, test_size=test_size, random_state=seed)
    dev_rel, final_rel = next(splitter.split(labels, groups=groups))
    dev_rows = [selected[i] for i in sorted(dev_rel)]
    final_rows = [selected[i] for i in sorted(final_rel)]

    def project(items):
        return [{column: row.get(column, "") for column in OUTPUT_COLUMNS} for row in items]

    def write(path, items):
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=OUTPUT_COLUMNS, lineterminator="\n")
            writer.writeheader()
            writer.writerows(project(items))

    write(dev_path, dev_rows)
    write(final_path, final_rows)

    dev_hosts = {urlsplit(row["url"]).hostname or "" for row in dev_rows}
    final_hosts = {urlsplit(row["url"]).hostname or "" for row in final_rows}
    dev_regs = {row["reg_domain"] for row in dev_rows}
    final_regs = {row["reg_domain"] for row in final_rows}
    if dev_regs & final_regs:
        raise SystemExit(f"reg_domain tumpang tindih: {len(dev_regs & final_regs)}")

    def host_lengths(items):
        return [len(urlsplit(row["url"]).hostname or "") for row in items]

    def aggregate(name, items):
        lengths = host_lengths(items)
        regs = {row["reg_domain"] for row in items}
        print(
            f"{name}: {len(items)} URL, {len(regs)} reg_domain; "
            f"root {sum(row.get('host_type') == 'root' for row in items)}, "
            f"berpath {sum(row.get('host_type') == 'berpath' for row in items)}; "
            f"di luar allowlist {sum((row.get('in_allowlist') or '') == '0' for row in items)}; "
            f"panjang host mean {statistics.mean(lengths):.2f}, median {statistics.median(lengths):.2f}"
        )

    aggregate("Dev", dev_rows)
    aggregate("Final", final_rows)
    print(f"Host tumpang tindih dev/final: {len(dev_hosts & final_hosts)}")
    print(f"reg_domain tumpang tindih dev/final: {len(dev_regs & final_regs)}")
    print(f"Ditulis: {dev_path} dan {final_path}")


def main(argv=None):
    parser = argparse.ArgumentParser(description="Bagi legit_review.csv (keep=1) menjadi dev/final per reg_domain")
    parser.add_argument("--review", default=str(DEFAULT_REVIEW), help="CSV review")
    parser.add_argument("--dev", default=str(DEFAULT_DEV), help="CSV dev keluaran")
    parser.add_argument("--final", default=str(DEFAULT_FINAL), help="CSV final keluaran")
    parser.add_argument("--test-size", type=float, default=0.3, help="proporsi final")
    parser.add_argument("--seed", type=int, default=42, help="seed split")
    args = parser.parse_args(argv)
    split_review(Path(args.review), Path(args.dev), Path(args.final), args.test_size, args.seed)
    return 0


if __name__ == "__main__":
    sys.exit(main())
