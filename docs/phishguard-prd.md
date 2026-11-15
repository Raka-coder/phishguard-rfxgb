# PhishGuard — Product Requirements Document (PRD)

> **Dokumen 1 dari 4.** Dokumen pendamping: `phishguard-architecture.md`, `phishguard-schema.md`, `phishguard-implementation.md`.
> Palet warna & desain UI ditunda ke dokumen `phishguard-design.md` (akan dibuat belakangan).

---

## 1. Identitas Proyek

| Atribut | Nilai |
|---|---|
| Nama proyek | **PhishGuard** |
| Nama repo | `phishguard-rfxgb` |
| Judul resmi | Sistem Deteksi Phishing Berbasis URL Menggunakan Algoritme Random Forest dan XGBoost pada Dataset PhiUSIIL dengan Antarmuka Aplikasi Web Reflex |
| Mata kuliah | Keamanan Informasi — KP70065004, Semester Ganjil 2026/2027 |
| Institusi | Universitas Siliwangi — Prodi Informatika |
| Tim | 3 anggota |
| Topik | Topik 1: **Defensive AI** ("AI untuk Deteksi Ancaman") |
| Dataset | Kaggle `ndarvind/phiusiil-phishing-url-dataset` (PhiUSIIL) — sudah diunduh sebagai ZIP berisi 1 CSV, disimpan di `data/` |
| Lisensi dataset | CC BY-NC-SA 4.0 (non-komersial, atribusi wajib — hanya untuk tugas kuliah) |
| Bahasa / runtime | 100% Python 3.11+ |
| Package manager | **uv** (semua perintah via `uv run`) |
| ML | scikit-learn (Random Forest), xgboost (XGBoost), pandas, joblib |
| Data inspect layer | **DuckDB** (inspeksi CSV & agregasi tanpa memuat penuh ke RAM) + **Parquet** (format kerja setelah konversi sekali) |
| Web UI | **Reflex** (pure Python, tanpa JS/HTML manual) |
| API inference | FastAPI (uvicorn), **port 8001** (Reflex backend memakai 8000) |
| LLM lokal | **Tidak ada** (dihapus dari scope) |
| Target OS dev | Windows (laptop spesifikasi terbatas) |

Referensi utama dataset: Prasad & Chandra (2023), *PhiUSIIL: A diverse security dataset for phishing URL detection*, Computers & Security, doi:10.1016/j.cose.2023.103545.

---

## 2. Konteks & Kewajiban Tugas Dosen

Deliverable wajib yang dinilai (semua harus terpetakan ke artefak proyek):

1. **Model/aplikasi yang bisa dijalankan** — aplikasi web Reflex + model terlatih, dapat mendeteksi URL.
2. **Metrik evaluasi**: precision, recall, F1 (+ accuracy, confusion matrix) untuk kedua model.
3. **Analisis False Positive & False Negative** dengan minimal **3 contoh nyata masing-masing** dari hasil pengujian.
4. **Video demo 5–10 menit di YouTube**, semua anggota tampil, ditayangkan atau dikirim ke dosen.
5. **Laporan** (pendahuluan, metode, pembahasan, kesimpulan) — referensi laporan di `docs/hasil_evaluasi.md` sebagai bahan.
6. **Etika**: tidak menyerang pihak ketiga; proyek hanya menganalisis *string URL*, tidak melakukan scanning/serangan ke situs lain.

---

## 3. Tujuan & Non-Tujuan

### Tujuan (Goals)
- G1: Membangun klasifikasi biner URL (phishing vs legitimate) dengan Random Forest **dan** XGBoost, dibandingkan dengan baseline Logistic Regression.
- G2: Memisahkan dua model untuk menghindari leakage: **Model A** (full fitur, untuk evaluasi & laporan) dan **Model B** (URL-only, untuk aplikasi).
- G3: Aplikasi web Reflex yang menerima URL bebas dari pengguna dan menampilkan label + probabilitas + fitur yang paling berpengaruh.
- G4: Dataset besar (235.795 baris) dapat dianalisis di laptop minim spek tanpa lag — via DuckDB + Parquet.
- G5: Repo Git-ready: setup satu perintah (`uv sync`) sehingga 3 anggota dapat berkolaborasi dengan environment identik.

### Non-Tujuan (Non-Goals)
- Tidak melakukan content fetching / scraping halaman saat inference (fitur konten hanya dipakai di Model A dari data historis).
- Tidak memakai LLM lokal maupun remote.
- Tidak membuat browser extension / mobile app.
- Tidak melakukan deteksi yang memerlukan interaksi ke situs target (klausa etika).

---

## 4. Metrik Keberhasilan

| Metrik | Target | Catatan |
|---|---|---|
| F1-score Model A (full fitur) | ≥ 0.97 | Nilai ~0.99 normal karena fitur konten kuat (leakage dibahas di laporan, bukan disembunyikan) |
| F1-score Model B (URL-only) | ≥ 0.95 | Ini model produksi; harus realistis |
| Recall phishing Model B | ≥ 0.93 | Prioritas: phishing terlewat (FN) lebih berbahaya |
| Latensi inference per URL | < 200 ms | Diukur di laptop, termasuk ekstraksi fitur |
| Setup anggota baru | ≤ 10 menit | `clone → uv sync → taruh CSV → convert` |
| Verifikasi app | `CI=1 uv run reflex run` lolos tanpa error | Gerbang wajib sebelum commit fitur UI |

---

## 5. Kebutuhan Fungsional

| ID | Kebutuhan |
|---|---|
| F1 | Pengguna dapat memasukkan (paste) satu URL pada halaman utama aplikasi. |
| F2 | Aplikasi menampilkan hasil: label (PHISHING/LEGITIMATE), probabilitas, waktu inferensi. |
| F3 | Aplikasi menampilkan **top-k fitur** yang paling berkontribusi terhadap keputusan (feature importance lokal sederhana: perbandingan nilai fitur URL terhadap rata-rata kelas). |
| F4 | Aplikasi memvalidasi format URL; input tidak valid ditolak dengan pesan jelas (HTTP 400 dari API). |
| F5 | Halaman **Evaluasi** menampilkan metrik Model A vs Model B (precision/recall/F1/accuracy) + confusion matrix. |
| F6 | Terdapat endpoint API `POST /check` (FastAPI :8001) yang dapat dipanggil terpisah untuk demonstrasi programatik. |
| F7 | Model dapat di-retrain via `uv run python src/train.py` dari `data/PhiUSIIL.parquet` (seed 42, stratified split). |
| F8 | Dataset diinspeksi & dikonversi via **DuckDB**: `scripts/inspect_data.py` (skema, jumlah baris, distribusi label, sampel) dan `scripts/convert_parquet.py` (CSV → Parquet ZSTD, sekali jalan). |
| F9 | Terdapat `scripts/test_live_urls.py` + `fixtures/urls.txt` untuk pengujian URL live (PhishTank/Tranco) — hanya membaca string URL, tidak fetch. |
| F10 | Semua artefak penting (metrik, contoh FP/FN) terekam ke `docs/hasil_evaluasi.md` otomatis oleh `src/evaluate.py`. |

## 6. Kebutuhan Non-Fungsional

| ID | Kebutuhan |
|---|---|
| NF1 | Semua perintah dijalankan lewat `uv run` — dilarang `python`/`pip` global. |
| NF2 | RAM hemat: EDA & agregasi via DuckDB (query langsung ke CSV); Pandas hanya memuat Parquet saat training; fallback `chunksize=100_000` bila `fit` OOM. |
| NF3 | `data/` (CSV, ZIP, Parquet), `*.duckdb`, `.venv/`, `.web/`, `__pycache__/`, `.env`, `kaggle.json` **tidak pernah di-commit** (lihat `.gitignore`). |
| NF4 | Deterministik: seed 42 untuk split & model; split stratified; hasil evaluasi dapat direproduksi anggota lain. |
| NF5 | Reflex: state mutation hanya di event handler; dilarang control-flow Python biasa atas Var di render tree (pakai `rx.cond`/`rx.foreach`/operator Var). |
| NF6 | Kode UI 100% Python — tidak ada file JS/HTML/JSX manual; `.web/` tidak pernah diedit. |
| NF7 | Dokumentasi agent-friendly: keempat dokumen ini di `docs/`, agent CLI mengerjakan tugas berdasarkan task breakdown di `phishguard-implementation.md`. |

---

## 7. Skenario Pengguna

### Skenario 1 — Cek URL mencurigakan (demo utama)
Pengguna menemukan link mencurigakan di chat. Ia membuka aplikasi (localhost:3000), paste URL, klik **Periksa**. Dalam < 1 detik muncul verdict PHISHING dengan probabilitas 0.97 dan daftar fitur paling berpengaruh (mis. "domain memakai IP", "keyword 'login-verify'", "TLD .xyz").

### Skenario 2 — Verifikasi situs legitim
Pengguna mengecek `https://www.wikipedia.org` → LEGITIMATE dengan probabilitas tinggi. Ini menunjukkan model tidak "menebak-nebak semua phishing".

### Skenario 3 — URL baru yang tidak ada di dataset (generalisasi)
Demo mengambil URL phishing **terverifikasi hari ini** dari PhishTank yang pasti tidak ada di PhiUSIIL (dataset 2023). Model tetap mendeteksi karena belajar pola leksikal, bukan menghafal. Ini poin kunci laporan & video.

### Skenario 4 — Batas kemampuan (analisis FN)
URL phishing yang di-hosting di domain legitim yang diretas (URL-nya "terlihat wajar") mungkin lolos (FN). Tim mendokumentasikan contoh nyata di `docs/hasil_evaluasi.md` dan menjelaskan keterbatasan pendekatan URL-only.

---

## 8. Risiko & Mitigasi

| # | Risiko | Dampak | Mitigasi |
|---|---|---|---|
| R1 | **Arah label terbalik**: di PhiUSIIL `1 = legitimate`, `0 = phishing` (counterintuitive) | Seluruh evaluasi & UI salah arah | Verifikasi wajib via `scripts/inspect_data.py` sebelum training; klaim di kode: `LABEL_LEGIT=1, LABEL_PHISH=0`; satu test assertion di `tests/` |
| R2 | **Leakage**: fitur konten halaman memberi akurasi ~99% tetapi mustahil dihitung saat inference live | Model produksi tidak jalan di dunia nyata | Strategi dua model (A evaluasi vs B produksi); dibahas eksplisit di laporan |
| R3 | **Lag saat membuka CSV di IDE** (130–150 MB) | Buang waktu, salah persepsi "dataset besar" | Larang buka CSV di editor; semua inspeksi via DuckDB script yang mencetak ringkasan |
| R4 | **OOM saat training** di laptop minim spek | Training gagal | Downcast float64→float32, bila perlu `chunksize`; 54 fitur numerik × 235rb baris umumnya muat |
| R5 | **Reflex API drift / kesalahan umum** (control flow Python atas Var, state mutation di luar handler) | App gagal compile/render | Rujuk docs resmi (`https://reflex.dev/docs/llms.txt`); verifikasi `CI=1 uv run reflex run`; `--loglevel debug` saat diagnosa |
| R6 | **Konflik port**: Reflex backend bind :8000 | FastAPI gagal start | FastAPI **wajib** di :8001 |
| R7 | **Bun DLL error di Windows** (Reflex frontend) | Frontend tidak jalan | Install Microsoft Visual C++ 2015 Redistributable (sesuai docs Reflex) |
| R8 | **Konflik Git notebook** (output sel + metadata) | Kolaborasi 3 orang kacau | Notebook output dibersihkan sebelum commit; logika penting di `scripts/` bukan notebook |
| R9 | **Link phishing demo mati** (situs ditakedown cepat) | Demo gagal hari-H | Tangkap screenshot + rekam video lebih awal; string URL tetap bisa dianalisis meski situs mati |
| R10 | **Versi dependensi beda antar anggota** | "Di komputer A jalan, di B tidak" | `uv.lock` wajib di-commit; semua via `uv sync`/`uv run` |
| R11 | Dataset kadaluarsa terhadap phishing 2026 | Recall live turun | Akui di laporan; Act 3 demo menunjukkan generalisasi; cadangan dataset: UCI Phishing Websites (Plan B paling ringan) |

---

## 9. Kriteria Sukses (Definition of Done Proyek)

1. `uv run python scripts/inspect_data.py` mencetak: 235.795 baris; label `1: 134.850`, `0: 100.945` — sama di laptop ketiga anggota.
2. `uv run python src/train.py` menghasilkan `src/model.pkl` (Model B) & `src/model_full.pkl` (Model A) + `docs/metrics.json`.
3. `uv run python src/evaluate.py` menulis precision/recall/F1 + confusion matrix + kandidat FP/FN ke `docs/hasil_evaluasi.md`.
4. `CI=1 uv run reflex run` jalan bersih; halaman utama & halaman evaluasi tampil.
5. `POST http://localhost:8001/check` mengembalikan 200 untuk URL valid dan 400 untuk input tidak valid.
6. Minimal 3 contoh FP dan 3 FN nyata terdokumentasi.
7. Video demo 5–10 menit direkam (4 babak: phishing betulan → situs legitim → URL PhishTank baru → kasus tricky/FP).
