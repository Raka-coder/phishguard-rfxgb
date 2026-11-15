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

| Grup | Contoh kolom | Perlakuan |
|---|---|---|
| **Identitas (DROP)** | `URL`, `Domain`, `Filename` | Dihapus dari semua proyeksi fitur; `URL` hanya dipakai sebagai kunci saat menelusuri contoh FP/FN |
| **Leksikal-URL (Model B)** | `URLLength`, `NoOfDots`, `NoOfHyphens`, `NoOfAmpersand`, `NoOfOtherSpecialChars`, `IsHTTPS`, `IsDomainIP`, `CharContinuationRate`, `TLDLegitimateProb`, `URLCharProb`, `NoOfSubDomain`, `HasObfuscation`, `ObfuscationRatio`, `NoOfSymbols`, `Robots`, `SpacialCharRatioInURL`, `DegitRatioInURL`, `NoOfDegitsInURL`, `NoOfEqual`, `NoOfQMark`, `NoOfAt`, `DomainLength`, `DomainRegisterLength`, `IsUnresolvableHost` *(nama final tetap divalidasi via DESCRIBE)* | Fitur yang **bisa dihitung dari string URL** → basis `extract_features()` dan proyeksi Model B |
| **Konten halaman (Model A saja)** | `LineOfCode`, `NoOfImage`, `NoOfCSS`, `NoOfJS`, `NoOfSelfRef`, `NoOfEmptyRef`, `NoOfExternalRef`, `HasTitle`, `DomainTitleMatchScope`, `HasDescription`, `HasSocialNet`, `HasSubmitButton`, `HasHiddenFields`, `HasPasswordField`, `HasCopyrightInfo`, `IsResponsive`, `NoOfPopup`, `NoOfiFrame`, `NoOfSelfRedirect`, `NoOfURLRedirect`, `HasFavicon`, `Bank`, `Pay`, `Crypto`, `Cryptocurrency` *(nama final tetap divalidasi)* | Hanya ada di dataset historis → **dilarang masuk Model B** (R2 leakage) |

> Catatan ejaan dataset: `Degit` (bukan `Digit`) — salin persis dari output DESCRIBE.

---

## 2. Skema Fitur Turunan — `extract_features(url) -> dict`

Fungsi murni di `src/feature_utils.py`. Input string URL apa pun dari pengguna; output dict fitur leksikal yang **nama & urutannya sama persis** dengan kolom proyeksi Model B di dataset (kolom yang tidak bisa dihitung live → tidak boleh ada di Model B).

| Fitur (contoh) | Definisi hitung dari string |
|---|---|
| `URLLength` | `len(url)` |
| `NoOfDots` | `url.count('.')` |
| `NoOfHyphens` | `url.count('-')` |
| `NoOfAt` | `url.count('@')` |
| `NoOfEqual` / `NoOfQMark` | `count('=')` / `count('?')` |
| `NoOfOtherSpecialChars` | hitung karakter khusus lain (`,;:%~+&*[]()!$#'")` |
| `DegitRatioInURL` | proporsi karakter digit `0-9` |
| `SpacialCharRatioInURL` | proporsi karakter khusus (ejaan dataset: "Spacial") |
| `IsHTTPS` | `1` bila scheme `https`, else `0` |
| `IsDomainIP` | `1` bila host adalah IPv4/IPv6 |
| `DomainLength` | panjang host |
| `NoOfSubDomain` | jumlah label host dikurangi 1 (di luar www/TLD) |
| `HasObfuscation` / `ObfuscationRatio` | ada/proporsi teknik obfuscation: `%XX`, `@`, IP host, homoglyph di luar ASCII, double-slash tak wajar |
| `NoOfSymbols` | jumlah simbol non-alnum |

Aturan kontrak:
1. Deterministik & murni (tanpa jaringan, tanpa I/O).
2. Semua nilai numerik (float/int) — tanpa `None` (default 0.0).
3. Urutan kolom output = urutan kolom training Model B (`src/config.py: URL_FEATURES`).
4. Ada unit test di `tests/test_predict.py` untuk URL tipikal (phishing & legitim).

---

## 3. Skema Artefak Model

| Artefak | Isi | Dibuat oleh |
|---|---|---|
| `src/model.pkl` | Model B (URL-only) terbaik — pipeline: imputer(optional) + estimator (RF/XGBoost) | `src/train.py` |
| `src/model_full.pkl` | Model A (full fitur) terbaik | `src/train.py` |
| `docs/metrics.json` | `{"model_b": {"rf": {...}, "xgb": {...}}, "model_a": {...}, "split": {"seed":42, "test_size":0.2, "stratified":true}, "trained_at": "..."}` | `src/train.py` |
| `docs/hasil_evaluasi.md` | Tabel metrik, confusion matrix, daftar ≥3 FP & ≥3 FN dengan URL, label benar, probabilitas | `src/evaluate.py` |

Model "terbaik" dipilih berdasar **F1 kelas phishing** pada validation/test set; keputusan disimpan di `metrics.json`.

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
