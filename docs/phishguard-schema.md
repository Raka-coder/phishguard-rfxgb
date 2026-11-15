# PhishGuard — Dokumen Skema Data & Kontrak

> **Dokumen 3 dari 4.** Pendamping: `phishguard-prd.md`, `phishguard-architecture.md`, `phishguard-implementation.md`.
> Sumber kebenaran nama kolom: **wajib diverifikasi** lewat `uv run python scripts/inspect_data.py` sebelum menulis kode training (jangan percaya dari ingatan).

---

## 1. Skema Dataset PhiUSIIL

- Sumber: Kaggle `ndarvind/phiusiil-phishing-url-dataset` (ZIP → 1 file CSV `PhiUSIIL.csv`).
- Ukuran: **235.795 baris × 55 kolom (54 fitur + 1 label)**.
- Lisensi CC BY-NC-SA 4.0 — penggunaan non-komersial dengan atribusi (tugas kuliah).
- Kertas referensi: Prasad & Chandra (2023), doi:10.1016/j.cose.2023.103545.

### 1.1 Konstanta label — PERHATIAN (Risiko R1)

```python
# src/config.py
LABEL_LEGIT = 1    # label 1 = LEGITIMATE (134.850 baris)  <-- arah "terbalik" dari intuisi!
LABEL_PHISH = 0    # label 0 = PHISHING   (100.945 baris)
```

Distribusi yang diharapkan (verifikasi via inspect_data.py):

| label | arti | jumlah |
|---|---|---|
| 1 | legitimate | 134.850 |
| 0 | phishing | 100.945 |

Implikasi: **P(phishing) = predict_proba[:, 0]**, bukan `[:, 1]`. Wajib ada assertion di `tests/test_predict.py`.

### 1.2 Grup kolom

> Diverifikasi ulang terhadap CSV di `data/` pada 2026-11-15. Daftar kolom yang benar ada di
> `src/config.py` (`FULL_FEATURES`, `URL_FEATURES`); tabel di bawah hanya ringkasan grup.

| Grup | Kolom | Perlakuan |
|---|---|---|
| **Identitas (DROP)** | `URL`, `Domain`, `TLD`, `Title`, `label` | Bukan fitur. `URL` hanya dipakai sebagai kunci saat menelusuri contoh FP/FN dan sebagai input `extract_features()`. `TLD`/`Title` berupa teks sehingga tidak masuk proyeksi numerik. |
| **Numerik (Model A, 50 kolom)** | `URLLength`, `DomainLength`, `IsDomainIP`, `URLSimilarityIndex`, `CharContinuationRate`, `TLDLegitimateProb`, `URLCharProb`, `TLDLength`, `NoOfSubDomain`, `HasObfuscation`, `NoOfObfuscatedChar`, `ObfuscationRatio`, `NoOfLettersInURL`, `LetterRatioInURL`, `NoOfDegitsInURL`, `DegitRatioInURL`, `NoOfEqualsInURL`, `NoOfQMarkInURL`, `NoOfAmpersandInURL`, `NoOfOtherSpecialCharsInURL`, `SpacialCharRatioInURL`, `IsHTTPS`, `LineOfCode`, `LargestLineLength`, `HasTitle`, `DomainTitleMatchScore`, `URLTitleMatchScore`, `HasFavicon`, `Robots`, `IsResponsive`, `NoOfURLRedirect`, `NoOfSelfRedirect`, `HasDescription`, `NoOfPopup`, `NoOfiFrame`, `HasExternalFormSubmit`, `HasSocialNet`, `HasSubmitButton`, `HasHiddenFields`, `HasPasswordField`, `Bank`, `Pay`, `Crypto`, `HasCopyrightInfo`, `NoOfImage`, `NoOfCSS`, `NoOfJS`, `NoOfSelfRef`, `NoOfEmptyRef`, `NoOfExternalRef` | Semua fitur dataset, dipakai Model A (evaluasi/laporan). |
| **Leksikal-URL (Model B, 19 kolom)** | lihat `src/config.py:URL_FEATURES` | **Dihitung ulang dari string URL** oleh `extract_features()`, tidak disalin dari kolom dataset (lihat §2). |
| **Konten halaman (dilarang di Model B)** | `LineOfCode`, `NoOfImage`, `HasTitle`, `DomainTitleMatchScore`, `Bank`, `Pay`, `Crypto`, `HasFavicon`, `Robots`, `IsResponsive`, redirect/popup/iFrame/hidden-field, … | Butuh fetch halaman → mustahil saat inference (R2). |

> Catatan ejaan dataset: `Degit` (bukan `Digit`), `Spacial` (bukan `Special`), sufiks `InURL` pada
> `NoOfEqualsInURL`, `NoOfQMarkInURL`, `NoOfAmpersandInURL`, `NoOfOtherSpecialCharsInURL`.
> Kolom yang **tidak ada** di dataset (sempat tercantum di draf dokumen ini): `NoOfDots`, `NoOfHyphens`,
> `NoOfAt`, `NoOfSymbols`, `DomainRegisterLength`, `IsUnresolvableHost`.

---

## 2. Skema Fitur Turunan — `extract_features(url) -> dict`

Fungsi murni di `src/feature_utils.py`. Input string URL apa pun dari pengguna; output dict 19 fitur
leksikal dengan nama & urutan sama persis dengan `src/config.py:URL_FEATURES`, tanpa `None`/NaN.

**Keputusan penting:** Model B dilatih dari hasil `extract_features()` atas kolom `URL`, bukan dari kolom
fitur dataset. Alasannya, beberapa kolom dataset (mis. `NoOfLettersInURL`, `CharContinuationRate`,
`NoOfOtherSpecialCharsInURL`) tidak dapat direproduksi dari string URL — diuji pada 2.000 baris, tidak ada
definisi kandidat yang cocok. Menyalin kolom dataset untuk training lalu menghitung versi berbeda saat
inference akan menimbulkan train/serve skew.

| Fitur | Definisi hitung dari string |
|---|---|
| `URLLength` | `len(url)` |
| `DomainLength` | `len(host)` (tanpa scheme, path, query, port) |
| `TLDLength` | `len(label terakhir host)` |
| `NoOfSubDomain` | `jumlah label host - 2` (minimum 0; `www` tetap dihitung sebagai subdomain, sama seperti dataset) |
| `IsDomainIP` | `1` bila host adalah IPv4/IPv6 |
| `IsHTTPS` | `1` bila string diawali `https` |
| `NoOfLettersInURL` / `LetterRatioInURL` | jumlah `str.isalpha()` / dibagi panjang URL |
| `NoOfDegitsInURL` / `DegitRatioInURL` | jumlah digit / dibagi panjang URL |
| `NoOfEqualsInURL`, `NoOfQMarkInURL`, `NoOfAmpersandInURL` | `url.count('=')`, `count('?')`, `count('&')` |
| `NoOfOtherSpecialCharsInURL` / `SpacialCharRatioInURL` | jumlah karakter di himpunan `,;:%~+&*[]()!$#'"?=/@_-` / dibagi panjang URL |
| `TLDLegitimateProb` | P(legit) untuk TLD URL, dari lookup yang dihitung **pada train split** (Laplace: `(legit+1)/(n+2)`), default = rasio global train; disimpan di `src/tld_probs.json` |
| `HasObfuscation` | `1` bila ada `%`, `@`, `\`, karakter non-ASCII, atau host berupa IP |
| `NoOfObfuscatedChar` / `ObfuscationRatio` | jumlah karakter obfuscation / dibagi panjang URL |

Aturan kontrak:
1. Deterministik & murni (tanpa jaringan, tanpa I/O); 42 µs/URL → ~10 detik untuk 235.795 URL.
2. Semua nilai numerik float — tanpa `None`/NaN, input kosong/rusak menghasilkan 0.
3. Urutan kolom output = urutan `URL_FEATURES`; `feature_utils.to_frame(urls, tld_probs, default)` menjamin itu.
4. Unit test di `tests/test_features.py` (nama/urutan kolom, IP host, input kosong, lookup TLD, `to_frame`).
5. **Tidak masuk Model B**: `URLSimilarityIndex`, `URLCharProb` (butuh statistik korpus), `IsUnresolvableHost`
   (butuh DNS/jaringan), `CharContinuationRate` (definisi dataset tidak dapat direproduksi dari string URL).

---

## 3. Skema Artefak Model

| Artefak | Isi | Dibuat oleh |
|---|---|---|
| `src/model.pkl` | Model B (URL-only) terbaik — `sklearn.Pipeline`: imputer(median) + estimator (LR/RF/XGBoost) | `src/train.py` |
| `src/model_full.pkl` | Model A (full fitur) terbaik | `src/train.py` |
| `src/tld_probs.json` | `{"default": float, "map": {tld: P(legit)}}` dihitung dari **train split** saja; dipakai `extract_features` untuk `TLDLegitimateProb` | `src/train.py` |
| `docs/metrics.json` | `{"model_b": {"lr","rf","xgb": {"cv_f1_phishing_mean","cv_f1_phishing_std","cv_folds","params","fit_seconds"}, "best", "n_features"}, "model_a": {...}, "split": {"seed":42,"test_size":0.2,"stratified":true,"n_train","n_test","cv_folds":5}, "selection", "label", "trained_at"}` | `src/train.py` |
| `docs/stats.json` | `{"model_b": {"features", "importances", "class_means": {"phishing": {...}, "legit": {...}}, "best"}, "model_a": {...}}` — dipakai T7 untuk top-k fitur | `src/train.py` |
| `docs/hasil_evaluasi.md` | Tabel metrik, confusion matrix, daftar ≥3 FP & ≥3 FN dengan URL, label benar, probabilitas | `src/evaluate.py` |

Kontrak evaluasi (T6):
- Split **tidak** dibuat ulang secara ad-hoc: `evaluate.py` memakai `config.make_split(df)` (fungsi yang sama
  dengan `train.py`), sehingga test set identik (188.636 train / 47.159 test) dan assertion ukurannya wajib.
- Metrik dihitung dengan `pos_label=0` (phishing). FP = aktual 1 diprediksi 0; FN = aktual 0 diprediksi 1;
  confusion matrix dilaporkan dengan label baris/kolom eksplisit 0=phishing, 1=legit.
- Contoh FP/FN: Model B, deduplikasi per URL, diurutkan berdasarkan keyakinan (FP: P tertinggi; FN: P terendah),
  maksimum 10 baris per tabel, total ditulis di ringkasan. Kolom "top-3 fitur menyimpang" memakai
  `docs/stats.json` (`class_means` kelas asli).
- `evaluate_url_list(urls: list[str]) -> list[dict]` disediakan untuk T11: hanya string URL, tanpa dataset.

Kontrak training (T5):
- Split stratified 80/20 seed 42. **Test set tidak disentuh saat training** — hanya T6 yang menyentuhnya.
- Pemilihan model: 5-fold `StratifiedKFold` (shuffle, seed 42) **pada train saja**, skor = F1 kelas phishing
  (`pos_label=0`), model terbaik per proyeksi di-refit pada seluruh train lalu disimpan.
- Imputer di-fit hanya pada train (ada di dalam Pipeline, sehingga ikut tersimpan).
- F1 phishing selalu `pos_label=LABEL_PHISH`; `P(phishing) = predict_proba[:, 0]`.
- Hyperparameter tercatat lengkap di `metrics.json` (`params`) agar hasil dapat direproduksi.

---

## 4. Skema API — FastAPI :8001

### POST /check
Request:
```json
{ "url": "https://contoh.com/login" }
```

Response 200:
```json
{
  "url": "https://contoh.com/login",
  "label": 0,
  "label_name": "PHISHING",
  "probability": 0.97,
  "inference_ms": 12.4,
  "top_features": [
    {"feature": "IsDomainIP", "value": 0, "impact": "menurunkan risiko"},
    {"feature": "URLLength",  "value": 57, "impact": "netral"}
  ]
}
```

Response 400 (input tidak valid):
```json
{ "detail": "URL tidak valid: scheme/host tidak ditemukan" }
```

Kontrak:
- `label`: 0 = PHISHING, 1 = LEGITIMATE (sama dengan dataset).
- `label_name`: "PHISHING" | "LEGITIMATE".
- `probability`: P(phishing) ∈ [0,1]; threshold 0.5.
- `top_features`: maksimal 5 item, terurut dampak terbesar.
- Input kosong, tanpa scheme, tanpa host → 400 (bukan 500).

### GET /health
```json
{ "status": "ok", "model_loaded": true }
```

---

## 5. Skema State Reflex (`app/app_state.py`)

| Var | Tipe | Mutable di |
|---|---|---|
| `url_input` | `str` | event handler on_change/on_blur |
| `result` | `dict` (str→str) | handler `handle_check` setelah HTTP ke :8001 |
| `error` | `str` | handler `handle_check` saat 400/timeout |
| `loading` | `bool` | awal & akhir `handle_check` |

Var turunan via `@rx.var`: `probability_pct`, `is_phishing`, `verdict_color`. Render bersyarat memakai `rx.cond(is_phishing, ...)`; daftar `top_features` dirender dengan `rx.foreach` (NF5).

---

## 6. Skema File Pendukung

| File | Format | Isi |
|---|---|---|
| `data/PhiUSIIL.csv` | CSV (dari ZIP Kaggle) | Dataset mentah — gitignored |
| `data/PhiUSIIL.parquet` | Parquet ZSTD | Format kerja — gitignored, dihasilkan `scripts/convert_parquet.py` |
| `tests/fixtures/urls.txt` | teks, 1 URL/baris + komentar `#` | Korpus uji: phishing PhishTank, legitim Tranco, edge cases (kosong, IP-host, super panjang) |
| `docs/hasil_evaluasi.md` | Markdown | Bahan laporan: metrik + FP/FN |
| `.gitignore` | — | `data/`, `*.zip`, `*.parquet`, `*.duckdb`, `.venv/`, `.web/`, `__pycache__/`, `.env`, `kaggle.json`, `.env.local`, `state.json` |
