# Status data T31-T32

Diperbarui: 19 November 2026. T31 dan T32 belum di-commit; pekerjaan dilakukan bertahap
sesuai instruksi pemilik. `docs/` tidak diubah oleh T31 maupun T32.

## Butir T31

| # | Butir | Status | Artefak | Catatan |
|---|---|---|---|---|
| 1 | Set legit Barat & Lokal | OK | `results/data/legit_barat_lokal_results.json`; sumber `data/realworld/legit_barat_lokal.txt` (gitignored); dokumentasi `results/data/legit_barat_lokal_README.md` | 40 URL (20 Barat, 20 lokal). Ringkasan verdict/sumber/band ada di `summary`; trail per URL disimpan ringkas. |
| 2 | Kategorisasi FN | OK | `results/data/fn_categories.json` | FN dan FP dihitung ulang dari split + `src/model.pkl`, lalu dicocokkan ke `docs/hasil_evaluasi.md` (`source.verified=true`). Kategori `domain_tua` MISSING (lihat bawah). |
| 3 | Contoh respons API | OK | `results/data/api_examples/01_phishing_denylist.json`, `02_legit_allowlist.json`, `03_suspicious_unknown.json` | Respons mentah `POST /check` dari API lokal port 8001, HTTP 200. API dijalankan dengan `PHISHGUARD_USE_GOOGLE=false` dan batas umur feed 168 jam. |
| 4 | Distribusi zona band | OK | `results/data/band_distribution.json` | Memuat band Model B dan C untuk set real-world (`data/realworld/urls.csv`) dan set legit. Pengukur ditambahkan ke `scripts/eval_legit_set.py` dan `scripts/test_layers.py` (fungsi `band_counts`). |
| 5 | Checklist screenshot | OK (checklist), MISSING (gambar) | `results/screenshots/CHECKLIST.md` | Empat tangkapan layar wajib diambil manual oleh pemilik. CHECKLIST memuat arahan penyisipan markdown dan penomoran gambar untuk Bab 3-4. |
| 6 | Catatan status data | OK | `results/laporan/data_status.md` | Berkas ini. |

## Butir T32

| # | Butir | Status | Artefak | Catatan |
|---|---|---|---|---|
| 1 | Sepuluh grafik PNG | OK | `results/figures/*.png` | Dihasilkan `scripts/make_figures.py` (matplotlib, dpi 200, label Indonesia, warna vonis). Sumber JSON dicek di awal; sumber hilang = skrip berhenti. |
| 2 | Kapsi gambar | OK | `results/figures/CAPTIONS.md` | Sepuluh kapsi berbentuk klaim + catatan n + path sumber. |
| 3 | Diagram Mermaid | OK | `results/diagrams/alur_keputusan.mmd`, `predict_url.mmd`, `sync_feeds.mmd`, `README.md` | Lapisan mengikuti `src/predict.py`: L0 GSB opt-in, L1 denylist, L2 allowlist, L3 Model B+C, L4 shortener. Lapisan peniruan merek (T20) belum ada dan digambar sebagai catatan. |
| 4 | Tes artefak | OK | `tests/test_figures.py` | Memastikan 10 PNG ada, tidak kosong, ukuran wajar, dan seluruh JSON sumber ada. |

## MISSING dan alasan

| Hal | Status | Alasan |
|---|---|---|
| Gambar `results/screenshots/01_cek_phishing.png` dst. | OK | Diambil via Chrome DevTools pada 2026-11-19; app dijalankan dengan `PHISHGUARD_USE_GOOGLE=false` dan `PHISHGUARD_FEED_MAX_AGE_HOURS=168`. |
| Kategori `domain_tua` (di `fn_categories.json`) | DIHAPUS — tidak terukur offline, lihat future work | Taksonomi final hanya memakai kategori yang terukur dari string URL (pendek_bersih, shortener, typosquatting, lainnya). Kategori berbasis umur domain tidak dimasukkan; dicatat sebagai batas pengukuran. |
| Daftar 122 URL FN utuh | Sengaja tidak dibuat | Dataset CC BY-NC-SA; JSON hanya menyimpan 5 contoh per kategori. Daftar direproduksi deterministik oleh `scripts/categorize_fn.py`. |
| `results/laporan/bab3.md`, `bab4.md`, `bab5.md`, `README.md` | OK | T33 selesai. Empat berkas draf tersedia; placeholder screenshot tersisa (lihat bawah). |

## Penyimpangan sumber data pada T32

| Butir spesifikasi | Yang dipakai | Alasan |
|---|---|---|
| `confusion_matrix.png` dari `docs/metrics.json` | Blok `TP=..., FN=..., FP=..., TN=...` pertama di `docs/hasil_evaluasi.md` | `docs/metrics.json` tidak menyimpan confusion matrix; angka test set hanya ada di markdown evaluasi. Skrip berhenti bila pola tidak ditemukan. |
| `auc_benchmarks.png`: AUC PhiUSIIL | `docs/model_c.json` (`variants.B_refit.test_grouped.roc_auc`) | Tidak ada AUC PhiUSIIL di `docs/metrics.json`. Nilai ini dihitung pada split berkelompok per host setelah dedup, sehingga protokolnya berbeda dari split acak 80/20; hal itu ditulis di kapsi. |
| `path_ablation.png` dari "JSON diagnostik" | `docs/realworld.json` (`diagnosis.legit_variants`, `diagnosis.phishing_stripped`) | JSON itu satu-satunya sumber angka ablation path/query. |
| `feed_decay.png` dari "artefak T19b" | `docs/denylist.json` (`age_curve`) | Artefak T19b ditulis ke JSON tersebut; hanya ada dua titik pembanding pada 9,61 jam dengan retensi 33%. |

## Berkas yang ditambahkan/diubah T31

- `scripts/eval_legit_set.py` (baru) — evaluasi offline set legit, menulis hasil per URL,
  ringkasan band, dan `band_distribution.json`.
- `scripts/categorize_fn.py` (baru) — reproduksi FN test set dan kategorisasi string.
- `scripts/test_layers.py` — tambah `band_counts()` dan blok `band_distribution` pada
  keluaran JSON (tidak dijalankan ulang, sehingga `docs/layer_tests.json` tidak berubah).
- `tests/test_report_data.py` (baru) — 4 tes helper (parsing, band, Levenshtein/merek,
  prioritas kategori).
- `data/realworld/legit_barat_lokal.txt` — input mentah, gitignored.
- `results/` — struktur data, screenshot, figures, diagrams, laporan.

## Berkas yang ditambahkan/diubah T32

- `scripts/make_figures.py` (baru) — 10 grafik dari JSON/artefak; gagal keras bila sumber
  hilang.
- `results/figures/*.png` (10 berkas) + `results/figures/CAPTIONS.md`.
- `results/diagrams/*.mmd` (3 berkas) + `results/diagrams/README.md` (blok Mermaid siap
  tempel).
- `tests/test_figures.py` (baru) — 2 tes artefak.
- `pyproject.toml` dan `uv.lock` — `matplotlib` masuk dev dependency.
- `results/screenshots/CHECKLIST.md` — tambah arahan penyisipan markdown dan tabel
  penomoran gambar.

## Verifikasi yang dijalankan

- `uv run python scripts/eval_legit_set.py` — 40 URL, 0 error; JSON dan band JSON tertulis.
- `uv run python scripts/categorize_fn.py` — FN/FP cocok dengan `docs/hasil_evaluasi.md`;
  seluruh FN masuk kategori terukur (kecuali `domain_tua` yang MISSING).
- API lokal: tiga `POST /check` → HTTP 200; vonis `PHISHING`, `LEGITIMATE`, `SUSPICIOUS`.
- `uv run python scripts/make_figures.py` — 10 PNG tertulis; seluruh sumber JSON ada.
- `uv run pytest -q tests/test_figures.py` — 2 passed.
- `uv run pytest -q` — 188 passed, 1 warning (Starlette/httpx deprecation).
- `docs/` tidak diubah; `docs/command.md` masih modified dari sebelum sesi T31.

## Butir T33

| # | Butir | Status | Artefak | Catatan |
|---|---|---|---|---|
| 1 | Draf Bab 3 (3A arsitektur, 3B pengolahan data, 3C logika prediksi, 3D UI) | OK | `results/laporan/bab3.md` | Merujuk `docs/metrics.json`, `docs/stats.json`, `docs/hasil_evaluasi.md`, `src/predict.py`, `src/config.py`, `results/data/api_examples/*.json`. |
| 2 | Draf Bab 4 (4A lingkungan, 4B implementasi lapisan, 4C etika) | OK | `results/laporan/bab4.md` | Port 8001/8000/3000, env vars, klausul offline, lisensi. |
| 3 | Draf Bab 5 (5A skenario, 5B test set, 5C FP, 5D FN & validasi dunia nyata, 5E efektivitas berlapis) | OK | `results/laporan/bab5.md` | Tabel ML murni vs hybrid dari `docs/layer_tests.json` + paragraf band 0,40–0,65. |
| 4 | Indeks gambar/tabel/sumber JSON | OK | `results/laporan/README.md` | Semua path gambar valid; placeholder screenshot dicatat. |
| 5 | Rapikan bahasa (humanizer-indonesia) | OK | keempat berkas | `scripts/metrik.py` dijalankan; temuan audit di bawah. |
| 6 | Gambar screenshot aktual | OK | `results/screenshots/01_cek_phishing.png`, `02_cek_legit.png`, `03_cek_suspicious.png`, `04_evaluasi.png` | Diambil via Chrome DevTools; placeholder di bab diganti path aktual. |

## Temuan audit humanizer (T33)

- `bila` (5 di bab3, 5 di bab4) diganti `jika` sesuai register akademik.
- bab3 dan bab4 memiliki rerata panjang kalimat di bawah pita (13,9 dan 11,6 kata)
  dan kepadatan kata pemadat 56,6 dan 43,2 per 1.000 kata, di bawah rentang korpus
  (73–139). Prosa teknis cenderung mampat; tidak disisipkan kata isian. bab5 lulus
  seluruh baris berambang (rerata 15,8, simpangan baku 7,1).
- Tidak ada em dash/en dash di badan prosa, tidak ada `di mana` sebagai pronomina
  relatif, tidak ada penyangkalan antisipatif.
- Triplet terdeteksi 5 (bab3), 7 (bab4), 3 (bab5); sebagian berasal dari tabel dan
  daftar teknis yang memang perlu tiga butir.

## Catatan tata letak

- Semua keluaran T31 berada di `results/` di akar repo. Folder `docs/results/` yang sudah
  ada sebelumnya kosong dan tidak dipakai.
- `results/data/legit_barat_lokal_README.md` mencatat sumber URL dan batas tafsir.
- Angka rinci tidak ditulis ulang di sini; rujuk JSON masing-masing agar tidak ada
  duplikasi manual.
