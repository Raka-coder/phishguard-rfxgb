# Kapsi gambar (T32)

Kapsi di bawah dipakai apa adanya di Bab 3-5. Bentuknya klaim satu kalimat, lalu catatan
n. Semua angka berasal dari JSON/artefak yang disebut di kolom sumber dan dihasilkan
ulang oleh `uv run python scripts/make_figures.py`; tidak ada angka yang ditulis manual
di skrip.

| Berkas | Kapsi | n | Sumber |
|---|---|---|---|
| `confusion_matrix.png` | Model B salah menilai 150 dari 47.159 URL uji, terdiri atas 122 false negative dan 28 false positive (0,32%). | 47.159 URL test set | `docs/hasil_evaluasi.md` |
| `model_comparison.png` | Selisih F1 test set Model A dan Model B hanya 0,0037, padahal Model A memakai 50 fitur termasuk fitur konten halaman yang tidak tersedia saat inferensi. | 47.159 URL test set; CV 5 lipatan pada 188.636 baris latih | `docs/metrics.json`, `docs/hasil_evaluasi.md` |
| `auc_benchmarks.png` | ROC AUC Model B turun dari 0,9988 pada PhiUSIIL (split berkelompok) ke 0,6687 pada data dunia nyata, lebih rendah daripada baseline satu fitur `DomainLength` (0,9522). | 330 URL tanpa allowlist (300 phishing, 30 legit) | `docs/model_c.json`, `docs/realworld.json` |
| `path_ablation.png` | Membuang path dan query menurunkan rerata skor URL legit dari 0,876 ke 0,201 dan menaikkan ROC AUC dari 0,669 ke 0,954. | 55 URL legit; 330 URL kelompok tanpa allowlist | `docs/realworld.json` |
| `feature_importance.png` | `IsHTTPS` menyumbang 0,749 importance Model B, diikuti `NoOfOtherSpecialCharsInURL` 0,191, sedangkan Model A didominasi `URLSimilarityIndex` 0,209. | 188.636 baris latih | `docs/stats.json` |
| `feed_decay.png` | Hanya 33% dari 300 entri snapshot awal yang masih ada di dua snapshot berikutnya setelah 9,61 jam. | 300 URL per snapshot, 3 snapshot | `docs/denylist.json` |
| `decision_composition.png` | Denylist sendirian hanya menandai 0,3% phishing, sedangkan Model B+C sendirian menandai 100% phishing dan 92,7% legit sebagai SUSPICIOUS; penambahan L0 (mock) menaikkan recall kumulatif ke 1,0. | 355 URL (300 phishing, 55 legit) | `docs/layer_tests.json` |
| `legit_barat_lokal.png` | 23 dari 25 URL legit yang dinilai model berakhir SUSPICIOUS, sedangkan dari 17 LEGITIMATE, 15 berasal dari allowlist dan 2 dari model. | 40 URL (20 Barat, 20 lokal) | `results/data/legit_barat_lokal_results.json` |
| `fn_categories.png` | 63 dari 122 false negative adalah URL pendek dan bersih, hanya 1 shortener dan 7 kandidat typosquatting. | 122 FN test set | `results/data/fn_categories.json` |
| `risk_band.png` | Zona 0,40-0,65 hampir kosong di data dunia nyata (0 dari 355 pada Model B, 10 dari 355 pada Model C), tetapi menampung 5 dari 40 URL set legit pada Model C. | 355 URL dunia nyata; 40 URL set legit | `results/data/band_distribution.json` |

Catatan pemakaian:

- `confusion_matrix.png` membaca blok `TP=..., FN=..., FP=..., TN=...` pertama di
  `docs/hasil_evaluasi.md` karena `docs/metrics.json` tidak menyimpan confusion matrix.
  Bila format markdown itu berubah, skrip berhenti dengan pesan jelas.
- `auc_benchmarks.png` memakai AUC PhiUSIIL dari `docs/model_c.json` (`variants.B_refit.
  test_grouped.roc_auc`), yang dihitung pada split berkelompok per host setelah dedup,
  bukan split acak 80/20. Perbedaan protokol itu harus disebut saat membandingkan.
- `risk_band.png` menampilkan persentase agar set legit (40 URL) dan set dunia nyata
  (355 URL) bisa dibandingkan; angka absolut ada di `results/data/band_distribution.json`
  dan di kapsi ini.
- Gambar yang memakai data dunia nyata selalu mencantumkan n pada judul atau kapsi.
