# PhishGuard — Deteksi Phishing Berbasis URL

Klasifikasi biner URL (phishing vs legitimate) memakai **Random Forest** dan **XGBoost** pada dataset
[PhiUSIIL](https://www.kaggle.com/datasets/ndarvind/phiusiil-phishing-url-dataset), dengan antarmuka web
**Reflex** (100% Python) dan **FastAPI** untuk inference.

Mata kuliah Keamanan Informasi — KP70065004, Informatika, Universitas Siliwangi.
Dataset: Prasad & Chandra (2023), doi:[10.1016/j.cose.2023.103545](https://doi.org/10.1016/j.cose.2023.103545), lisensi CC BY-NC-SA 4.0.

> Spesifikasi lengkap ada di `docs/`: [PRD](docs/phishguard-prd.md) · [arsitektur](docs/phishguard-architecture.md) · [skema & kontrak](docs/phishguard-schema.md) · [rencana implementasi T1–T12](docs/phishguard-implementation.md).

## Status

Setup selesai (T1–T3): environment, scaffolding Reflex, inspeksi data, dan konversi Parquet sudah jalan di
dataset yang ada di `data/`. Belum ada model terlatih, API, atau halaman UI — lihat peta jalan di bawah.

## Dataset

Dataset sudah tersedia lokal di `data/` (tidak pernah di-commit — lihat `.gitignore`):

| Berkas | Asal | Ukuran |
|---|---|---|
| `data/PhiUSIIL.csv` | [Kaggle: ndarvind/phiusiil-phishing-url-dataset](https://www.kaggle.com/datasets/ndarvind/phiusiil-phishing-url-dataset) — satu CSV di dalam ZIP | 54 MB, 235.795 × 55 |
| `data/PhiUSIIL.parquet` | dibuat lokal oleh `scripts/convert_parquet.py` (ZSTD) | 15 MB |

Nama berkas di ZIP Kaggle bisa berbeda (mis. `PhiUSIIL_Phishing_URL_Dataset.csv`); seluruh kode memakai
`data/PhiUSIIL.csv`, dan path itu didefinisikan sekali di `src/config.py` (`DATA_CSV`, `DATA_PARQUET`).
Jangan ganti nama atau memindahkan CSV tanpa memperbarui konstanta tersebut.

## Prasyarat

| Kebutuhan | Cek |
|---|---|
| Windows 10/11 + Python 3.11 | `uv --version` (uv mengunduh Python 3.11 otomatis sesuai `.python-version`) |
| [uv](https://docs.astral.sh/uv/) | `powershell -c "irm https://astral.sh/uv/install.ps1 \| iex"` |
| Git | `git --version` |
| Dataset CSV dari Kaggle | `data/PhiUSIIL.csv` (lihat bagian Dataset) |

Bila frontend Reflex gagal start dengan error DLL/bun di Windows, pasang
**Microsoft Visual C++ 2015 Redistributable x64**.

## Setup dari nol (anggota baru)

```powershell
git clone https://github.com/Raka-coder/phishguard-rfxgb.git
cd phishguard-rfxgb
uv sync                                  # environment identik dari uv.lock

# dataset: unduh ZIP dari Kaggle, ekstrak, rename hasilnya menjadi data/PhiUSIIL.csv
# (dataset ini TIDAK di-commit: data/ dan *.parquet ada di .gitignore)

uv run reflex init --name app --template blank --no-agents   # sekali saja, bila .web/ belum ada
uv run python scripts/inspect_data.py    # verifikasi: 235795 baris; label 1: 134850, 0: 100945
uv run python scripts/convert_parquet.py # sekali per laptop -> data/PhiUSIIL.parquet (15 MB)
```

## Menjalankan aplikasi

```powershell
uv run python src/train.py                   # latih model -> src/model.pkl, src/model_full.pkl, docs/metrics.json
uv run python src/evaluate.py                # metrik + contoh FP/FN -> docs/hasil_evaluasi.md
uv run uvicorn api.main:app --port 8001      # terminal 1 — API
uv run reflex run                            # terminal 2 — web di http://localhost:3000
```

## Perintah harian

| Tujuan | Perintah |
|---|---|
| Verifikasi data | `uv run python scripts/inspect_data.py` |
| Konversi CSV → Parquet | `uv run python scripts/convert_parquet.py` |
| Training | `uv run python src/train.py` |
| Evaluasi + FP/FN | `uv run python src/evaluate.py` |
| Test unit | `uv run pytest -q` (satu test: `uv run pytest -q tests/test_predict.py::test_nama`) |
| API | `uv run uvicorn api.main:app --port 8001` |
| Web app | `uv run reflex run` |
| Cek UI tanpa buka browser | `$env:CI=1; uv run reflex run` (atau `uv run reflex compile`) |
| Uji URL live | `uv run python scripts/test_live_urls.py` |
| Debug Reflex | `uv run reflex run --loglevel debug` |

Semua perintah Python **wajib** lewat `uv run` — jangan pakai `python`/`pip` global.

## Struktur

```
docs/                 4 dokumen spesifikasi + hasil evaluasi (metrics.json, hasil_evaluasi.md)
data/                 PhiUSIIL.csv (54 MB, Kaggle), PhiUSIIL.parquet (15 MB) — keduanya gitignored
scripts/              inspect_data.py, convert_parquet.py, test_live_urls.py
src/                  config.py (path, seed, label), feature_utils.py, train.py, evaluate.py, predict.py
api/main.py           FastAPI :8001 — POST /check, GET /health
app/app.py            entrypoint Reflex (rx.App + add_page)
app/app_state.py      rx.State + event handler
app/pages/            index.py (cek URL), evaluasi.py (metrik)
tests/                test_predict.py + fixtures/urls.txt
rxconfig.py, uv.lock, pyproject.toml
```

## Hal yang mudah salah

- **Arah label terbalik.** Di PhiUSIIL `1 = legitimate` (134.850 baris) dan `0 = phishing` (100.945 baris).
  Jadi probabilitas phishing adalah `predict_proba[:, 0]`, bukan `[:, 1]`. Distribusi angka di atas
  adalah gerbang verifikasi setiap anggota.
- **Dua model.** Model A (`src/model_full.pkl`, 54 fitur termasuk fitur konten halaman) hanya untuk
  evaluasi/laporan; Model B (`src/model.pkl`, fitur leksikal URL saja) yang dipakai API & UI. Fitur konten
  yang dimasukkan ke Model B adalah kebocoran data, bukan peningkatan.
- **Nama kolom jangan diketik dari ingatan.** Ejaan dataset: `NoOfDegitsInURL`, `DegitRatioInURL`,
  `SpacialCharRatioInURL`, `NoOfEqualsInURL`, `NoOfQMarkInURL`, `NoOfAmpersandInURL`,
  `NoOfOtherSpecialCharsInURL`. Jalankan `DESCRIBE` dulu.
- **Port.** API wajib `:8001`; `:8000` dipakai backend Reflex, `:3000` frontend.
- **Tanpa akses jaringan saat inference.** Hanya string URL yang dianalisis — tidak fetch, tidak resolve,
  tidak memindai situs pihak ketiga (klausa etika).
- **Reflex 0.11.** Halaman tidak lagi ditemukan otomatis dari `app/pages/`; daftarkan eksplisit dengan
  `app.add_page(index, route="/")` di `app/app.py`. Kontrol alur di dalam render tree memakai `rx.cond` /
  `rx.foreach`, bukan `if`/`for` Python atas Var; mutasi state hanya di event handler.
- **Jangan buka `data/PhiUSIIL.csv` di editor** dan jangan `pd.read_csv` untuk eksplorasi — query via
  DuckDB agar hemat RAM. DuckDB 2.0 menghapus `Relation.fetchone()`; pakai `.fetchall()` atau `.df()`.
- **Skrip di `scripts/` menambahkan root repo ke `sys.path`** (`sys.path.insert(0, ...parents[1])`) karena
  `src/` bukan paket terinstal. Skrip baru wajib menyalin dua baris itu agar `from src.config import …` jalan.

## Peta jalan

T1 scaffolding ✅ · T2 `inspect_data.py` ✅ · T3 `convert_parquet.py` ✅ · T4 `config.py` + `feature_utils.py` ·
T5 `train.py` · T6 `evaluate.py` · T7 `predict.py` + test · T8 API · T9 UI index · T10 halaman evaluasi ·
T11 uji URL live · T12 poles + tag `v1.0`. Detail DoD: `docs/phishguard-implementation.md` §5.

## Etika & lisensi

Proyek ini hanya menganalisis string URL dan tidak melakukan pemindaian atau serangan ke pihak ketiga.
Dataset dipakai untuk keperluan akademik non-komersial dengan atribusi (CC BY-NC-SA 4.0).
