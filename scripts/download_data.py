"""Unduh dataset PhiUSIIL otomatis via kagglehub (tanpa akun/API key)."""

import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

DATASET_SLUG = "ndarvind/phiusiil-phishing-url-dataset"
ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "data" / "PhiUSIIL.csv"
MIN_BYTES_OK = 100 * 1024 * 1024  # 100 MB


def _human_size(n: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024:
            return f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} TB"


def main() -> int:
    if TARGET.exists():
        print(f"Dataset sudah ada di {TARGET} (skipped)")
        print(f"Ukuran: {_human_size(TARGET.stat().st_size)}")
        print("Lanjutkan: uv run python scripts/convert_parquet.py")
        return 0

    try:
        import kagglehub
    except ImportError:
        print("kagglehub belum terpasang. Jalankan `uv sync` dulu.")
        return 1

    print(f"Mengunduh dataset '{DATASET_SLUG}' via kagglehub (butuh internet, ~150 MB)...")
    try:
        folder = Path(kagglehub.dataset_download(DATASET_SLUG))
    except Exception as exc:  # noqa: BLE001 - tampilkan pesan ramah, bukan traceback
        print("Gagal mengunduh dataset.")
        print(f"Penyebab: {exc}")
        print()
        print("Fallback manual:")
        print("  1. Buka https://www.kaggle.com/datasets/ndarvind/phiusiil-phishing-url-dataset")
        print("  2. Download ZIP, ekstrak, rename hasilnya menjadi data/PhiUSIIL.csv")
        print("  3. Jalankan ulang: uv run python scripts/download_data.py")
        return 1

    csvs = sorted(folder.rglob("*.csv"))
    if not csvs:
        print("Struktur dataset berubah: tidak ada file *.csv di hasil ekstrak.")
        print(f"Folder cache: {folder}")
        print("Lakukan download manual dari Kaggle dan taruh CSV di data/.")
        return 1

    if len(csvs) == 1:
        source = csvs[0]
    else:
        named = [p for p in csvs if p.name == "PhiUSIIL.csv"]
        if not named:
            print("Struktur dataset berubah: lebih dari satu CSV dan tidak ada 'PhiUSIIL.csv'.")
            print("File yang ditemukan:")
            for p in csvs:
                print(f"  - {p.name} ({p})")
            print("Lakukan download manual dan pilih CSV yang benar.")
            return 1
        source = named[0]

    TARGET.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, TARGET)  # copy, bukan move: cache kagglehub dipertahankan
    size = TARGET.stat().st_size
    print(f"Disalin: {source} -> {TARGET}")
    print(f"Ukuran: {_human_size(size)}")
    if size < MIN_BYTES_OK:
        print("PERINGATAN: ukuran < 100 MB, kemungkinan download tidak lengkap.")
    else:
        print("Ukuran OK.")
    print()
    print("Lanjutkan: uv run python scripts/convert_parquet.py")
    print("Lalu verifikasi: uv run python scripts/inspect_data.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
