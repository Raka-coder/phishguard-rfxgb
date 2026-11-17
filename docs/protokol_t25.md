# Protokol T25 — pemilihan kandidat Model B vs host-only

Protokol ini ditulis **sebelum** evaluasi dijalankan. Semua angka harus berasal dari
skrip; tidak ada angka manual.

## 1. Kandidat

1. `B_refit`: Model B (19 fitur URL) yang dilatih ulang pada split berkelompok T24.
2. `C_host`: model 10 fitur host-only, dengan **normalisasi awalan `www.` sebelum
   ekstraksi fitur** (host tanpa `www.`). Latih ulang dari awal; laporkan efek
   normalisasi dibanding `C_host` T24 (tanpa normalisasi).
3. `B+C` (aturan kesepakatan): `PHISHING` jika kedua model memvonis phishing,
   `LEGITIMATE` jika keduanya legit, selain itu `SUSPICIOUS`.

Ambang biner tetap 0,5 untuk kedua model (`P(phishing) >= 0,5`). Aturan kesepakatan
tidak melatih model baru.

## 2. Set yang dipakai untuk pemilihan (boleh dipakai)

- Test PhiUSIIL berkelompok (split T24: host tidak tumpang tindih).
- CV 5-fold berkelompok pada train (T24).
- `legit_dev.csv` (set legitimate T24a) + separuh phishing OpenPhish (seed 42).

## 3. Set yang hanya dievaluasi satu kali di akhir

- `legit_final.csv` + separuh phishing OpenPhish yang tersisa.
- Tidak ada penyesuaian ambang, fitur, atau pemilihan setelah melihat hasil ini.

## 4. Metrik

Untuk setiap kandidat dan aturan kesepakatan:

- Specificity (dengan CI Wilson 95%).
- Recall (dengan CI Wilson 95%).
- MCC.
- Untuk aturan kesepakatan: proporsi `SUSPICIOUS`.
- ROC-AUC dan F1 bila relevan.

Rincian per kelompok:

- root vs berpath.
- in allowlist vs not in allowlist.

## 5. Laporan

- Hasil dua benchmark (PhiUSIIL grouped test dan set dunia nyata) ditampilkan
  berdampingan, termasuk saat kandidat kalah.
- Perbandingan efek normalisasi `www.` pada `C_host`.
- Agregat T24a (jumlah URL legit per kelompok dan jumlah kontributor) bila
  tersedia; jika belum ada, dilaporkan sebagai belum tersedia.
- Keluaran: `docs/t25.md` dan `docs/t25.json`. Tidak ada URL di keluaran publik.

## 6. Batasan

- Tidak mengubah `src/predict.py`, API, UI, atau `src/model.pkl`.
- `legit_dev`/`legit_final` bersifat pribadi dan gitignored.
- Set legit T18/T24a kecil; interval kepercayaan lebar.
