# Set uji dunia nyata (T18/T18b)

Dokumen ini menjelaskan cara `data/realworld/urls.csv` dibuat dan bagaimana
`scripts/eval_realworld.py` mengukurnya. Semua angka hasil pengukuran ada di
`docs/realworld.json` — tidak ada angka metrik yang ditulis manual di dokumen ini.

## Tujuan

Mengukur model dan lapisan reputasi pada URL yang **tidak berasal dari PhiUSIIL**:

- `model_only` — Model B langsung, melewati allowlist dan uncertainty band.
- `with_reputation` — `predict_url` apa adanya (allowlist + uncertainty band).
- Hasil **penuh** dan hasil **seimbang** (jumlah phishing = jumlah legitimate)
  dilaporkan berdampingan.
- Metrik utama reputasi dihitung pada kelompok **`not_in_allowlist`**, karena
  kelompok allowlist memang diputuskan tanpa model.

Positif = **phishing**. `SUSPICIOUS` dihitung **non-phishing** dan jumlahnya
dilaporkan terpisah agar tidak menutupi keraguan.

## Metrik

Setiap blok metrik memuat `tp, fp, fn, tn` serta:

| Metrik | Arti |
|---|---|
| `precision`, `recall`, `f1` | Metrik standar dengan phishing sebagai positif. |
| `specificity` | True negative rate: legitimate yang benar disebut legitimate. |
| `balanced_accuracy` | Rata-rata `recall` dan `specificity`. |
| `mcc` | Matthews correlation coefficient; `null` bila penyebut nol. |
| `fp_rate` | False positive rate = FP / (FP + TN). |
| `fp_rate_ci95` | Interval kepercayaan Wilson 95% untuk `fp_rate`. |
| `recall_ci95` | Interval kepercayaan Wilson 95% untuk `recall`. |
| `predicted_phishing_pct` | Persentase URL yang diprediksi phishing oleh jalur tersebut. |

`with_reputation` dipilih per `decision_source` (`allowlist`, `model`,
`uncertainty`) dan per status allowlist (`in_allowlist`, `not_in_allowlist`).
Nilai `primary` pada blok reputasi adalah metrik kelompok `not_in_allowlist`.

## Sumber data

| Kelas | Sumber | Keterangan |
|---|---|---|
| Phishing (label `0`) | Snapshot feed **OpenPhish** (`https://openphish.com/feed.txt`) | Diunduh manual sekali, disimpan sebagai teks di `data/realworld/openphish.txt`. |
| Legitimate (label `1`) | **Kurasi manual** pemilik proyek | `data/realworld/legit.csv` (`url,source`), menekankan URL berpath: repo, video, dokumentasi, berita, bank. |

Catatan lisensi OpenPhish: Terms of Use mengizinkan pemakaian untuk riset
akademik/personal, tetapi melarang mendistribusikan ulang data mentah ke pihak
ketiga. Karena itu:

- `data/realworld/` **tidak di-commit** (sudah tercakup `data/` di `.gitignore`).
- `docs/realworld.json` hanya memuat **agregat dan metadata**, bukan daftar URL feed.
- Setiap orang yang ingin mereproduksi harus mengunduh feed sendiri dan menyetujui
  Terms of Use OpenPhish.

Daftar URL legitimate adalah draf kurasi awal dan perlu ditinjau pemilik proyek
sebelum dipakai untuk klaim di laporan.

## Cara membuat

```powershell
# 1. Unduh snapshot feed sekali (satu-satunya langkah berjaringan; bukan bagian skrip)
New-Item -ItemType Directory -Force -Path data\realworld | Out-Null
Invoke-WebRequest https://openphish.com/feed.txt -OutFile data\realworld\openphish.txt

# 2. Siapkan data\realworld\legit.csv dengan header: url,source
#    (satu URL legitimate per baris)

# 3. Bangun set uji — validasi http(s), buang duplikat, tulis data\realworld\urls.csv
uv run python scripts/build_realworld_set.py

# 4. Evaluasi — tulis docs\realworld.json (agregat) dan data\realworld\errors.csv (lokal)
uv run python scripts/eval_realworld.py
```

`build_realworld_set.py` **tidak membuka jaringan**. Ia hanya membaca file lokal.
Label mengikuti dataset PhiUSIIL: `0 = phishing`, `1 = legitimate`.

Kolom `data/realworld/urls.csv`: `url,label,source,collected_at`.

`data/realworld/errors.csv` berisi FP/FN dari kedua jalur pada set penuh, lengkap
dengan skor model, vonis, sumber keputusan, dan status allowlist. File ini
**lokal dan gitignored** karena memuat URL feed; jangan di-commit atau dibagikan.

## Isi `docs/realworld.json`

- `generated_at` — waktu evaluasi (UTC).
- `dataset` — path CSV, jumlah total/dievaluasi/dilewati, jumlah per kelas,
  sebaran `source`, dan rentang `collected_at`.
- `definitions` — definisi positif, perlakuan `SUSPICIOUS`, dan kelompok utama.
- `thresholds` — ambang yang dibaca dari `src/config.py` (bukan angka baru).
- `variants.full` — hasil seluruh URL:
  - `model_only` — metrik model saja.
  - `with_reputation` — `primary` (kelompok `not_in_allowlist`), `all`,
    `by_allowlist`, dan `by_decision_source`, plus `suspicious`.
- `variants.balanced` — hasil setelah sampel phishing diturunkan deterministik
  (seed tetap) agar jumlah kelas sama; memuat `seed`, `n_per_class`,
  `equal_classes`, `model_only`, dan `with_reputation` dengan struktur yang sama.
  Jika jumlah phishing sudah <= legitimate, seluruh phishing dipakai dan
  `equal_classes=false`.

Metrik dihitung dari prediksi nyata pada CSV; mengubah CSV lalu menjalankan ulang
skrip akan mengubah JSON.

## Keterbatasan (jujur)

- **Ukuran kecil dan satu snapshot.** Hasil berlaku untuk snapshot ini, bukan
  populasi phishing dunia nyata. Feed berubah setiap hari.
- **Label legitimate manual bisa salah.** URL bisa mati, berubah isi, atau
  dialihkan; URL tidak dibuka saat pelabelan (sesuai klausul etika).
- **Feed phishing condong ke URL yang jelas** (tanpa HTTPS, TLD aneh, host IP),
  sehingga recall bisa terlihat lebih tinggi daripada kenyataan.
- **Tidak ada daftar peringkat domain** (Tranco/Umbrella) sesuai PRD v2.
  Allowlist hanya berisi domain yang dikurasi di `src/trusted_domains.json`.
- **Tidak ada whois/umur domain, denylist feed, atau peniruan merek** pada versi
  ini; lapisan tersebut baru dikerjakan pada tugas berikutnya.
- **`SUSPICIOUS` bukan phishing** dalam metrik biner; jumlahnya tetap dilaporkan.
- **Mode seimbang bukan data baru.** Ia hanya menurunkan sampel phishing dari set
  yang sama; hasilnya bergantung pada seed tetap dan ukuran legit, bukan pada
  distribusi dunia nyata.
- **`errors.csv` memuat URL mentah** (termasuk feed) dan hanya untuk analisis
  lokal; jangan di-commit, dibagikan, atau ditempel ke laporan publik.
- Model dan artefak (`src/model.pkl`, `src/tld_probs.json`) harus sudah ada
  (jalankan `uv run python src/train.py` bila belum).
