# PhishGuard — Dokumen Implementasi (Setup + Task Breakdown untuk AI Agent/CLI)

> **Dokumen 4 dari 4.** Pendamping: `phishguard-prd.md`, `phishguard-architecture.md`, `phishguard-schema.md`.
> Dokumen ini adalah **petunjuk kerja untuk agent CLI**: kerjakan tugas T1–T12 berurutan, setiap tugas punya Definition of Done (DoD) yang bisa diverifikasi dengan perintah.

---

## 1. Prasyarat

| Prasyarat | Cara cek |
|---|---|
| Windows 10/11 + Python 3.11+ | `python --version` |
| uv terinstall | `uv --version` (jika belum: `powershell -c "irm https://astral.sh/uv/install.ps1 \| iex"`) |
| Git | `git --version` |
| Dataset ZIP Kaggle sudah diekstrak → `data/PhiUSIIL.csv` | cek `data/` |
| (Bila bun DLL error saat menjalankan Reflex) | Install Microsoft Visual C++ 2015 Redistributable x64 |

**Aturan emas:** semua perintah Python selalu lewat `uv run ...` — dilarang `python`/`pip` global (NF1).

---

## 2. Setup dari Nol (urutan persis)

```powershell
# 0. Buat repo lokal + GitHub remote (nama WAJIB: phishguard-rfxgb)
mkdir phishguard-rfxgb; cd phishguard-rfxgb
git init

# 1. Inisialisasi proyek uv (membuat pyproject.toml)
uv init --python 3.11

# 2. Tambah dependensi (terkunci di uv.lock)
uv add pandas duckdb pyarrow scikit-learn xgboost joblib fastapi "uvicorn[standard]" httpx reflex

# 3. Buat folder kerja
mkdir data, notebooks, src, app\pages, api, scripts, tests\fixtures, docs

# 4. Taruh dataset: ekstrak ZIP Kaggle → data/PhiUSIIL.csv  (TIDAK di-commit)

# 5. Tulis .gitignore (isi di bagian 4) lalu commit awal
git add . ; git commit -m "chore: init project"

# 6. Verifikasi data (WAJIB sebelum training — memverifikasi arah label R1)
uv run python scripts/inspect_data.py
#  HARUS mencetak: 235795 baris; label 1: 134850, label 0: 100945

# 7. Konversi sekali ke Parquet
uv run python scripts/convert_parquet.py   # → data/PhiUSIIL.parquet

# 8. Inisialisasi Reflex (pilih template 0 / blank)
uv run reflex init

# 9. Training + evaluasi (setelah kode src/ selesai — T5, T6)
uv run python src/train.py
uv run python src/evaluate.py

# 10. Jalankan sistem (2 terminal)
uv run uvicorn api.main:app --port 8001     # terminal 1
CI=1 uv run reflex run                      # terminal 2 → http://localhost:3000
```

Catatan Windows: `CI=1 uv run reflex run` di PowerShell → `$env:CI=1; uv run reflex run`. `CI=1` dipakai untuk verifikasi headless (frontend :3000, backend :8000, tanpa buka browser).

---

## 3. Struktur Proyek Final

```
phishguard-rfxgb/
├── rxconfig.py                  # config Reflex (dibuat reflex init)
├── pyproject.toml + uv.lock     # dependensi terkunci (uv.lock WAJIB di-commit)
├── README.md                    # langkah setup ringkas (bagian 2) — untuk anggota baru
├── .gitignore
├── data/                        # gitignored: PhiUSIIL.csv, PhiUSIIL.parquet
├── scripts/
│   ├── inspect_data.py          # DuckDB: DESCRIBE, COUNT, GROUP BY label, sampel 5 baris
│   └── convert_parquet.py       # DuckDB COPY CSV → Parquet ZSTD
├── notebooks/                   # EDA pribadi; output sel dibersihkan sebelum commit
├── src/
│   ├── config.py                # seed 42, LABEL_LEGIT=1/LABEL_PHISH=0, URL_FEATURES, FULL_FEATURES, path
│   ├── feature_utils.py         # extract_features(url) -> dict (murni)
│   ├── train.py                 # split stratified → RF & XGBoost (A & B) → model.pkl, model_full.pkl, docs/metrics.json
│   ├── evaluate.py              # metrik + confusion matrix + contoh FP/FN → docs/hasil_evaluasi.md
│   └── predict.py               # predict_url(url) -> dict; model preload singleton
├── api/
│   └── main.py                  # FastAPI :8001 — POST /check, GET /health
├── app/
│   ├── rxconfig ada di root; app_state.py  # rx.State + event handlers
│   └── pages/
│       ├── index.py             # form URL + kartu hasil (rx.cond, rx.foreach)
│       └── evaluasi.py          # tampil metrik A vs B + confusion matrix
├── tests/
│   ├── test_predict.py          # unit test extract_features & predict_url + assertion arah label
│   └── fixtures/urls.txt        # korpus URL uji (phish/legit/edge)
└── docs/                        # dokumen spesifikasi ini + hasil_evaluasi.md, metrics.json, screenshots/
```

---

## 4. Isi `.gitignore` (lengkap)

```gitignore
# data — JANGAN commit (ukuran + lisensi CC BY-NC-SA)
data/
*.zip
*.parquet
*.duckdb

# environment & build
.venv/
__pycache__/
*.pyc
.web/
state.json

# rahasia & lokal
.env
.env.local
kaggle.json
```

---

## 5. Task Breakdown untuk Agent CLI (T1–T12)

> Kerjakan berurutan. Setiap tugas: (a) buat file, (b) verifikasi DoD dengan perintah, (c) commit dengan pesan yang disebut.

**T1 — Scaffolding & gitignore**
Buat struktur bagian 3 + `.gitignore` bagian 4 + README (salin setup bagian 2).
DoD: `git status` tidak menampilkan `data/` dalam tracked files.

**T2 — scripts/inspect_data.py**
DuckDB in-memory (`duckdb.connect()`), cetak: skema (`DESCRIBE SELECT * FROM 'data/PhiUSIIL.csv'`), jumlah baris, `GROUP BY label`, sampel 5 baris kolom kunci.
DoD: output menunjukkan 235.795 baris & distribusi label sesuai schema §1.1.

**T3 — scripts/convert_parquet.py**
`COPY (SELECT * FROM read_csv_auto('data/PhiUSIIL.csv')) TO 'data/PhiUSIIL.parquet' (FORMAT PARQUET, COMPRESSION ZSTD)`.
DoD: file parquet ada; `duckdb.query("SELECT COUNT(*) FROM 'data/PhiUSIIL.parquet'")` = 235.795.

**T4 — src/config.py + src/feature_utils.py**
`config.py`: seed 42, konstanta label, `FULL_FEATURES` (dari output DESCRIBE T2, kecuali `URL`,`Domain`,`Filename`,`label`) dan `URL_FEATURES` (subset leksikal — cocokkan nama persis dengan dataset, ingat ejaan `Degit`/`Spacial`). `feature_utils.py`: `extract_features(url)` sesuai kontrak schema §2 + builder DataFrame.
DoD: `uv run python -c "from src.feature_utils import extract_features; print(extract_features('https://192.168.0.1/paypal-login-verify.xyz'))"` menampilkan dict fitur lengkap tanpa `None`.

**T5 — src/train.py**
Baca Parquet → downcast float32 → split stratified 80/20 seed 42 → latih: Logistic Regression (baseline), RF, XGBoost × dua proyeksi (A full, B URL) → pilih terbaik per proyeksi berdasar F1 kelas phishing → simpan artefak + `docs/metrics.json`.
DoD: kedua .pkl ada; F1 Model B ≥ 0.95; `metrics.json` terisi.

**T6 — src/evaluate.py + docs/hasil_evaluasi.md**
Evaluasi test set: precision/recall/F1/accuracy + confusion matrix kedua model; kumpulkan contoh FP & FN dari test set (≥3 masing-masing, tulis URL + label benar + probabilitas).
DoD: `docs/hasil_evaluasi.md` berisi tabel metrik dan daftar FP/FN nyata.

**T7 — src/predict.py + tests/test_predict.py**
`predict_url(url)`: validasi dasar (scheme+host) → extract_features → DataFrame urut `URL_FEATURES` → `model.predict_proba` → P(phishing)=proba[label==0] → top-5 features (deviasi thd rata-rata kelas dari training stats tersimpan). Test: assertion arah label, URL phishing tipikal → P>0.8, wikipedia.org → P(phishing)<0.2, input kosong → raise/ditolak.
DoD: `uv run pytest -q` hijau.

**T8 — api/main.py (FastAPI :8001)**
`POST /check` (schema §4), `GET /health`; error handler 400; CORS untuk localhost:3000.
DoD: `curl -X POST http://localhost:8001/check -H "Content-Type: application/json" -d "{\"url\":\"https://www.wikipedia.org\"}"` → 200 berisi label_name LEGITIMATE; body kosong → 400.

**T9 — Reflex state + halaman index**
`app/app_state.py` (schema §5) + `app/pages/index.py`: input URL, tombol Periksa (event handler → httpx POST :8001), kartu hasil.
DoD: **`CI=1 uv run reflex run`** jalan tanpa error; paste URL → verdict tampil; TIDAK ada `if`/`for` Python biasa atas Var di render tree (pakai `rx.cond`/`rx.foreach`).

**T10 — Halaman evaluasi**
`app/pages/evaluasi.py` baca `docs/metrics.json`/`hasil_evaluasi.md` → tampil tabel metrik A vs B + confusion matrix.
DoD: halaman tampil di :3000/evaluasi dengan angka yang sama dengan metrics.json.

**T11 — scripts/test_live_urls.py + fixtures/urls.txt**
Korpus: 3–5 URL phishing PhishTank (terverifikasi, dicatat + screenshot), 3–5 legitim (Tranco), edge cases. Script memanggil `predict_url` dan mencetak tabel hasil.
DoD: `uv run python scripts/test_live_urls.py` menampilkan tabel; hasil disalin ke `docs/hasil_evaluasi.md` bagian "Uji Live".

**T12 — Poles & dokumentasi**
README final, catatan FP/FN tambahan dari uji live, screenshot ke `docs/screenshots/`, tag `v1.0` di Git.
DoD: ke-9 poin Kriteria Sukses di PRD §9 tercentang; video demo dapat direkam mengikuti skenario 1–4.

---

## 6. Konvensi Kode

- Python murni; UI 100% Python Reflex — **dilarang** menulis JS/HTML/JSX manual atau mengedit `.web/` (NF6).
- State Reflex: mutasi hanya dalam event handler; Var turunan lewat `@rx.var`.
- Fungsi ML murni & deterministik (seed 42, NF4); tanpa state global kecuali singleton model di `predict.py`.
- Nama kolom dataset **disalin persis** dari `DESCRIBE` (ejaan `Degit`, `Spacial`).
- Setiap modul punya docstring 1 baris; comment menjelaskan "kenapa", bukan "apa".

## 7. Kolaborasi Git (3 anggota)

1. `uv.lock` **selalu** di-commit → `uv sync` memberi environment identik.
2. Data tidak di-commit; anggota baru: clone → `uv sync` → ekstrak ZIP ke `data/` → `uv run python scripts/convert_parquet.py` → verifikasi dengan `inspect_data.py` (output harus sama semua anggota).
3. Notebook: bersihkan output sebelum commit; logika permanen taruh di `scripts/`/`src/`.
4. Branch `main` + branch fitur per tugas (T1–T12), PR kecil, merge cepat.
5. Verifikasi sebelum push: `uv run pytest -q` dan (bila menyentuh UI) `CI=1 uv run reflex run`.

## 8. Perintah Harian (cheat sheet)

| Tujuan | Perintah |
|---|---|
| Verifikasi data | `uv run python scripts/inspect_data.py` |
| Konversi ke Parquet | `uv run python scripts/convert_parquet.py` |
| Training | `uv run python src/train.py` |
| Evaluasi + FP/FN | `uv run python src/evaluate.py` |
| Test unit | `uv run pytest -q` |
| API | `uv run uvicorn api.main:app --port 8001` |
| Web app (headless verifikasi) | `CI=1 uv run reflex run` |
| Web app (dev normal) | `uv run reflex run` |
| Uji URL live | `uv run python scripts/test_live_urls.py` |
| Debug Reflex | `uv run reflex run --loglevel debug` |

## 9. Referensi untuk Agent

- Dokumen Reflex untuk agent: `https://reflex.dev/docs/llms.txt` dan `https://reflex.dev/docs/ai/integrations/agent-toolkit.md` — baca sebelum menulis kode UI; cek `uv run reflex --version`.
- Dataset paper: doi:10.1016/j.cose.2023.103545.
- Sumber URL live: PhishTank (phishtank.org) untuk phishing terverifikasi; Tranco list untuk legitim. **Etika (NF): hanya analisis string URL — tidak fetch halaman, tidak menyerang pihak ketiga.**
