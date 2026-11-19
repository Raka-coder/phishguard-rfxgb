# Indeks laporan PhishGuard (Bab 3–5)

Folder ini berisi draf bab laporan dalam format Markdown. Bab disusun untuk
diekspor ke Word/PDF. Angka dan tabel di dalamnya dirujuk ke berkas JSON
atau dokumen yang tercantum; tidak ada angka yang ditulis manual tanpa sumber.

## Daftar berkas

| Berkas | Isi |
|---|---|
| `bab3.md` | Arsitektur, pengolahan data, logika prediksi, antarmuka |
| `bab4.md` | Lingkungan, implementasi lapisan, etika dan batasan |
| `bab5.md` | Skenario, evaluasi test set, analisis FP, FN dan validasi dunia nyata, efektivitas berlapis |
| `data_status.md` | Status data T31–T32 (OK/MISSING) |
| `README.md` | Berkas ini (indeks) |

## Indeks gambar

| Gambar | Berkas | Dipakai di | Sumber |
|---|---|---|---|
| 3.1 | `../diagrams/alur_keputusan.mmd` | 3A.1 | `src/predict.py` |
| 3.2 | `../diagrams/predict_url.mmd` | 3A.2 | `src/predict.py` |
| 3.3 | `../figures/model_comparison.png` | 3A.3 | `docs/metrics.json`, `docs/hasil_evaluasi.md` |
| 3.4 | `../figures/feature_importance.png` | 3C.5 | `docs/stats.json` |
| 3.5 | `../screenshots/01_cek_phishing.png` | 3D.2 | `results/data/api_examples/01_phishing_denylist.json` |
| 3.6 | `../screenshots/02_cek_legit.png` | 3D.2 | `results/data/api_examples/02_legit_allowlist.json` |
| 3.7 | `../screenshots/03_cek_suspicious.png` | 3D.2 | `results/data/api_examples/03_suspicious_unknown.json` |
| 4.1 | `../diagrams/sync_feeds.mmd` | 4B.2 | `scripts/sync_feeds.py` |
| 4.2 | `../figures/feed_decay.png` | 4B.2 | `docs/denylist.json` |
| 4.3 | (tidak dipakai) | | |
| 4.4 | `../screenshots/04_evaluasi.png` | 4B.7 | `docs/metrics.json`, `docs/hasil_evaluasi.md` |
| 5.1 | `../figures/confusion_matrix.png` | 5B | `docs/hasil_evaluasi.md` |
| 5.2 | `../figures/path_ablation.png` | 5C | `docs/realworld.json` |
| 5.3 | `../figures/fn_categories.png` | 5D.1 | `results/data/fn_categories.json` |
| 5.4 | `../figures/legit_barat_lokal.png` | 5D.2 | `results/data/legit_barat_lokal_results.json` |
| 5.5 | `../figures/auc_benchmarks.png` | 5D.3 | `docs/model_c.json`, `docs/realworld.json` |
| 5.6 | `../figures/risk_band.png` | 5D.3 | `results/data/band_distribution.json` |
| 5.7 | `../figures/decision_composition.png` | 5E.1 | `docs/layer_tests.json` |

## Indeks tabel

| Tabel | Bab | Sumber |
|---|---|---|
| 3.1 Dua model by design | 3A.3 | `docs/metrics.json`, `docs/stats.json` |
| 3.2 Lapisan 0–4 | 3C.2 | `src/predict.py`, `src/config.py` |
| 19 fitur Model B | 3B.2 | `src/config.py` |
| 5B metrik test set | 5B | `docs/hasil_evaluasi.md` |
| 5B CV 5-fold | 5B | `docs/metrics.json` |
| 5C fitur FP dunia nyata | 5C | `docs/realworld.json` |
| 5D kategori FN | 5D.1 | `results/data/fn_categories.json` |
| 5E isolasi lapisan | 5E.1 | `docs/layer_tests.json` |
| 5E kumulatif lapisan | 5E.1 | `docs/layer_tests.json` |

## Indeks sumber JSON

| Berkas | Dipakai di |
|---|---|
| `docs/metrics.json` | 3A.3, 5B |
| `docs/stats.json` | 3A.3, 3C.5 |
| `docs/hasil_evaluasi.md` | 3A.3, 5B, 5C |
| `docs/realworld.json` | 5C, 5D.3 |
| `docs/model_c.json` | 5B, 5D.3 |
| `docs/layer_tests.json` | 5E |
| `docs/denylist.json` | 4B.2 |
| `results/data/band_distribution.json` | 5D.3 |
| `results/data/fn_categories.json` | 5D.1 |
| `results/data/legit_barat_lokal_results.json` | 5D.2 |
| `results/data/api_examples/*.json` | 3C.6, 3D.2 |

## Placeholder yang tersisa

- Lapisan peniruan merek (T20) belum diimplementasikan.
- Gambar 4.3 tidak dipakai (slot kosong agar penomoran gambar tetap
  sesuai checklist).
