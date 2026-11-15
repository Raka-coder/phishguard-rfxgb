"""Konversi CSV PhiUSIIL ke Parquet ZSTD (sekali per laptop)."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # agar `import src.*` jalan dari scripts/

import duckdb

from src.config import DATA_CSV, DATA_PARQUET


def main() -> int:
    if not DATA_CSV.exists():
        print(f"Dataset tidak ditemukan: {DATA_CSV}")
        return 1
    if DATA_PARQUET.exists():
        print(f"Sudah ada: {DATA_PARQUET} ({DATA_PARQUET.stat().st_size / 1_000_000:.1f} MB) — dilewati.")
        return 0

    con = duckdb.connect()
    con.sql(
        f"COPY (SELECT * FROM read_csv_auto('{DATA_CSV.as_posix()}')) "
        f"TO '{DATA_PARQUET.as_posix()}' (FORMAT PARQUET, COMPRESSION ZSTD)"
    )

    rows = con.sql(f"SELECT COUNT(*) FROM '{DATA_PARQUET.as_posix()}'").fetchall()[0][0]
    print(f"Ditulis: {DATA_PARQUET} ({DATA_PARQUET.stat().st_size / 1_000_000:.1f} MB), {rows} baris")
    return 0


if __name__ == "__main__":
    sys.exit(main())
