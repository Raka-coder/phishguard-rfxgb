# Diagnosis set uji dunia nyata (T18c/T18d)

Dihasilkan otomatis oleh `scripts/diagnose_realworld.py` pada 2026-11-16T23:55:04+00:00. Semua angka diambil dari skrip; dokumen ini tidak memuat URL.

## Cakupan

- Kelompok diagnosis: **not_in_allowlist + phishing** — 330 URL (300 phishing, 30 legitimate di luar allowlist).
- Model: Model B; ambang label 0.5.
- Kelompok ini dipakai karena domain allowlist diputuskan tanpa model.

## ROC-AUC dan PR-AUC

| Metrik | Nilai |
|---|---|
| ROC-AUC | 0.6687 |
| PR-AUC | 0.9223 |

AUC mengukur pemeringkatan skor, bukan kualitas vonis pada ambang tertentu.

## Distribusi skor per kelas

| Statistik | Phishing | Legit |
|---|---|---|
| n | 300 | 30 |
| mean | 0.9986 | 0.8391 |
| median | 1.0 | 0.9796 |
| min | 0.7125 | 0.2334 |
| max | 1.0 | 1.0 |
| predicted_phishing_pct | 100.0 | 83.33 |

| Kuantil | Phishing | Legit |
|---|---|---|
| 0.00 | 0.7125 | 0.2334 |
| 0.01 | 0.9963 | 0.2407 |
| 0.05 | 0.9999 | 0.2703 |
| 0.10 | 1.0 | 0.3024 |
| 0.25 | 1.0 | 0.8453 |
| 0.50 | 1.0 | 0.9796 |
| 0.75 | 1.0 | 1.0 |
| 0.90 | 1.0 | 1.0 |
| 0.95 | 1.0 | 1.0 |
| 0.99 | 1.0 | 1.0 |
| 1.00 | 1.0 | 1.0 |

## Sapuan ambang

> **Peringatan:** ambang di bawah dipilih/dibandingkan pada set kecil ini. Jangan menganggap ambang terbaik di sini sebagai hasil yang tervalidasi; risiko overfit tinggi. Ambang produksi harus ditentukan pada data lain.

| Ambang | Recall | Specificity | MCC | FP | FN | % diprediksi phishing |
|---|---|---|---|---|---|---|
| 0.10 | 1.0000 | 0.0000 | — | 30 | 0 | 100.0 |
| 0.11 | 1.0000 | 0.0000 | — | 30 | 0 | 100.0 |
| 0.12 | 1.0000 | 0.0000 | — | 30 | 0 | 100.0 |
| 0.13 | 1.0000 | 0.0000 | — | 30 | 0 | 100.0 |
| 0.14 | 1.0000 | 0.0000 | — | 30 | 0 | 100.0 |
| 0.15 | 1.0000 | 0.0000 | — | 30 | 0 | 100.0 |
| 0.16 | 1.0000 | 0.0000 | — | 30 | 0 | 100.0 |
| 0.17 | 1.0000 | 0.0000 | — | 30 | 0 | 100.0 |
| 0.18 | 1.0000 | 0.0000 | — | 30 | 0 | 100.0 |
| 0.19 | 1.0000 | 0.0000 | — | 30 | 0 | 100.0 |
| 0.20 | 1.0000 | 0.0000 | — | 30 | 0 | 100.0 |
| 0.21 | 1.0000 | 0.0000 | — | 30 | 0 | 100.0 |
| 0.22 | 1.0000 | 0.0000 | — | 30 | 0 | 100.0 |
| 0.23 | 1.0000 | 0.0000 | — | 30 | 0 | 100.0 |
| 0.24 | 1.0000 | 0.0333 | 0.1743 | 29 | 0 | 99.7 |
| 0.25 | 1.0000 | 0.0333 | 0.1743 | 29 | 0 | 99.7 |
| 0.26 | 1.0000 | 0.0667 | 0.2469 | 28 | 0 | 99.39 |
| 0.27 | 1.0000 | 0.0667 | 0.2469 | 28 | 0 | 99.39 |
| 0.28 | 1.0000 | 0.0667 | 0.2469 | 28 | 0 | 99.39 |
| 0.29 | 1.0000 | 0.1000 | 0.3029 | 27 | 0 | 99.09 |
| 0.30 | 1.0000 | 0.1000 | 0.3029 | 27 | 0 | 99.09 |
| 0.31 | 1.0000 | 0.1333 | 0.3503 | 26 | 0 | 98.79 |
| 0.32 | 1.0000 | 0.1333 | 0.3503 | 26 | 0 | 98.79 |
| 0.33 | 1.0000 | 0.1333 | 0.3503 | 26 | 0 | 98.79 |
| 0.34 | 1.0000 | 0.1333 | 0.3503 | 26 | 0 | 98.79 |
| 0.35 | 1.0000 | 0.1333 | 0.3503 | 26 | 0 | 98.79 |
| 0.36 | 1.0000 | 0.1333 | 0.3503 | 26 | 0 | 98.79 |
| 0.37 | 1.0000 | 0.1667 | 0.3922 | 25 | 0 | 98.48 |
| 0.38 | 1.0000 | 0.1667 | 0.3922 | 25 | 0 | 98.48 |
| 0.39 | 1.0000 | 0.1667 | 0.3922 | 25 | 0 | 98.48 |
| 0.40 | 1.0000 | 0.1667 | 0.3922 | 25 | 0 | 98.48 |
| 0.41 | 1.0000 | 0.1667 | 0.3922 | 25 | 0 | 98.48 |
| 0.42 | 1.0000 | 0.1667 | 0.3922 | 25 | 0 | 98.48 |
| 0.43 | 1.0000 | 0.1667 | 0.3922 | 25 | 0 | 98.48 |
| 0.44 | 1.0000 | 0.1667 | 0.3922 | 25 | 0 | 98.48 |
| 0.45 | 1.0000 | 0.1667 | 0.3922 | 25 | 0 | 98.48 |
| 0.46 | 1.0000 | 0.1667 | 0.3922 | 25 | 0 | 98.48 |
| 0.47 | 1.0000 | 0.1667 | 0.3922 | 25 | 0 | 98.48 |
| 0.48 | 1.0000 | 0.1667 | 0.3922 | 25 | 0 | 98.48 |
| 0.49 | 1.0000 | 0.1667 | 0.3922 | 25 | 0 | 98.48 |
| 0.50 | 1.0000 | 0.1667 | 0.3922 | 25 | 0 | 98.48 |
| 0.51 | 1.0000 | 0.1667 | 0.3922 | 25 | 0 | 98.48 |
| 0.52 | 1.0000 | 0.1667 | 0.3922 | 25 | 0 | 98.48 |
| 0.53 | 1.0000 | 0.1667 | 0.3922 | 25 | 0 | 98.48 |
| 0.54 | 1.0000 | 0.1667 | 0.3922 | 25 | 0 | 98.48 |
| 0.55 | 1.0000 | 0.1667 | 0.3922 | 25 | 0 | 98.48 |
| 0.56 | 1.0000 | 0.1667 | 0.3922 | 25 | 0 | 98.48 |
| 0.57 | 1.0000 | 0.1667 | 0.3922 | 25 | 0 | 98.48 |
| 0.58 | 1.0000 | 0.1667 | 0.3922 | 25 | 0 | 98.48 |
| 0.59 | 1.0000 | 0.1667 | 0.3922 | 25 | 0 | 98.48 |
| 0.60 | 1.0000 | 0.1667 | 0.3922 | 25 | 0 | 98.48 |
| 0.61 | 1.0000 | 0.1667 | 0.3922 | 25 | 0 | 98.48 |
| 0.62 | 1.0000 | 0.1667 | 0.3922 | 25 | 0 | 98.48 |
| 0.63 | 1.0000 | 0.1667 | 0.3922 | 25 | 0 | 98.48 |
| 0.64 | 1.0000 | 0.1667 | 0.3922 | 25 | 0 | 98.48 |
| 0.65 | 1.0000 | 0.1667 | 0.3922 | 25 | 0 | 98.48 |
| 0.66 | 1.0000 | 0.1667 | 0.3922 | 25 | 0 | 98.48 |
| 0.67 | 1.0000 | 0.1667 | 0.3922 | 25 | 0 | 98.48 |
| 0.68 | 1.0000 | 0.1667 | 0.3922 | 25 | 0 | 98.48 |
| 0.69 | 1.0000 | 0.1667 | 0.3922 | 25 | 0 | 98.48 |
| 0.70 | 1.0000 | 0.2000 | 0.4303 | 24 | 0 | 98.18 |
| 0.71 | 1.0000 | 0.2000 | 0.4303 | 24 | 0 | 98.18 |
| 0.72 | 0.9967 | 0.2000 | 0.3924 | 24 | 1 | 97.88 |
| 0.73 | 0.9967 | 0.2000 | 0.3924 | 24 | 1 | 97.88 |
| 0.74 | 0.9967 | 0.2333 | 0.4299 | 23 | 1 | 97.58 |
| 0.75 | 0.9967 | 0.2333 | 0.4299 | 23 | 1 | 97.58 |
| 0.76 | 0.9967 | 0.2333 | 0.4299 | 23 | 1 | 97.58 |
| 0.77 | 0.9967 | 0.2333 | 0.4299 | 23 | 1 | 97.58 |
| 0.78 | 0.9967 | 0.2333 | 0.4299 | 23 | 1 | 97.58 |
| 0.79 | 0.9967 | 0.2333 | 0.4299 | 23 | 1 | 97.58 |
| 0.80 | 0.9967 | 0.2333 | 0.4299 | 23 | 1 | 97.58 |
| 0.81 | 0.9967 | 0.2333 | 0.4299 | 23 | 1 | 97.58 |
| 0.82 | 0.9967 | 0.2333 | 0.4299 | 23 | 1 | 97.58 |
| 0.83 | 0.9967 | 0.2333 | 0.4299 | 23 | 1 | 97.58 |
| 0.84 | 0.9967 | 0.2667 | 0.4648 | 22 | 1 | 97.27 |
| 0.85 | 0.9967 | 0.2667 | 0.4648 | 22 | 1 | 97.27 |
| 0.86 | 0.9967 | 0.2667 | 0.4648 | 22 | 1 | 97.27 |
| 0.87 | 0.9967 | 0.2667 | 0.4648 | 22 | 1 | 97.27 |
| 0.88 | 0.9967 | 0.3333 | 0.5285 | 20 | 1 | 96.67 |
| 0.89 | 0.9967 | 0.3333 | 0.5285 | 20 | 1 | 96.67 |
| 0.90 | 0.9933 | 0.3333 | 0.5017 | 20 | 2 | 96.36 |
| 0.91 | 0.9933 | 0.3333 | 0.5017 | 20 | 2 | 96.36 |
| 0.92 | 0.9933 | 0.3333 | 0.5017 | 20 | 2 | 96.36 |
| 0.93 | 0.9933 | 0.3667 | 0.5320 | 19 | 2 | 96.06 |
| 0.94 | 0.9933 | 0.3667 | 0.5320 | 19 | 2 | 96.06 |
| 0.95 | 0.9933 | 0.4667 | 0.6157 | 16 | 2 | 95.15 |
| 0.96 | 0.9933 | 0.5000 | 0.6416 | 15 | 2 | 94.85 |
| 0.97 | 0.9933 | 0.5000 | 0.6416 | 15 | 2 | 94.85 |
| 0.98 | 0.9900 | 0.5000 | 0.6203 | 15 | 3 | 94.55 |
| 0.99 | 0.9900 | 0.5000 | 0.6203 | 15 | 3 | 94.55 |

## Kontribusi fitur pada FP di luar allowlist

Jumlah FP model-only di luar allowlist: **25**.
Kontribusi dihitung dengan `pred_contribs` XGBoost, lalu dirata-rata. Nilai positif berarti mendorong vonis phishing. URL tidak ditampilkan.

| Fitur | Rata-rata \|kontribusi\| | Rata-rata kontribusi ke phishing |
|---|---|---|
| `DomainLength` | 9.3912 | 9.3912 |
| `URLLength` | 5.4838 | 0.9226 |
| `NoOfOtherSpecialCharsInURL` | 2.6571 | 2.6571 |
| `NoOfSubDomain` | 1.7948 | 1.2716 |
| `IsHTTPS` | 1.0893 | -1.0893 |
| `NoOfDegitsInURL` | 0.6858 | -0.5461 |
| `NoOfLettersInURL` | 0.449 | -0.3806 |
| `TLDLegitimateProb` | 0.4097 | -0.3626 |
| `SpacialCharRatioInURL` | 0.192 | 0.1282 |
| `DegitRatioInURL` | 0.0449 | -0.0009 |

## Eksperimen varian URL legitimate

Jumlah URL legitimate: **55**. Skor adalah P(phishing) dari Model B.

| Varian | Mean | Median | Min | Max | % diprediksi phishing | Delta mean vs asli | Delta median | Naik | Turun |
|---|---|---|---|---|---|---|---|---|---|
| original | 0.8758 | 1.0 | 0.0033 | 1.0 | 89.09 | — | — | — | — |
| no_path_query | 0.2014 | 0.0021 | 0.0 | 0.9996 | 20.0 | -0.6744 | -0.9409 | 0 | 55 |
| www_prefix | 0.8741 | 0.9999 | 0.0033 | 1.0 | 89.09 | -0.0018 | 0.0000 | 6 | 4 |

## Hapus path/query pada URL phishing

Jumlah URL phishing: **300**, legitimate pembanding: **30** (kelompok diagnosis yang sama).

| Statistik skor phishing | Asli | Tanpa path/query | Perubahan |
|---|---|---|---|
| Mean | 0.9986 | 0.9045 | -0.0941 |
| Median | 1.0 | 1.0 | -0.0 |

Naik: 12, Turun: 283, Tetap: 5.

Legit pembanding: mean 0.8391 → 0.2006 (delta -0.6385).

| Perbandingan ROC-AUC | ROC-AUC | PR-AUC |
|---|---|---|
| Phishing stripped vs legit stripped | 0.9541 | 0.9949 |
| Referensi: URL asli | 0.6687 | 0.9223 |

Perbedaan AUC menunjukkan seberapa besar sinyal pemisah berasal dari path/query.

## Baseline satu fitur

Baseline memakai nilai fitur mentah pada kelompok diagnosis yang sama, tanpa latihan model.
Arah skor tetap: **nilai lebih besar = lebih condong phishing** (tanpa pembalikan tanda).

| Skor | Arah | ROC-AUC | PR-AUC |
|---|---|---|---|
| `URLLength` saja | higher_is_phishing | 0.9367 | 0.9927 |
| `DomainLength` saja | higher_is_phishing | 0.9522 | 0.9947 |
| Model B (19 fitur) | higher_is_phishing (P(phishing)) | 0.6687 | 0.9223 |

Baseline satu fitur hanya memakai satu kolom, sehingga perbandingan ini mengukur nilai tambah fitur lain secara kasar.

## Jejak kontribusi homepage legitimate

Kontribusi `pred_contribs` per URL; nilai positif berarti mendorong phishing. URL asli tidak ditampilkan (hanya label anonim).

| URL | Skor | Diprediksi phishing | Fitur pendorong utama |
|---|---|---|---|
| `legit_homepage_1` | 0.923 | ya | `DomainLength` (2.7809); `NoOfOtherSpecialCharsInURL` (2.2381); `IsHTTPS` (-1.3474) |
| `legit_homepage_2` | 0.8747 | ya | `DomainLength` (5.3999); `NoOfOtherSpecialCharsInURL` (2.2162); `URLLength` (-1.8769) |
| `legit_homepage_3` | 0.2845 | tidak | `DomainLength` (10.6723); `URLLength` (-8.1349); `NoOfOtherSpecialCharsInURL` (2.1225) |

URL dipilih deterministik: tiga URL legitimate pertama dengan path kosong/`/` tanpa query.

## Kesetaraan fitur (parity)

Sampel acak **5000** baris dari split train (seed 42; legit 2870, phishing 2130). Test tidak dipakai. 'Cocok persis' berarti sama persis dengan kolom dataset.

### Legit (n=2870)

| Fitur | Cocok persis | MAE | Maks abs | Korelasi |
|---|---|---|---|---|
| `URLLength` | 0.0% | 1.0 | 1.0 | 1.0000 |
| `DomainLength` | 100.0% | 0.0 | 0.0 | 1.0000 |
| `TLDLength` | 100.0% | 0.0 | 0.0 | 1.0000 |
| `NoOfSubDomain` | 100.0% | 0.0 | 0.0 | 1.0000 |
| `IsDomainIP` | 100.0% | 0.0 | 0.0 | — |
| `IsHTTPS` | 100.0% | 0.0 | 0.0 | — |
| `NoOfLettersInURL` | 0.0% | 9.0 | 9.0 | 1.0000 |
| `LetterRatioInURL` | 0.0% | 0.324224 | 0.517882 | 0.9366 |
| `NoOfDegitsInURL` | 100.0% | 0.0 | 0.0 | 1.0000 |
| `DegitRatioInURL` | 97.0% | 9.1e-05 | 0.009333 | 1.0000 |
| `NoOfEqualsInURL` | 100.0% | 0.0 | 0.0 | — |
| `NoOfQMarkInURL` | 100.0% | 0.0 | 0.0 | — |
| `NoOfAmpersandInURL` | 100.0% | 0.0 | 0.0 | — |
| `NoOfOtherSpecialCharsInURL` | 1.22% | 1.841115 | 2.0 | 0.6037 |
| `SpacialCharRatioInURL` | 0.0% | 0.068477 | 0.114471 | 0.5011 |
| `HasObfuscation` | 100.0% | 0.0 | 0.0 | — |
| `NoOfObfuscatedChar` | 100.0% | 0.0 | 0.0 | — |
| `ObfuscationRatio` | 100.0% | 0.0 | 0.0 | — |
| `TLDLegitimateProb` | 0.0% | 0.535927 | 0.995553 | -0.4042 |

### Phishing (n=2130)

| Fitur | Cocok persis | MAE | Maks abs | Korelasi |
|---|---|---|---|---|
| `URLLength` | 47.84% | 0.521596 | 1.0 | 1.0000 |
| `DomainLength` | 99.95% | 0.001878 | 4.0 | 1.0000 |
| `TLDLength` | 99.95% | 0.001878 | 4.0 | 0.9917 |
| `NoOfSubDomain` | 100.0% | 0.0 | 0.0 | 1.0000 |
| `IsDomainIP` | 99.95% | 0.000469 | 1.0 | 0.9352 |
| `IsHTTPS` | 99.72% | 0.002817 | 1.0 | 0.9944 |
| `NoOfLettersInURL` | 0.0% | 6.164319 | 16.0 | 0.9994 |
| `LetterRatioInURL` | 0.0% | 0.181291 | 0.523667 | 0.6771 |
| `NoOfDegitsInURL` | 98.64% | 0.013615 | 1.0 | 1.0000 |
| `DegitRatioInURL` | 56.1% | 0.000886 | 0.04 | 0.9996 |
| `NoOfEqualsInURL` | 99.77% | 0.002347 | 1.0 | 0.9979 |
| `NoOfQMarkInURL` | 100.0% | 0.0 | 0.0 | 1.0000 |
| `NoOfAmpersandInURL` | 96.9% | 0.094366 | 26.0 | 0.3173 |
| `NoOfOtherSpecialCharsInURL` | 10.66% | 1.585446 | 31.0 | 0.9360 |
| `SpacialCharRatioInURL` | 0.8% | 0.044544 | 0.173294 | 0.4753 |
| `HasObfuscation` | 97.79% | 0.022066 | 1.0 | 0.4603 |
| `NoOfObfuscatedChar` | 97.56% | 0.058685 | 15.0 | 0.8117 |
| `ObfuscationRatio` | 97.46% | 0.000488 | 0.104826 | 0.6479 |
| `TLDLegitimateProb` | 0.0% | 0.333794 | 0.984275 | 0.6352 |

### TLDLegitimateProb

- Tabel: `src/tld_probs.json` (12597 TLD), dibuat oleh `src/train.py` dari split train.
- Rumus per TLD: `(jumlah legit per TLD + 1) / (jumlah total per TLD + 2)`; default: `(jumlah legit train + 1) / (jumlah baris train + 2)` (Laplace smoothing).
- Nilai default dipakai pada **0.2%** baris sampel karena TLD tidak ada di tabel; nilai default tabel = `0.571894`.

## Fitur homepage legitimate: T18 vs data latih

Median fitur **3** homepage T18 (anonim) dibandingkan median **107880** homepage legitimate di data latih.

| Fitur | Median T18 | Rentang T18 | Median latih | Delta |
|---|---|---|---|---|
| `URLLength` | 28.0 | 21.0..30.0 | 27.0 | 1.0 |
| `DomainLength` | 19.0 | 12.0..21.0 | 19.0 | 0.0 |
| `TLDLength` | 2.0 | 2.0..2.0 | 3.0 | -1.0 |
| `NoOfSubDomain` | 2.0 | 2.0..2.0 | 1.0 | 1.0 |
| `IsDomainIP` | 0.0 | 0.0..0.0 | 0.0 | 0.0 |
| `IsHTTPS` | 1.0 | 1.0..1.0 | 1.0 | 0.0 |
| `NoOfLettersInURL` | 21.0 | 14.0..23.0 | 22.0 | -1.0 |
| `LetterRatioInURL` | 0.75 | 0.666667..0.766667 | 0.806452 | -0.056452 |
| `NoOfDegitsInURL` | 0.0 | 0.0..0.0 | 0.0 | 0.0 |
| `DegitRatioInURL` | 0.0 | 0.0..0.0 | 0.0 | 0.0 |
| `NoOfEqualsInURL` | 0.0 | 0.0..0.0 | 0.0 | 0.0 |
| `NoOfQMarkInURL` | 0.0 | 0.0..0.0 | 0.0 | 0.0 |
| `NoOfAmpersandInURL` | 0.0 | 0.0..0.0 | 0.0 | 0.0 |
| `NoOfOtherSpecialCharsInURL` | 4.0 | 4.0..4.0 | 3.0 | 1.0 |
| `SpacialCharRatioInURL` | 0.142857 | 0.133333..0.190476 | 0.115385 | 0.027472 |
| `HasObfuscation` | 0.0 | 0.0..0.0 | 0.0 | 0.0 |
| `NoOfObfuscatedChar` | 0.0 | 0.0..0.0 | 0.0 | 0.0 |
| `ObfuscationRatio` | 0.0 | 0.0..0.0 | 0.0 | 0.0 |
| `TLDLegitimateProb` | 0.75 | 0.75..0.75 | 0.775718 | -0.025718 |

## Sensitivitas skor URL legitimate

Jumlah URL legitimate: **55**; skor P(phishing), makin besar makin condong phishing.
`trailing_slash` menambah `/` bila belum ada dan menghapusnya bila sudah ada; `www_prefix` hanya menambah bila belum berawalan `www.`; `scheme_flip` menukar `http` dan `https`.

| Varian | URL berubah | Mean | Median | Delta mean | Delta median | Naik | Turun |
|---|---|---|---|---|---|---|---|
| original | 0 | 0.8758 | 1.0 | — | — | — | — |
| trailing_slash | 31 | 0.8757 | 1.0 | -0.0001 | 0.0000 | 7 | 1 |
| www_prefix | 23 | 0.8741 | 0.9999 | -0.0018 | 0.0000 | 6 | 4 |
| uppercase_host | 55 | 0.8758 | 1.0 | 0.0000 | 0.0000 | 0 | 0 |
| scheme_flip | 55 | 1.0 | 1.0 | 0.1241 | 0.0000 | 32 | 0 |

## Keterbatasan

- Set kecil dan satu snapshot; sapuan ambang rawan overfit.
- Kontribusi fitur menjelaskan model, bukan sebab phishing di dunia nyata.
- Label legitimate masih kurasi manual dan belum diverifikasi per URL.
- Varian `no_path_query` dan `www_prefix` mengubah URL, sehingga bukan lagi URL asli.
- Baseline `URLLength`/`DomainLength` hanya satu fitur; selisih AUC bukan bukti kausalitas.
- Parity membandingkan definisi repo dengan kolom dataset yang proses pembuatannya tidak terdokumentasi; selisih bukan otomatis bug.
- Sampel parity hanya 5000 baris train; persentase dan korelasi bisa berubah pada sampel lain.
- Referensi homepage latih adalah seluruh URL root legitimate, bukan kurasi 'homepage'.
- Huruf besar host tidak mengubah host secara standar URL, tetapi model menerima string mentah.
- Varian sensitivitas mengubah URL asli, jadi skornya bukan skor URL sebenarnya.
- Jejak homepage adalah contoh kecil, bukan sampel representatif seluruh legitimate.
- Dokumen ini sengaja tidak memuat URL feed; daftar error lokal ada di `data/realworld/errors.csv`.

## Cara menjalankan

```powershell
uv run python scripts/build_realworld_set.py
uv run python scripts/eval_realworld.py
uv run python scripts/diagnose_realworld.py
```
