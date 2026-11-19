Saya cek dulu commit terbaru dan struktur `results/` yang sudah Anda buat, supaya instruksi mengikuti tata letak aktual repo.
Verifikasi: commit terbaru `70f919bd` (19 Nov) — **T30 sudah selesai** (pengujian lapisan L0–L4 masuk). Folder `results/` belum ada di remote (Anda buat lokal, belum di-push — pastikan ikut ter-commit). Berikut instruksi yang disusun ulang dengan pemisahan bersih: **skrip tetap di `scripts/` (konvensi repo), semua keluaran laporan masuk ke `results/`, dokumen sumber lama di `docs/` tidak disentuh.**

---

# Paket Laporan Bab 3–5 (revisi: folder `results/`)

## Prinsip tata letak (jaga agar repo tetap rapi)

```
results/
├── data/                      # JSON hasil pengujian BARU (layer test lanjutan, set legit, FN, API examples)
│   └── api_examples/          # 3 contoh respons mentah /check
├── figures/                   # PNG grafik dari make_figures.py
├── diagrams/                  # sumber Mermaid (.mmd) untuk diagram arsitektur
├── screenshots/               # tangkapan layar manual owner (diceklis oleh agent)
└── laporan/                   # bab3.md, bab4.md, bab5.md, README.md, data_status.md
```

Aturan pemisahan: `docs/` **tidak ditambah/diubah** (JSON evaluasi lama seperti `metrics.json`, `realworld.json`, `layer_tests.json` tetap di tempatnya dan dibaca dari sana); skrip baru tetap masuk `scripts/`; input mentah set legit tetap di `data/realworld/` (gitignored, konvensi existing). `.gitignore` diperbarui hanya jika perlu; hasil akhir (`results/laporan/`, `results/figures/`, `results/data/`) di-commit supaya laporan reproducible.

---

## T31 — Produksi data yang masih kurang → `results/data/`

1. **Set legit Barat & Lokal:** ±40 URL legit (20 Barat: github, cloudflare pages, vercel, wikipedia, MDN, dst.; 20 lokal: kompas, detik, tokopedia, bri.co.id, kampus, pemerintah — termasuk beberapa dengan UTM panjang dan deploy cloud). URL mentah ke `data/realworld/legit_barat_lokal.txt` (gitignored) + dokumentasi sumber di `results/data/legit_barat_lokal_README.md`. Jalankan pipeline penuh via skrip baru `scripts/eval_legit_set.py` → per URL: verdict, risk_level, decision_source, trail ringkas, P(phishing) → `results/data/legit_barat_lokal_results.json`.
2. **Kategorisasi 122 FN:** skrip `scripts/categorize_fn.py` membaca daftar FN test set dari artefak evaluasi, klasifikasi per pola (pendek-bersih, shortener, domain tua, typosquatting via pencocokan string sederhana, lainnya) + 5 contoh URL per kategori → `results/data/fn_categories.json`.
3. **Contoh respons API:** curl `/check` lokal untuk 3 kasus (URL feed OpenPhish → PHISHING; github.com → LEGITIMATE; URL tak dikenal → TIDAK TERVERIFIKASI) → simpan JSON mentah di `results/data/api_examples/`.
4. **Distribusi zona band:** pastikan ada JSON yang mencatat jumlah URL real-world dan set legit Barat/Lokal yang jatuh di zona 0,40–0,65; kalau belum, tambahkan pengukurannya ke `scripts/eval_legit_set.py` dan `scripts/test_layers.py` (output JSON).
5. **Checklist screenshot:** agent mencetak daftar tangkapan layar yang dibutuhkan ke `results/screenshots/CHECKLIST.md` (halaman cek URL × 3 kasus dengan trail, halaman evaluasi); pengambilan gambar manual oleh owner, file disimpan di `results/screenshots/`.
6. **Catatan status data:** `results/laporan/data_status.md` — setiap butir: OK (file JSON asal) atau MISSING dengan alasan. Dilarang mengarang data; yang gagal dihasilkan ditandai MISSING, bukan diputarbelikkan.

---

## T32 — Grafik & diagram → `results/figures/` dan `results/diagrams/`

Buat `scripts/make_figures.py` (matplotlib; label Bahasa Indonesia; warna konsisten verdict merah/kuning/hijau; dpi ≥ 200; gagal keras jika JSON sumber hilang — tanpa fallback angka keras). Output PNG ke `results/figures/`:

1. `confusion_matrix.png` — 2×2 Model B ← `docs/metrics.json`
2. `model_comparison.png` — metrik Model A vs B + CV 5-fold ← `docs/metrics.json`
3. `auc_benchmarks.png` — AUC PhiUSIIL vs real-world ← `docs/realworld.json`
4. `path_ablation.png` — pintasan path/query (skor 0,876→0,201; AUC 0,669→0,954) ← JSON diagnostik
5. `feature_importance.png` — kontribusi fitur ← `docs/stats.json`
6. `feed_decay.png` — kurva umur entri denylist ← artefak T19b
7. `decision_composition.png` — komposisi keputusan isolasi & kumulatif ← `docs/layer_tests.json` (T30)
8. `legit_barat_lokal.png` — hasil set legit per sumber keputusan ← `results/data/legit_barat_lokal_results.json`
9. `fn_categories.png` — distribusi kategori FN ← `results/data/fn_categories.json`
10. `risk_band.png` — distribusi skor terhadap zona 0,40–0,65 ← JSON poin T31.4

Diagram (Mermaid `.mmd` di `results/diagrams/`, disisipkan sebagai blok kode di markdown): alur keputusan berlapis sesuai penomoran AKTUAL di `src/predict.py` (konfirmasi lapisan peniruan merek + shortener — sertakan bila ada), flowchart `predict_url` (short-circuit), flowchart `sync_feeds.py`. Setiap gambar wajib kapsi berbentuk klaim kalimat + catatan n (ukuran sampel) untuk data real-world. Tambahkan test kecil yang memastikan semua PNG non-kosong dan semua JSON yang dirujuk ada.

---

## T33 — Draf Bab 3–5 → `results/laporan/`

Tulis `bab3.md`, `bab4.md`, `bab5.md` dalam Bahasa Indonesia + `README.md` (indeks gambar/tabel/sumber JSON per bab). Struktur mengikuti outline owner (3A arsitektur, 3B pengolahan data, 3C logika prediksi, 3D UI; 4A lingkungan, 4B implementasi lapisan, 4C etika; 5A skenario, 5B evaluasi test set, 5C analisis FP, 5D FN & validasi dunia nyata, 5E efektivitas berlapis). Aturan:

- Semua angka/tabel merujuk JSON (`docs/*.json` atau `results/data/*.json`) — konsisten satu mekanisme referensi.
- Gambar disisipkan dengan path relatif (`../figures/...` dari folder laporan) + kapsi; contoh respons API sebagai code block.
- 5C tanpa studi kasus Cloudflare/Replit/Traveloka sebagai "FP": FP dianalisis dari 28 kasus test set + diagnostik path/query; kasus hosting modern/UTM masuk sebagai bagian set legit di 5D dan mitigasi di 5E, ditulis sesuai hasil aktual (LEGITIMATE maupun TIDAK TERVERIFIKASI sama-sama sah).
- 5E wajib: tabel perbandingan ML murni vs hybrid per tingkatan (dari `docs/layer_tests.json`) + paragraf peran band 0,40–0,65 dalam transparansi keputusan.
- Data MISSING → placeholder `<TODO: data X, lihat results/laporan/data_status.md>`, jangan diisi perkiraan.
- Setiap subbab minimal 2–3 paragraf naratif; istilah teknis dijelaskan saat pertama muncul.
- Verifikasi akhir: semua path gambar valid, semua angka terlacak ke JSON, `uv run pytest -q` hijau, daftar placeholder tersisa dilaporkan di akhir.

---

<!--Tiga catatan: (1) push dulu folder `results/` lokal Anda sebelum memberi instruksi ini ke agent, supaya struktur kosongnya sudah ada di remote dan commit tiap tugas mengisi folder yang sama; (2) T30 sudah selesai di `70f919bd`, jadi instruksi ini tidak lagi memintanya — grafik 7 langsung membaca `docs/layer_tests.json`; (3) setelah T33 selesai, kirim `results/laporan/data_status.md` ke saya — saya bisa review draf babnya dan bantu menyusun narasi yang belum mengalir sebelum Anda ekspor ke Word/PDF.-->