"""Inspeksi dataset PhiUSIIL via DuckDB tanpa memuat penuh ke RAM."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # agar `import src.*` jalan dari scripts/

import duckdb

from src.config import DATA_CSV, EXPECTED_LABEL_COUNTS, EXPECTED_ROWS

SAMPLE_COLUMNS = ["URL", "URLLength", "DomainLength", "IsHTTPS", "TLD", "label"]


def main() -> int:
    if not DATA_CSV.exists():
        print(f"Dataset tidak ditemukan: {DATA_CSV}")
        print("Letakkan CSV PhiUSIIL (hasil ekstrak ZIP Kaggle) di data/PhiUSIIL.csv")
        return 1

    con = duckdb.connect()
    csv = DATA_CSV.as_posix()

    print(f"File : {DATA_CSV} ({DATA_CSV.stat().st_size / 1_000_000:.1f} MB)\n")
    print("=== Skema ===")
    print(con.sql(f"DESCRIBE SELECT * FROM read_csv_auto('{csv}')").df().to_string(index=False))

    rows = con.sql(f"SELECT COUNT(*) FROM read_csv_auto('{csv}')").fetchall()[0][0]
    print(f"\n=== Jumlah baris ===\n{rows}")

    print("\n=== Distribusi label ===")
    rows_by_label = con.sql(
        f"SELECT label, COUNT(*) FROM read_csv_auto('{csv}') GROUP BY label ORDER BY label"
    ).fetchall()
    counts = dict(rows_by_label)
    for label, count in counts.items():
        name = "legitimate" if label == 1 else "phishing"
        print(f"label {label} ({name}): {count}")

    print("\n=== Sampel 5 baris ===")
    cols = ", ".join(SAMPLE_COLUMNS)
    print(con.sql(f"SELECT {cols} FROM read_csv_auto('{csv}') LIMIT 5").df().to_string(index=False))

    ok = rows == EXPECTED_ROWS and counts == EXPECTED_LABEL_COUNTS
    print("\n=== Verifikasi ===")
    print(f"{'OK' if ok else 'GAGAL'}: {rows} baris, label {counts}")
    if not ok:
        print(f"Diharapkan: {EXPECTED_ROWS} baris, label {EXPECTED_LABEL_COUNTS}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
