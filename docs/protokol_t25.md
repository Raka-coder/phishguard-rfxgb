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

## 7. Aturan keputusan (T25b)

Aturan ini diterapkan pada hasil set dev dunia nyata, sebelum set final dilihat.

1. Kandidat yang lolos harus memiliki recall pada test PhiUSIIL berkelompok
   >= 0,95.
2. Di antara yang lolos, pilih MCC tertinggi pada set dev dunia nyata.
3. Tie-break: ketahanan sensitivitas, yaitu perubahan skor/verdict terkecil pada
   variasi URL (hapus path/query, tukar http/https, tambah www., trailing slash).
4. Kandidat terpilih lalu dievaluasi **satu kali** pada set final.

## 8. Metrik tambahan untuk aturan kesepakatan (T25b)

- Recall-terjaring: phishing divonis `PHISHING` atau `SUSPICIOUS`.
- Proporsi legitimate yang divonis `SUSPICIOUS`.
- Specificity ketat: `SUSPICIOUS` dihitung salah.
- Specificity longgar: `SUSPICIOUS` dihitung benar.
- Rincian root vs berpath dan in vs not in allowlist untuk semua metrik.
