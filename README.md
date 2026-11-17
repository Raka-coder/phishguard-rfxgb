# PhishGuard — Deteksi Phishing Berlapis dari URL

[![Python](https://img.shields.io/badge/Python-3.11-3776AB?style=flat-square&logo=python&logoColor=white)](https://www.python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.163-009688?style=flat-square&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Reflex](https://img.shields.io/badge/Reflex-0.11-6C5CE7?style=flat-square)](https://reflex.dev)
[![Tests](https://img.shields.io/badge/tests-143%20passed-brightgreen?style=flat-square)](#testing)
[![Dataset](https://img.shields.io/badge/Dataset-CC%20BY--NC--SA%204.0-lightgrey?style=flat-square)](https://creativecommons.org/licenses/by-nc-sa/4.0/)

PhishGuard mengklasifikasikan URL sebagai **phishing**, **legitimate**, atau **TIDAK TERVERIFIKASI** dengan
model yang dilatih dari dataset [PhiUSIIL](https://www.kaggle.com/datasets/ndarvind/phiusiil-phishing-url-dataset),
lalu menjelaskan setiap vonis lewat `trail` (lapisan mana yang memutuskan dan kenapa). Antarmuka memakai
**Reflex** (100% Python) dan inference dilayani **FastAPI**. Proyek mata kuliah Keamanan Informasi —
KP70065004, Informatika, Universitas Siliwangi.

> Tujuan utamanya bukan sekadar angka tinggi di test set, melainkan deteksi yang jujur: menampilkan
> kelemahan, memisahkan hasil test set dari uji dunia nyata, dan menjelaskan batas tiap lapisan.

## Arsitektur berlapis

Setiap permintaan berhenti di lapisan pertama yang memutuskan. Urutannya:

```
URL
 │
 ├─1─ denylist feed OpenPhish (snapshot lokal, offline) ── cocok ──> PHISHING
 │        feed hilang/basi -> dilewati, tercatat di trail
 ├─2─ allowlist domain tepercaya (offline, ~60 domain) ── cocok ──> LEGITIMATE
 ├─3─ Model C (host, 10 fitur) + Model B (URL, 19 fitur)
 │        dua skor dipetakan ke zona rendah / sedang / tinggi:
 │        sama-sama rendah -> LEGITIMATE, sama-sama tinggi -> TIDAK TERVERIFIKASI,
 │        berbeda -> TIDAK TERVERIFIKASI
 ├─4─ shortener (bit.ly, t.co, dll.) ──> TIDAK TERVERIFIKASI bila masih LEGITIMATE
 └─5─ uncertainty band Model B 0,40–0,65 ──> TIDAK TERVERIFIKASI
```

- **Model A** (50 fitur, termasuk konten halaman) hanya untuk laporan; fitur kontennya tidak tersedia
  saat inference live, jadi angkanya jangan dibandingkan langsung dengan Model B.
- **Model B** (`src/model.pkl`, XGBoost, 19 fitur leksikal) dan **Model C**
  (`models/experimental/C_host.pkl`, 10 fitur host) dipakai API/UI. Model C bersifat opsional: tanpa
  artefaknya, vonis memakai Model B saja.
- Arah label dataset terbalik: `1 = legitimate`, `0 = phishing`, sehingga
  `P(phishing) = predict_proba[:, 0]`. Skor phishing-as-positive dipakai di semua metrik.
- **Tanpa jaringan saat inference.** Ekstraksi fitur murni string → dict; tidak ada fetch, resolve,
  atau probe ke URL yang dianalisis. Lihat [Etika](#etika).

Respons API memuat `verdict`, `risk_level`, `decision_source`, `reason`, dan `trail`. Field lama
`label` (0/1) tetap ada untuk kompatibilitas. Detail kontrak ada di `docs/phishguard-schema.md`.

## Hasil

Metrik test set (47.159 baris, tidak pernah dilatih) — angka dari `docs/hasil_evaluasi.md`:

| Model | Fitur | Accuracy | Precision (phishing) | Recall (phishing) | F1 (phishing) | FP | FN |
|---|---|---|---|---|---|---|---|
| B — URL-only (xgb) | 19 | 0.9968 | 0.9986 | 0.9940 | 0.9963 | 28 | 122 |
| A — full (rf, laporan) | 50 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 0 | 0 |

Angka dunia nyata jauh lebih rendah dan sengaja ditampilkan apa adanya di halaman **Evaluasi**:
`docs/realworld.json`, `docs/t25.json`, dan `docs/denylist.json`. Semua angka dibaca dari JSON yang
dihasilkan skrip — tidak ditulis manual di UI. Bacaan singkat: `docs/realworld_README.md`,
`docs/model_c.md`, `docs/denylist_README.md`.

> Label contoh FP/FN di `docs/hasil_evaluasi.md` berasal dari dataset PhiUSIIL dan **belum diverifikasi
> independen**; jangan menyebut domain nyata sebagai phishing tanpa catatan itu.

## Clone bersih — Windows

```powershell
git clone https://github.com/Raka-coder/phishguard-rfxgb.git
cd phishguard-rfxgb

# uv mengunduh Python 3.11 bila belum ada
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
uv sync

# Dataset (butuh internet; idempotent). Fallback: lihat "Dataset" di bawah.
uv run python scripts/download_data.py
uv run python scripts/convert_parquet.py
uv run python scripts/inspect_data.py   # wajib: 235795 baris; label 1:134850, 0:100945

# Artefak sudah di-commit: src/model.pkl, models/experimental/C_host.pkl,
# models/experimental/tld_probs_host.json, src/tld_probs.json -> tidak perlu training ulang.
# Bila ingin melatih ulang dari awal:
uv run python src/train.py              # menimpa metrics.json/stats.json — simpan dulu jika perlu
uv run python scripts/train_t25.py      # menghasilkan ulang C_host.pkl + tld_probs_host.json

# Opsional: snapshot feed untuk lapisan denylist (satu-satunya skrip yang memakai jaringan)
uv run python scripts/sync_feeds.py

uv run pytest -q                        # 143 tests
uv run reflex compile                  # cek UI tanpa server

# Terminal 1 — API
uv run uvicorn api.main:app --port 8001
# Terminal 2 — UI (headless/CI)
$env:CI=1; uv run reflex run            # frontend :3000, backend :8000
```

Bila frontend Reflex gagal start di Windows dengan error DLL/bun, pasang Microsoft Visual C++
2015 Redistributable x64.

## Clone bersih — Linux / macOS

```bash
git clone https://github.com/Raka-coder/phishguard-rfxgb.git
cd phishguard-rfxgb

curl -LsSf https://astral.sh/uv/install.sh | sh
uv sync

uv run python scripts/download_data.py
uv run python scripts/convert_parquet.py
uv run python scripts/inspect_data.py

# Opsional: snapshot feed denylist
uv run python scripts/sync_feeds.py

uv run pytest -q
uv run reflex compile

# Terminal 1 — API
uv run uvicorn api.main:app --port 8001
# Terminal 2 — UI (headless/CI)
CI=1 uv run reflex run
```

Semua perintah Python **wajib** lewat `uv run`; jangan pakai `python`/`pip` global. Jalankan dari root repo.

> **Verifikasi wajib:** `inspect_data.py` harus mencetak persis `235795 baris; label 1: 134850, 0: 100945`.
> Kalau berbeda, STOP dan laporkan.

## Artefak yang dibutuhkan aplikasi

Artefak berikut **ada di repo** dan langsung dipakai saat inference:

| File | Ukuran | Kegunaan |
|---|---|---|
| `src/model.pkl` | 880.792 byte | Model B (XGBoost, 19 fitur) |
| `src/tld_probs.json` | kecil | probabilitas TLD untuk Model B |
| `models/experimental/C_host.pkl` | 1.210.954 byte | Model C (host, 10 fitur) |
| `models/experimental/tld_probs_host.json` | tabel TLD host |  |

Hash SHA256 artefak model (dari commit ini):

```
9e7293bddfc3cb79a4fde0c7aa445aa759e2ab8556c61902231051c3dc0e280b  src/model.pkl
60faa4123b57a44aaacf20b3eeb21bf2159cdc81afc2c4653e1f9ac830e8a231  models/experimental/C_host.pkl
00a6de620719b2dc0833f3acff39a88f8effa3da5856da233b5bc88cb526bd39  models/experimental/tld_probs_host.json
5087b2324f6a4cc4e082c33987b0558efbf00506c9b554557b759ddfe2f521ee  src/tld_probs.json
```

> **Keamanan:** `joblib`/pickle dapat menjalankan kode saat dimuat. Muat hanya artefak dari repo ini.
> Setelah training ulang, hash berubah — perbarui daftar di atas bila artefak di-commit ulang.

Yang **tidak** ada di repo dan harus dibuat/diunduh lokal:

- `data/PhiUSIIL.csv` dan `data/PhiUSIIL.parquet` — dataset berlisensi (lihat bawah).
- `src/model_full.pkl` — Model A, hanya dipakai `src/evaluate.py`; buat dengan `uv run python src/train.py`.
- `data/feeds/` — snapshot OpenPhish, harus diunduh sendiri lewat `scripts/sync_feeds.py` dan tidak
  boleh didistribusikan ulang. Tanpa snapshot ini, lapisan denylist dilewati dengan aman.

## Dataset

- `uv run python scripts/download_data.py` mengunduh dari Kaggle
  ([ndarvind/phiusiil-phishing-url-dataset](https://www.kaggle.com/datasets/ndarvind/phiusiil-phishing-url-dataset))
  dan menyalinnya ke `data/PhiUSIIL.csv` (idempotent). `convert_parquet.py` membuat parquet sekali per mesin.
- **Fallback manual:** unduh ZIP dari halaman Kaggle, ekstrak, rename menjadi `data/PhiUSIIL.csv`, lalu
  jalankan ulang `scripts/download_data.py` (akan terdeteksi "sudah ada" dan skip).
- Sumber: Prasad & Chandra (2023), *PhiUSIIL: A diverse security profile empowered phishing URL detection
  framework*, Computers & Security, doi:[10.1016/j.cose.2023.103545](https://doi.org/10.1016/j.cose.2023.103545).
- Lisensi **CC BY-NC-SA 4.0** — non-komersial, dengan atribusi, turunan dibagikan dengan lisensi sama.
  Dataset tidak di-commit.

## sinkronisasi feed

Satu-satunya skrip yang boleh mengakses jaringan adalah `uv run python scripts/sync_feeds.py`. Ia
menyimpan snapshot bertanggal di `data/feeds/openphish-YYYYMMDD-HHMMSS.txt` tanpa menimpa snapshot lama.
`src/denylist.py` mencocokkan URL secara offline terhadap snapshot terbaru; snapshot basi
(default 24 jam, `PHISHGUARD_FEED_MAX_AGE_HOURS`) dilewati. Aturan evaluasi dan lisensi ada di
`docs/denylist_README.md`.

## Testing

```powershell
uv run pytest -q                                  # 143 tests
uv run pytest -q tests/test_predict.py::test_nama
uv run reflex compile                             # build UI tanpa server
uv run python scripts/test_live_urls.py           # uji corpus contoh sintetis
uv run python scripts/test_live_urls.py --markdown
```

`tests/fixtures/urls.txt` berisi **contoh sintetis** berlabel (bukan URL phishing nyata dari feed) plus
URL legitimate modern. Untuk uji dunia nyata, ikuti `docs/realworld_README.md` dan unduh feed sendiri.

## Konfigurasi lingkungan (.env)

Salin template bila perlu: `copy .env.example .env` (Windows) atau `cp .env.example .env` (Linux/macOS).
`.env` di-gitignore; variabel shell (`$env:...` / `export ...`) lebih prioritas.

```env
PHISHGUARD_API_URL=http://localhost:8001/check
PHISHGUARD_FEED_DIR=data/feeds
PHISHGUARD_FEED_MAX_AGE_HOURS=24
```

## Struktur proyek

```
src/           config.py, feature_utils.py, features_host.py, reputation.py, denylist.py,
               predict.py, train.py, evaluate.py, model.pkl, tld_probs.json
models/experimental/  C_host.pkl, tld_probs_host.json (Model C; varian riset lainnya di-gitignore)
api/           main.py — FastAPI :8001 (/check, /health)
app/           app.py, app_state.py, pages/ (index, evaluasi), style.py, limitations.json
scripts/       download_data.py, convert_parquet.py, sync_feeds.py, train_t25.py,
               eval_t25.py, eval_denylist.py, test_live_urls.py, …
tests/         test_*.py + fixtures/urls.txt
data/          dataset & snapshot feed — gitignored
docs/          spesifikasi, hasil evaluasi, dan JSON agregat (tanpa URL feed)
assets/        ikon/font UI (perhatikan lisensi aset pihak ketiga sebelum publikasi)
```

## Konvensi penting

- Label dataset: `1 = legitimate`, `0 = phishing`. `P(phishing) = predict_proba[:, 0]`.
- Split hanya dari `src/config.py: make_split(df)` (stratified, seed 42); test set tidak dilatih.
- Model A hanya laporan; Model B/C yang dipakai API/UI. Fitur konten di Model B = kebocoran data.
- Model B dihitung ulang dari string URL via `extract_features()`, bukan disalin dari kolom dataset.
- Port: API `:8001`, backend Reflex `:8000`, frontend `:3000`.
- **Tanpa akses jaringan saat inference.**
- Reflex 0.11: halaman didaftarkan eksplisit dengan `app.add_page(...)`; alur memakai `rx.cond`/`rx.foreach`.

## Etika

Inference **tidak mengakses jaringan** dan tidak pernah membuka, me-resolve, atau memprobe URL yang
dianalisis. Hanya `scripts/sync_feeds.py` yang boleh mengunduh daftar feed publik secara berkala, dan
data feed **tidak didistribusikan ulang** (simpan lokal di `data/feeds/`). Dataset PhiUSIIL dipakai
untuk keperluan akademik non-komersial dengan atribusi (CC BY-NC-SA 4.0).

## Referensi

- Prasad & Chandra (2023), *PhiUSIIL: A diverse security profile empowered phishing URL detection framework*, Computers & Security, doi:[10.1016/j.cose.2023.103545](https://doi.org/10.1016/j.cose.2023.103545).
- Spesifikasi: [PRD](docs/phishguard-prd.md) · [arsitektur](docs/phishguard-architecture.md) · [skema](docs/phishguard-schema.md) · [PRD v2](docs/PRD-v2.md) · [denylist](docs/denylist_README.md).
