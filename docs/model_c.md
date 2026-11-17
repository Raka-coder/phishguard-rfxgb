# Model C — eksperimen host-only (T24)

Dihasilkan `scripts/train_model_c.py` + `scripts/eval_model_c.py` pada 2026-11-17T04:41:18+00:00 (dievaluasi 2026-11-17T04:42:32+00:00). Semua angka berasal dari kedua skrip; tidak ada angka manual.

## Ringkasan

| Varian | Fitur | CV F1 | Test F1 | Test MCC | Test ROC-AUC | T18 penuh F1 | T18 non-allowlist F1 | Specificity non-allowlist (95% CI) | Latih (dtk) |
|---|---|---|---|---|---|---|---|---|---|
| `B_refit` | 19 | 0.9961 | 0.9965 | 0.9939 | 0.9988 | 0.9231 | 0.9585 | 0.1333 (0.0531–0.2968) | 31.6 |
| `B_noHTTPS` | 18 | 0.9908 | 0.9912 | 0.9846 | 0.9986 | 0.9136 | 0.9487 | 0.0667 (0.0185–0.2132) | 30.9 |
| `C_host` | 10 | 0.8172 | 0.7915 | 0.6724 | 0.8817 | 0.9532 | 0.9612 | 0.7333 (0.5555–0.8582) | 25.3 |

Varian yang direkomendasikan: **`B_refit`** — F1 phishing rata-rata CV train berkelompok (tie-break MCC); test berkelompok dan set T18 tidak dipakai memilih.

## Data dan split

- Sumber: `PhiUSIIL.parquet`; 235795 baris awal, 425 baris duplikat URL dibuang, 235370 baris dipakai (134850 legit, 100520 phishing; 220077 host unik).
- Split: 187856 train / 47514 test (20.19% baris); 176061 / 44016 host; host yang muncul di kedua sisi: 0.
- Label train: 107828 legit, 80028 phishing. Label test: 27022 legit, 20492 phishing.
- CV: StratifiedGroupKFold per host di train (5 fold), seed 42.

## TLD probability

| Tabel | Kunci | Kunci berfragmen path | Default | Cakupan TLD baris test |
|---|---|---|---|---|
| Baru (host, OOF) | 642 | 0 | 0.573992 | 99.64% |
| Lama (URL penuh) | 12597 | 10683 | 0.571894 | 99.59% |

Rumus baru: `(jumlah legit per TLD + 1) / (jumlah total per TLD + 2)`; default `(jumlah legit train + 1) / (jumlah baris train + 2)`. Baris train memakai nilai out-of-fold dari 5 fold berkelompok; baris test memakai tabel dari seluruh train.
Tabel lama: Dibuat src/train.py:95 dengan rsplit pada URL penuh, sehingga sebagian besar kunci mengandung fragmen path dan tidak pernah cocok saat inference (TLD dari host).

## Fitur

| Varian | Sumber fitur | Jumlah | Daftar |
|---|---|---|---|
| `B_refit` | url | 19 | `URLLength`, `DomainLength`, `TLDLength`, `NoOfSubDomain`, `IsDomainIP`, `IsHTTPS`, `NoOfLettersInURL`, `LetterRatioInURL`, `NoOfDegitsInURL`, `DegitRatioInURL`, `NoOfEqualsInURL`, `NoOfQMarkInURL`, `NoOfAmpersandInURL`, `NoOfOtherSpecialCharsInURL`, `SpacialCharRatioInURL`, `HasObfuscation`, `NoOfObfuscatedChar`, `ObfuscationRatio`, `TLDLegitimateProb` |
| `B_noHTTPS` | url | 18 | `URLLength`, `DomainLength`, `TLDLength`, `NoOfSubDomain`, `IsDomainIP`, `NoOfLettersInURL`, `LetterRatioInURL`, `NoOfDegitsInURL`, `DegitRatioInURL`, `NoOfEqualsInURL`, `NoOfQMarkInURL`, `NoOfAmpersandInURL`, `NoOfOtherSpecialCharsInURL`, `SpacialCharRatioInURL`, `HasObfuscation`, `NoOfObfuscatedChar`, `ObfuscationRatio`, `TLDLegitimateProb` |
| `C_host` | host | 10 | `HostLength`, `HostLetterCount`, `HostDigitCount`, `HostSpecialCount`, `HostLetterRatio`, `HostDigitRatio`, `NoOfSubDomain`, `TLDLength`, `IsDomainIP`, `TLDLegitimateProb` |

## CV train berkelompok

| Varian | F1 phishing | MCC | ROC-AUC |
|---|---|---|---|
| `B_refit` | 0.9961 | 0.9931 | 0.9987 |
| `B_noHTTPS` | 0.9908 | 0.984 | 0.9986 |
| `C_host` | 0.8172 | 0.7252 | 0.9079 |

## Test berkelompok (host tidak tumpang tindih dengan train)

| Varian | Precision | Recall | F1 | MCC | ROC-AUC | TP | FP | FN | TN |
|---|---|---|---|---|---|---|---|---|---|
| `B_refit` | 0.9988 | 0.9942 | 0.9965 | 0.9939 | 0.9988 | 20374 | 24 | 118 | 26998 |
| `B_noHTTPS` | 0.9951 | 0.9874 | 0.9912 | 0.9846 | 0.9986 | 20233 | 99 | 259 | 26923 |
| `C_host` | 0.8892 | 0.7132 | 0.7915 | 0.6724 | 0.8817 | 14615 | 1822 | 5877 | 25200 |

## T18 penuh

355 URL (55 legit, 300 phishing). Skor model mentah, tanpa lapisan reputasi, memakai tabel TLD host baru.

| Varian | Precision | Recall | F1 | MCC | ROC-AUC | Specificity (95% CI) |
|---|---|---|---|---|---|---|
| `B_refit` | 0.8571 | 1.0 | 0.9231 | 0.2791 | 0.5903 | 0.0909 (0.0395–0.1958) |
| `B_noHTTPS` | 0.8506 | 0.9867 | 0.9136 | 0.1073 | 0.5619 | 0.0545 (0.0187–0.1485) |
| `C_host` | 0.9564 | 0.95 | 0.9532 | 0.7034 | 0.9253 | 0.7636 (0.6365–0.8563) |

## T18 tanpa allowlist

330 URL (30 legit, 300 phishing). Skor model mentah, tanpa lapisan reputasi, memakai tabel TLD host baru.

| Varian | Precision | Recall | F1 | MCC | ROC-AUC | Specificity (95% CI) |
|---|---|---|---|---|---|---|
| `B_refit` | 0.9202 | 1.0 | 0.9585 | 0.3503 | 0.6742 | 0.1333 (0.0531–0.2968) |
| `B_noHTTPS` | 0.9136 | 0.9867 | 0.9487 | 0.1148 | 0.6439 | 0.0667 (0.0185–0.2132) |
| `C_host` | 0.9727 | 0.95 | 0.9612 | 0.6226 | 0.9173 | 0.7333 (0.5555–0.8582) |

## Catatan pemilihan vs hasil akhir

Aturan tugas: varian dipilih hanya dari CV train, sehingga rekomendasi tetap `B_refit`. Pada T18 non-allowlist urutan F1 adalah `C_host`, `B_refit`, `B_noHTTPS`; angka ini dilaporkan sebagai hasil akhir dan tidak dipakai memilih ulang.

## Sensitivitas URL legitimate

55 URL legit T18; delta skor P(phishing) terhadap URL asli.

| Varian | Perubahan | URL berubah | Mean delta | Median delta | Maks | Naik | Turun |
|---|---|---|---|---|---|---|---|
| `B_refit` | `no_path_query` | 55 | -0.6769 | -0.919 | 0.9995 | 0 | 55 |
| `B_refit` | `scheme_flip` | 55 | 0.1221 | 0.0 | 0.9738 | 32 | 0 |
| `B_refit` | `www_prefix` | 23 | -0.0076 | 0.0 | 0.3075 | 5 | 5 |
| `B_refit` | `trailing_slash` | 31 | -0.0005 | 0.0 | 0.0405 | 7 | 1 |
| `B_noHTTPS` | `no_path_query` | 55 | -0.7267 | -0.9522 | 0.9988 | 0 | 55 |
| `B_noHTTPS` | `scheme_flip` | 55 | -0.2821 | 0.0 | 0.9086 | 2 | 33 |
| `B_noHTTPS` | `www_prefix` | 23 | -0.0007 | 0.0 | 0.0906 | 6 | 7 |
| `B_noHTTPS` | `trailing_slash` | 31 | -0.0003 | 0.0 | 0.0189 | 8 | 4 |
| `C_host` | `no_path_query` | 55 | 0.0 | 0.0 | 0.0 | 0 | 0 |
| `C_host` | `scheme_flip` | 55 | 0.0 | 0.0 | 0.0 | 0 | 0 |
| `C_host` | `www_prefix` | 23 | -0.0273 | 0.0 | 0.937 | 11 | 12 |
| `C_host` | `trailing_slash` | 31 | 0.0 | 0.0 | 0.0 | 0 | 0 |

`C_host` hanya memakai host, sehingga pemotongan path/query, tukar skema, dan trailing slash seharusnya menghasilkan delta 0; `www_prefix` tetap mengubah host.

## Waktu latih

| Varian | CV 5-fold (dtk) | Fit akhir (dtk) |
|---|---|---|
| `B_refit` | 25.5 | 6.1 |
| `B_noHTTPS` | 24.9 | 6.0 |
| `C_host` | 20.5 | 4.8 |

Total skrip latih: 241.0 detik. Hyperparameter sama dengan Model B (tanpa tuning).

## Batasan

- Model C hanya melihat host: path, query, skema, dan isi halaman tidak dipakai.
- Dibuang dari C_host: IsHTTPS/skema, URLLength, seluruh path/query, hitungan '=', '?', '&', fitur obfuscation URL, dan fitur konten; B_noHTTPS hanya membuang IsHTTPS.
- Fitur host dilebur menjadi satu vonis per host, sehingga phishing di host sah (mis. layanan user-content) dan legit di host buruk tidak dapat dibedakan.
- Split dikelompokkan per host penuh, bukan registrable domain; subdomain berbeda dari domain yang sama masih bisa muncul di kedua sisi.
- GroupShuffleSplit tidak stratified, jadi proporsi label train/test bisa bergeser.
- Tabel TLD baru memakai TLD host; tabel lama dihitung dari URL penuh sehingga banyak kuncinya tidak pernah cocok saat inference.
- Set legit T18 kecil, sehingga specificity dan interval kepercayaannya lebar.
- Skor T18 dihitung tanpa allowlist/band ragu, sehingga bukan vonis produksi.
- Varian sensitivitas mengubah URL asli; skornya bukan skor URL sebenarnya.
- Model C tidak dapat menangkap phishing yang hanya berbeda di path/query.

## Perintah

```powershell
uv run python scripts/train_model_c.py
uv run python scripts/eval_model_c.py
uv run pytest -q
```

Artefak model eksperimen ada di `models/experimental/` (gitignored). `src/model.pkl`, API, dan UI tidak berubah.
