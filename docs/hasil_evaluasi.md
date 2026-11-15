# Hasil Evaluasi PhishGuard

- Tanggal evaluasi: 2026-11-15T06:29:56+00:00
- Model A terbaik: `rf` (50 fitur) ·
  Model B terbaik: `xgb` (19 fitur)
- Angka training/CV bersumber dari `docs/metrics.json` (`trained_at` = 2026-11-15T05:27:42+00:00)
- Test set: 47159 baris, stratified 80/20 (seed 42,
  train 188636). Test set tidak dipakai saat training.
- Definisi: **FP** = aktual legit (1) diprediksi phishing (0); **FN** = aktual phishing (0) diprediksi legit (1).
  Semua metrik phishing memakai `pos_label=0`.

## Tabel metrik (test set)

| Model | fitur | accuracy | precision (phishing) | recall (phishing) | F1 (phishing) | FP | FN |
|---|---|---|---|---|---|---|---|
| B | 19 | 0.9968 | 0.9986 | 0.9940 | 0.9963 | 28 | 122 |
| A | 50 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 0 | 0 |

### Confusion matrix — Model B (URL-only, produksi)

| aktual \ prediksi | phishing (0) | legit (1) |
|---|---|---|
| **phishing (0)** | TP=20067 | FN=122 |
| **legit (1)** | FP=28 | TN=26942 |

TP=20067, FN=122, FP=28, TN=26942 (threshold=0.5, P(phishing) = predict_proba[:, 0])

### Confusion matrix — Model A (full, laporan)

| aktual \ prediksi | phishing (0) | legit (1) |
|---|---|---|
| **phishing (0)** | TP=20189 | FN=0 |
| **legit (1)** | FP=0 | TN=26970 |

TP=20189, FN=0, FP=0, TN=26970 (threshold=0.5, P(phishing) = predict_proba[:, 0])

## Contoh False Positive — Model B

Total **28** baris (28 URL unik); 10 contoh teratas ditampilkan.

| URL | P(phishing) | label benar | top-3 fitur menyimpang (vs rata-rata kelas) |
|---|---|---|---|
| `https://www.san-francisco.investinluxembourg.us` | 0.9908 | legit | DomainLength=39 (rata2 kelas=19.2)<br>NoOfLettersInURL=40 (rata2 kelas=21.9)<br>URLLength=47 (rata2 kelas=27.2) |
| `https://www.thebertonandeastbridge.onesuffolk.net` | 0.9682 | legit | DomainLength=41 (rata2 kelas=19.2)<br>NoOfLettersInURL=43 (rata2 kelas=21.9)<br>URLLength=49 (rata2 kelas=27.2) |
| `https://www.79798282.net` | 0.9218 | legit | NoOfDegitsInURL=8 (rata2 kelas=0.0517)<br>NoOfLettersInURL=11 (rata2 kelas=21.9)<br>DegitRatioInURL=0.333 (rata2 kelas=0.00207) |
| `https://www.maslo.top` | 0.8455 | legit | TLDLegitimateProb=0.00426 (rata2 kelas=0.82)<br>DomainLength=13 (rata2 kelas=19.2)<br>NoOfLettersInURL=16 (rata2 kelas=21.9) |
| `https://www.reporterosasociados.com.co` | 0.8278 | legit | DomainLength=30 (rata2 kelas=19.2)<br>NoOfLettersInURL=32 (rata2 kelas=21.9)<br>NoOfSubDomain=2 (rata2 kelas=1.16) |
| `https://www.sopo-cundinamarca.gov.co` | 0.8217 | legit | DomainLength=28 (rata2 kelas=19.2)<br>NoOfSubDomain=2 (rata2 kelas=1.16)<br>TLDLegitimateProb=0.244 (rata2 kelas=0.82) |
| `https://www.formula1-dictionary.net` | 0.7733 | legit | NoOfDegitsInURL=1 (rata2 kelas=0.0517)<br>DomainLength=27 (rata2 kelas=19.2)<br>URLLength=35 (rata2 kelas=27.2) |
| `https://www.svyat-olga-lyublino.ru` | 0.7629 | legit | NoOfOtherSpecialCharsInURL=5 (rata2 kelas=3.08)<br>DomainLength=26 (rata2 kelas=19.2)<br>TLDLegitimateProb=0.34 (rata2 kelas=0.82) |
| `https://www.extremefishing-botadubrovnik.com` | 0.7165 | legit | DomainLength=36 (rata2 kelas=19.2)<br>NoOfLettersInURL=38 (rata2 kelas=21.9)<br>URLLength=44 (rata2 kelas=27.2) |
| `https://www.javerianacali.edu.co` | 0.7029 | legit | NoOfSubDomain=2 (rata2 kelas=1.16)<br>TLDLegitimateProb=0.244 (rata2 kelas=0.82)<br>DomainLength=24 (rata2 kelas=19.2) |

## Contoh False Negative — Model B

Total **122** baris (122 URL unik); 10 contoh teratas ditampilkan.

| URL | P(phishing) | label benar | top-3 fitur menyimpang (vs rata-rata kelas) |
|---|---|---|---|
| `https://www.kidzcommunity.org` | 0.0005 | phishing | NoOfDegitsInURL=0 (rata2 kelas=4.36)<br>URLLength=29 (rata2 kelas=46.3)<br>NoOfOtherSpecialCharsInURL=3 (rata2 kelas=5.28) |
| `https://www.xvsc.my.id` | 0.0006 | phishing | NoOfDegitsInURL=0 (rata2 kelas=4.36)<br>NoOfLettersInURL=16 (rata2 kelas=34.2)<br>URLLength=22 (rata2 kelas=46.3) |
| `https://www.hirosguide.hu` | 0.0010 | phishing | NoOfDegitsInURL=0 (rata2 kelas=4.36)<br>URLLength=25 (rata2 kelas=46.3)<br>NoOfLettersInURL=20 (rata2 kelas=34.2) |
| `https://www.ridm.in` | 0.0012 | phishing | NoOfDegitsInURL=0 (rata2 kelas=4.36)<br>URLLength=19 (rata2 kelas=46.3)<br>NoOfLettersInURL=14 (rata2 kelas=34.2) |
| `https://www.metanfo.fr` | 0.0012 | phishing | NoOfDegitsInURL=0 (rata2 kelas=4.36)<br>URLLength=22 (rata2 kelas=46.3)<br>NoOfLettersInURL=17 (rata2 kelas=34.2) |
| `https://www.unisonhomes.com.au` | 0.0014 | phishing | NoOfDegitsInURL=0 (rata2 kelas=4.36)<br>NoOfSubDomain=2 (rata2 kelas=1.17)<br>NoOfOtherSpecialCharsInURL=3 (rata2 kelas=5.28) |
| `https://www.versoflor.de` | 0.0015 | phishing | NoOfDegitsInURL=0 (rata2 kelas=4.36)<br>URLLength=24 (rata2 kelas=46.3)<br>NoOfLettersInURL=19 (rata2 kelas=34.2) |
| `https://www.in.mt` | 0.0015 | phishing | NoOfDegitsInURL=0 (rata2 kelas=4.36)<br>NoOfLettersInURL=12 (rata2 kelas=34.2)<br>URLLength=17 (rata2 kelas=46.3) |
| `https://www.tinyurl.com` | 0.0016 | phishing | NoOfDegitsInURL=0 (rata2 kelas=4.36)<br>URLLength=23 (rata2 kelas=46.3)<br>NoOfLettersInURL=18 (rata2 kelas=34.2) |
| `https://www.alullanos.com` | 0.0018 | phishing | NoOfDegitsInURL=0 (rata2 kelas=4.36)<br>URLLength=25 (rata2 kelas=46.3)<br>NoOfLettersInURL=20 (rata2 kelas=34.2) |

## Keterbatasan yang teramati (draf analisis, finalisasi oleh owner)

- Fitur paling berpengaruh Model B: `IsHTTPS` (0.749), `NoOfOtherSpecialCharsInURL` (0.191), `NoOfDegitsInURL` (0.029).
  Dominasi `IsHTTPS` berarti model banyak belajar "phishing cenderung tanpa HTTPS" — pola era dataset,
  sementara phishing 2026 umumnya memakai HTTPS.
- Model A: `URLSimilarityIndex` (0.208), `NoOfExternalRef` (0.155), `LineOfCode` (0.128) — fitur konten halaman inilah yang membuat
  angkanya ~1.00 dan tidak tersedia saat inference live (leakage yang didokumentasikan, bukan disembunyikan).
- False positive Model B: 28 baris (28 URL unik) — pola yang terlihat: URL legit pendek,
  HTTPS, tanpa digit/simbol, sering berupa domain bank/populer dengan path `/login`.
- False negative Model B: 122 baris (122 URL unik) — pola: URL phishing pendek dan "bersih"
  (`https://…`, tanpa query, sedikit simbol), mirip URL legit di dataset.
- Kesimpulan draf: performa test tinggi karena distribusi dataset; risiko utama di data live adalah
  ketergantungan pada HTTPS dan keterbatasan fitur leksikal murni (lihat T11 untuk uji URL live).
