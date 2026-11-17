# Investigasi proses latih Model B (T18f)

Dokumen ini menjawab pertanyaan T18f dengan menunjuk file, fungsi, dan nomor baris.
Tidak ada kode, model, atau data yang diubah. Semua angka berasal dari perintah yang
dijalankan saat investigasi; perintah dan keterbatasannya dicatat di bagian akhir.
Dokumen ini tidak memuat URL.

## Ringkasan

| Pertanyaan | Jawaban singkat |
|---|---|
| Sumber 19 fitur Model B | Dihitung ulang dari string URL dengan `to_frame()`/`extract_features()`, **bukan** kolom fitur dataset. |
| Data latih | `data/PhiUSIIL.parquet`, 235.795 baris, kolom `URL`, 134.850 legit dan 100.945 phishing; semua URL terisi. |
| Split & CV | Split acak stratified 80/20 (`make_split`), CV 5-fold stratified acak; tidak ada pengelompokan per domain. |
| Risiko kebocoran | Ada. 143 URL persis dan 3.830 baris test (8,12%) berbagi host dengan train; hampir semuanya phishing. |
| Waktu latih Model B | Estimasi kasar 8 menit di mesin ini, didominasi CV Random Forest; angka tercatat ada di `docs/metrics.json`. |
| Ekstraktor cepat | Tidak ada jalur vektorisasi/multiprocessing. `to_frame()` memakai loop Python; 188.636 baris sekitar 8 detik. |

## 1. Asal 19 fitur Model B

Model B **tidak** memakai kolom fitur bawaan dataset. Di `src/train.py`:

- `src/train.py:139` — `X_a = df[FULL_FEATURES]...` adalah satu-satunya jalur yang mengambil
  kolom fitur dataset, dan itu untuk **Model A**.
- `src/train.py:140` — `X_b = to_frame(urls, tld_probs, tld_default)...` adalah fitur
  **Model B**, dihitung dari string URL.
- `src/train.py:134` — `urls = df["URL"].astype(str)` menjadi input ekstraktor.
- `src/train.py:45` — `to_frame` diimpor dari `src/feature_utils.py`.
- `src/feature_utils.py:86-95` — `to_frame()` membuat satu baris per URL dengan
  `[extract_features(u, ...) for u in urls]` (baris 94).
- `src/feature_utils.py:44-83` — `extract_features()` menghitung 19 fitur dari string;
  `n = len(url)` di baris 52 dan hitungan karakter di baris 55-58.
- `src/config.py:86-92` — daftar 19 kolom `URL_FEATURES` yang dihasilkan fungsi tersebut.

Satu fitur, `TLDLegitimateProb`, tidak dihitung murni dari URL: nilainya diambil dari
tabel `src/tld_probs.json` (`src/feature_utils.py:82`). Tabel itu dibuat di
`src/train.py:93-100` dari URL **train** dan label train, lalu ditulis di
`src/train.py:136`.

Catatan penting: `build_tld_probs()` memakai `urls.map(lambda u: u.rsplit(".", 1)[-1]...)`
(`src/train.py:95`), yaitu memotong URL penuh, bukan host. Akibatnya 10.683 dari 12.597
kunci tabel mengandung fragmen path, sementara saat inference `extract_features()` memakai
TLD dari host (`src/feature_utils.py:60-61` dan `:82`). Ini adalah temuan, bukan
perbaikan; dampak angkanya sudah dilaporkan di T18e.

## 2. Isi file data latih

`src/train.py:116` membaca `DATA_PARQUET`, yang didefinisikan di `src/config.py:15`
sebagai `data/PhiUSIIL.parquet`. File CSV di `data/PhiUSIIL.csv` ada, tetapi
`src/train.py` tidak membacanya.

Hasil pemeriksaan read-only:

| Item | Nilai |
|---|---|
| Bentuk data | 235.795 baris x 55 kolom |
| Kolom URL | `URL` (disebut juga di `src/config.py:50` sebagai kolom identitas) |
| Label legit (`1`) | 134.850 |
| Label phishing (`0`) | 100.945 |
| URL null/kosong | 0 / 0 |
| URL berawalan skema http/https | 235.795 dari 235.795 (100%) |
| URL unik | 235.370 |
| Baris duplikat (kelebihan salinan) | 425 |
| Host unik | 220.077 |
| Baris dengan path tidak kosong | 60.427 (25,63%) |

Jadi semua baris berisi string URL mentah yang lengkap dengan skema; tidak ada baris
yang hanya berisi domain atau nilai kosong. Label mengikuti kontrak dataset:
`1 = legitimate`, `0 = phishing` (`src/config.py:30-32`).

## 3. Split, hyperparameter, metrik, dan risiko kebocoran

### Split

- `src/config.py:40-48` — `make_split()` memakai `train_test_split` dengan
  `test_size=TEST_SIZE` (0,2), `stratify=df["label"]`, dan `random_state=SEED` (42).
  Indeks diurutkan sebelum dikembalikan.
- `src/train.py:128` — split yang sama dipanggil di training; ukuran yang diharapkan
  188.636 train / 47.159 test (`src/config.py:36-37`).
- `src/evaluate.py:162-171` — evaluasi memakai `make_split()` yang sama dan hanya
  menyentuh `test_idx`.
- CV: `src/train.py:142` — `StratifiedKFold(n_splits=5, shuffle=True, random_state=42)`.
  Fold dijalankan serial (`src/train.py:167`, `n_jobs=1`) dan hanya pada `X_train`,
  `y_train` (`src/train.py:163`).
- **Tidak ada** `GroupKFold`/`GroupShuffleSplit` atau argumen `groups` di repo
  (hasil pencarian; satu-satunya pemanggil `train_test_split` ada di
  `src/config.py:42`).

### Hyperparameter

Didefinisikan di `src/train.py:51-85`, dengan konstanta di `src/config.py:59-62`:

| Algoritme | Pipeline dan parameter |
|---|---|
| Logistic Regression | `SimpleImputer(strategy="median")` -> `StandardScaler()` -> `LogisticRegression(max_iter=2000, random_state=42)` |
| Random Forest | `SimpleImputer(strategy="median")` -> `RandomForestClassifier(n_estimators=300, n_jobs=-1, random_state=42)` |
| XGBoost | `SimpleImputer(strategy="median")` -> `XGBClassifier(n_estimators=400, learning_rate=0.1, max_depth=6, tree_method="hist", n_jobs=-1, random_state=42, eval_metric="logloss")` |

Imputer di-fit di dalam pipeline, sehingga statistik median hanya berasal dari fold
train masing-masing (`src/train.py:52-53`).

### Metrik validasi

- `src/train.py:48` — `PHISHING_F1 = make_scorer(f1_score, pos_label=LABEL_PHISH)`,
  jadi F1 selalu dengan phishing (`0`) sebagai positif.
- `src/train.py:166-175` — `cross_val_score` 5-fold di train untuk setiap algoritme.
- `src/train.py:177-181` — model dengan rata-rata F1 CV terbaik di-fit ulang pada
  seluruh train dan disimpan.
- `src/train.py:154` — dasar pemilihan: rata-rata F1 kelas phishing pada 5-fold CV
  di train.
- Test set tidak dipakai untuk memilih model; baru dinilai di `src/evaluate.py:162-174`.

### Risiko kebocoran antar split

Split hanya stratified menurut label, **tidak** mengelompokkan URL atau domain. Karena
dataset memuat duplikat dan banyak host berulang, ada kebocoran:

| Pemeriksaan | Hasil |
|---|---|
| Baris test yang host-nya juga ada di train | 3.830 (8,12% dari test) |
| ... di antaranya phishing / legit | 3.821 / 9 |
| Host unik test yang juga ada di train | 2.109 dari 45.253 |
| Baris test yang URL persisnya ada di train | 143 (semuanya phishing) |
| URL dengan label bertentangan | 0 |
| Baris train dalam grup URL duplikat | 532 baris (266 grup), semuanya phishing |
| Baris train yang host-nya berulang di train | 15.678 (8,31%); 15.653 phishing, 25 legit |

Implikasi: CV dan test set dapat terlihat lebih baik daripada performa pada URL yang
benar-benar baru, terutama untuk kelas phishing. Tidak ada indikasi label ganda untuk
URL yang sama, tetapi pengulangan URL/domain yang sama tetap membuat fold dan test
tidak independen. Model B dilatih dari string URL, jadi duplikat juga berarti salinan
fitur yang identik, bukan hanya domain yang mirip.

## 4. Estimasi waktu latih Model B

Dua sumber: log yang sudah ada dan benchmark kecil read-only. Benchmark tidak menyimpan
artefak dan tidak menimpa `src/model.pkl`.

| Pengukuran | Hasil |
|---|---|
| `to_frame()` 20.000 URL | 0,91 detik |
| `to_frame()` 188.636 URL train | 8,13 detik (sekitar 43 ms per 1.000 URL) |
| Fit XGBoost 20.000 baris (parameter training, `n_jobs=-1`) | 0,73 detik |
| `docs/metrics.json`: fit akhir Model B LR | 3,9 detik |
| `docs/metrics.json`: fit akhir Model B RF | 60,2 detik |
| `docs/metrics.json`: fit akhir Model B XGB | 15,5 detik |
| `docs/metrics.json`: F1 CV Model B LR/RF/XGB | 0,9870 / 0,9949 / 0,9962 |

Perkiraan kasar untuk satu putaran Model B di mesin ini, memakai angka log:

- 5-fold CV untuk 3 algoritme: sekitar `5 x (3,9 + 60,2 + 15,5)` = sekitar 398 detik.
- Fit akhir model terbaik: sekitar 15,5 detik.
- Ekstraksi fitur train: sekitar 8,1 detik.
- Total: sekitar 7-8 menit, didominasi CV Random Forest.

Angka ini perkiraan, bukan hasil menjalankan `src/train.py` penuh. Waktu nyata bisa
berbeda karena cache, beban mesin, dan biaya scoring. Script juga menjalankan Model A
dan Model B dalam satu loop (`src/train.py:158-161`), jadi total `train.py` lebih besar
dari perkiraan Model B saja.

Yang bisa diparalelkan:

- XGBoost sudah paralel internal (`n_jobs=-1`, `src/train.py:78`).
- Random Forest sudah paralel internal (`n_jobs=-1`, `src/train.py:65`).
- Fold CV **belum** paralel: `cross_val_score(..., n_jobs=1)` di `src/train.py:167`.
- Loop Model A/Model B berjalan serial (`src/train.py:158`).
- Ekstraksi fitur berjalan satu proses (`src/feature_utils.py:94`), padahal
  `extract_features()` murni string dan tidak melakukan I/O (`src/feature_utils.py:1`),
  sehingga secara teori mudah diparalelkan. Namun biayanya hanya sekitar 8 detik,
  jadi bukan bottleneck utama.

## 5. Jalur ekstraksi cepat di repo

**Tidak ada** jalur vektorisasi atau multiprocessing untuk ekstraktor:

- `src/feature_utils.py:94` — `to_frame()` memakai list comprehension Python per URL,
  bukan operasi string vektor pandas.
- `src/feature_utils.py:55-58` — hitungan huruf/digit/karakter spesial dilakukan per
  string di dalam `extract_features()`; tidak ada versi batch.
- Pencarian di `src/` dan `scripts/` hanya menemukan `joblib` untuk simpan/muat model
  (`src/train.py:14`, `src/evaluate.py:10`, `src/predict.py:11`) dan `n_jobs` untuk
  model (`src/train.py:65`, `:78`, `:167`). Tidak ada `multiprocessing`,
  `ProcessPoolExecutor`, `ThreadPoolExecutor`, `joblib.Parallel`, atau `swifter`.
- `src/train.py:95` memakai `pandas.Series.map` untuk ekstraksi TLD saat membangun tabel,
  tetapi itu bukan ekstraksi 19 fitur.

Jadi cara tercepat yang tersedia saat ini adalah loop Python yang sudah ada. Benchmark
menunjukkan biayanya 8,13 detik untuk 188.636 baris, sehingga optimasi ekstraksi tidak
akan mengubah waktu latih secara berarti dibandingkan CV Random Forest.

## Perintah yang dijalankan

Semua read-only; tidak ada model atau artefak yang ditulis.

1. Pemeriksaan data dan split (pandas): bentuk data, label, URL null/kosong, skema,
   URL/host unik, duplikasi, serta irisan URL/host train-test.
2. Pemeriksaan duplikasi internal train: baris dalam grup URL duplikat, baris dengan
   host berulang, dan labelnya.
3. Benchmark `to_frame()` pada 20.000 dan 188.636 URL, serta fit XGBoost pada 20.000
   baris in-memory (tanpa `dump`).
4. Membaca `docs/metrics.json` untuk `fit_seconds` dan F1 CV Model B.
5. Pencarian kode untuk `multiprocessing`, `Parallel`, `n_jobs`, `GroupKFold`,
   `StratifiedKFold`, dan `train_test_split`.
6. Membaca `src/train.py`, `src/config.py`, `src/feature_utils.py`, dan
   `src/evaluate.py` untuk verifikasi nomor baris.

## Yang tidak diverifikasi

- `uv run python src/train.py` penuh **tidak dijalankan** karena akan menulis ulang
  artefak model dan `docs/metrics.json`; angka waktunya diambil dari log yang ada.
- CV 5-fold tidak dijalankan ulang, jadi perkiraan total belum diukur langsung.
- Angka kebocoran dihitung pada level dataset/split, bukan pada fold CV yang sebenarnya;
  karena `StratifiedKFold` mengacak, duplikat bisa tersebar antar fold, tetapi
  jumlah pasti per fold tidak dihitung.
- Tidak diuji apakah `multiprocessing` benar-benar mempercepat ekstraksi di mesin ini.
- Semantik kolom dataset tidak diperiksa ulang di sini; perbandingan definisi fitur
  ada di `docs/diagnosis_realworld.md` (T18e).
