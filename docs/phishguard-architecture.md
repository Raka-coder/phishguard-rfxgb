# PhishGuard — Dokumen Arsitektur

> **Dokumen 2 dari 4.** Pendamping: `phishguard-prd.md` (kebutuhan), `phishguard-schema.md` (kontrak data), `phishguard-implementation.md` (langkah kerja).

---

## 1. Gambaran Umum

PhishGuard adalah sistem deteksi phishing berbasis URL dengan arsitektur **4 lapisan**, semuanya Python, dijalankan lokal di laptop anggota (tanpa cloud, tanpa LLM):

```
┌──────────────────────────────────────────────────────────────────────┐
│  L4. UI — Reflex (pure Python → compile ke React)                    │
│      frontend :3000 │ backend Reflex :8000                           │
│      Halaman: index (cek URL) │ evaluasi (metrik & confusion matrix) │
└──────────────────────────────┬───────────────────────────────────────┘
                               │ HTTP (base_url api)
┌──────────────────────────────▼───────────────────────────────────────┐
│  L3. API — FastAPI + uvicorn, PORT 8001                              │
│      POST /check  → validasi URL → predict_url() → JSON 200/400      │
└──────────────────────────────┬───────────────────────────────────────┘
┌──────────────────────────────▼───────────────────────────────────────┐
│  L2. ML — src/predict.py + src/model.pkl (Model B, URL-only)         │
│      extract_features(url) → DataFrame 1 baris → model → probabilitas│
│      + feature importance lokal                                      │
└──────────────────────────────────────────────────────────────────────┘
┌──────────────────────────────────────────────────────────────────────┐
│  L1. DATA — offline, sekali setup per laptop                         │
│      data/PhiUSIIL.csv (zip Kaggle)                                  │
│        → DuckDB inspect (scripts/inspect_data.py)                    │
│        → DuckDB COPY → data/PhiUSIIL.parquet (ZSTD, sekali)          │
│      training: pandas read_parquet → src/train.py → model A & B      │
└──────────────────────────────────────────────────────────────────────┘
```

Alasan pemisahan lapisan: model (L2) tidak pernah tahu tentang web (L3/L4); API bisa didemokan terpisah dengan `curl`; UI tidak pernah menyentuh dataset.

---

## 2. Lapisan Data (L1) — DuckDB → Parquet

### 2.1 Alur
1. `data/PhiUSIIL.csv` berasal dari ZIP Kaggle yang diekstrak manual (lihat implementation).
2. **Inspeksi** (`scripts/inspect_data.py`): DuckDB menjalankan SQL **langsung ke file CSV** tanpa memuat penuh ke RAM — `DESCRIBE`, `COUNT`, `GROUP BY label`, `USING SAMPLE`. Output ini juga alat verifikasi wajib (R1: arah label).
3. **Konversi** (`scripts/convert_parquet.py`): satu perintah `COPY (SELECT * FROM read_csv_auto(...)) TO 'data/PhiUSIIL.parquet' (FORMAT PARQUET, COMPRESSION ZSTD)`. Dilakukan **sekali per laptop**.
4. **Training/EDA lanjutan** membaca Parquet (`pd.read_parquet`) — lebih cepat & hemat RAM daripada CSV.

### 2.2 Kenapa DuckDB + Parquet (keputusan desain)
- CSV 130–150 MB membuat IDE lag dan parse pandas lambat; DuckDB query tanpa load penuh → EDA instan di laptop minim spek.
- Parquet: kolom-terkompresi, portabel, deterministik antar Windows — hasil konversi identik di semua anggota.
- File `.duckdb`/`.parquet`/CSV tidak di-commit; setiap anggota membangunnya lokal dari ZIP Kaggle yang sama (lisensi CC BY-NC-SA 4.0 juga melarang redistribusi dataset).
- **Fallback** (R4): bila `fit` OOM, downcast float64→float32 atau iterasi `pd.read_csv(..., chunksize=100_000)` untuk engineering fitur bertahap.

### 2.3 Prinsip anti-leakage arsitektural
Satu sumber (kolom `URL` + dataset) → dua **proyeksi fitur** berbeda:
- **Proyeksi A (full)**: 50 kolom numerik dataset — dipakai Model A (evaluasi/laporan).
- **Proyeksi B (URL-only, 19 fitur)**: dihitung **ulang dari string URL** oleh
  `feature_utils.extract_features()` saat training, bukan disalin dari kolom dataset — dipakai Model B
  (produksi). Ini yang menjamin definisi fitur saat training identik dengan saat inference.
Proyeksi didaftarkan eksplisit di `src/config.py` (`FULL_FEATURES`, `URL_FEATURES`), sehingga mustahil
Model B tanpa sengaja menerima fitur konten.

---

## 3. Lapisan ML (L2)

### 3.1 Strategi dua model

| | Model A — "full" | Model B — "url" (produksi) |
|---|---|---|
| Artefak | `src/model_full.pkl` | `src/model.pkl` |
| Fitur | 54 fitur numerik PhiUSIIL | Subset leksikal (daftar di schema) |
| Input | Baris dataset lengkap | **String URL bebas** dari pengguna |
| Ketersediaan fitur saat live | Banyak fitur konten tak bisa dihitung | Semua fitur bisa dihitung dari URL |
| Peran | Evaluasi & laporan (angka ~97–99%) | Dipakai API & Reflex |
| Model | RF, XGBoost (+ baseline Logistic Regression) | RF, XGBoost |

### 3.2 Komponen

- `src/config.py` — konstanta: path, seed 42, daftar kolom proyeksi A & B, konstanta label `LABEL_LEGIT=1, LABEL_PHISH=0`, threshold 0.5.
- `src/feature_utils.py` — fungsi murni `extract_features(url: str) -> dict` (fitur leksikal dari string) + helper konversi dict → DataFrame kolom urut sesuai Model B.
- `src/train.py` — baca Parquet → verifikasi dtype kolom numerik = `FULL_FEATURES` → split stratified 80/20 (seed 42) → latih LR/RF/XGBoost untuk kedua proyeksi → pilih terbaik per proyeksi via **5-fold CV pada train** (F1 kelas phishing) → refit & simpan `model.pkl`, `model_full.pkl`, `src/tld_probs.json`, `docs/metrics.json`, `docs/stats.json`.
- `src/evaluate.py` — evaluasi Model A & Model B pada test set → precision/recall/F1/accuracy, confusion matrix, **kumpulkan contoh FP & FN nyata** → tulis `docs/hasil_evaluasi.md`.
- `src/predict.py` — `predict_url(url) -> {"url","label","label_name","probability","inference_ms","top_features"}`; memuat `model.pkl` sekali (singleton) agar latensi < 200 ms.

### 3.3 Alur inference (live)
```
URL string (dari Reflex atau curl)
  → extract_features(url)            # murni, tanpa jaringan
  → pd.DataFrame([features])[kolom_model_B]
  → model.predict_proba              # [P(legit), P(phish)]
  → probabilitas phishing = p[0]     # label 0 = phishing (R1!)
  → ambil top-k fitur paling menyimpang dari rata-rata kelas
  → dict JSON
```
Tidak ada akses jaringan, tidak ada fetching halaman — klausa etika terpenuhi secara arsitektural.

---

## 4. Lapisan API (L3)

- FastAPI di **:8001** (Reflex backend memakai :8000 — R6).
- `POST /check` body `{"url": "..."}` → validasi (skema & heuristik dasar: harus ada scheme/host) → `predict_url` → **200** dengan JSON hasil; body tidak valid → **400** `{"detail": "..."}`.
- `GET /health` untuk pengecekan cepat.
- API dipanggil Reflex melalui konfigurasi `api_url` (bisa dioverride lewat `.env`, tidak di-commit).

---

## 5. Lapisan UI (L4) — Reflex

- Proyek Reflex berada di root repo (`rxconfig.py`) dengan modul `app/`.
- State (`rx.State`) hanya menyimpan input URL, hasil prediksi, dan flag loading; mutasi hanya di event handler (`handle_check` memanggil API :8001 via `httpx`).
- Halaman:
  - `app/pages/index.py` — form input + kartu hasil (label, gauge probabilitas, waktu, tabel top features). Render bersyarat **wajib** `rx.cond`, daftar fitur wajib `rx.foreach` (kesalahan Reflex paling umum — NF5).
  - `app/pages/evaluasi.py` — membaca `docs/hasil_evaluasi.md`/`metrics.json` dan menampilkan metrik Model A vs B + confusion matrix.
- Halaman evaluasi **tidak** memanggil model; hanya membaca artefak evaluasi.

---

## 6. Alur End-to-End (urutan hidup proyek)

```
[OFFLINE, sekali]  ZIP Kaggle → extract → data/PhiUSIIL.csv
                   uv run python scripts/inspect_data.py      (verifikasi: 235.795; 1:134.850; 0:100.945)
                   uv run python scripts/convert_parquet.py   → data/PhiUSIIL.parquet

[OFFLINE, saat retrain]
                   uv run python src/train.py     → model.pkl, model_full.pkl, docs/metrics.json
                   uv run python src/evaluate.py  → docs/hasil_evaluasi.md (metrik + FP/FN)

[ONLINE demo]
                   uv run uvicorn api.main:app --port 8001     (terminal 1)
                   CI=1 uv run reflex run                      (terminal 2)
                   browser :3000 → paste URL → hasil
                   curl -X POST :8001/check -d '{"url":"..."}' (demo programatik)
```

---

## 7. Keputusan Arsitektural & Rasional (ringkas)

| Keputusan | Rasional |
|---|---|
| DuckDB untuk inspeksi, bukan pandas penuh | RAM hemat (NF2), laptop minim spek (R3), verifikasi label wajib (R1) |
| Parquet sebagai format kerja | Kecepatan baca + deterministik antar anggota (R10) |
| Dua model, bukan satu | Fitur konten tak tersedia live → leakage (R2) |
| FastAPI terpisah, bukan logika model di Reflex | API dapat didemokan/diuji mandiri; port 8001 (R6) |
| Predict singleton preload | Latensi < 200 ms |
| Data tidak di-commit | Ukuran + lisensi CC BY-NC-SA 4.0; tiap anggota build lokal |
| Tidak ada LLM | Di luar scope yang disepakati; kebutuhan tugas terpenuhi dengan klasik ML |
