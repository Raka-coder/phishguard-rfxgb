# Set uji dunia nyata (T18)

Dokumen ini menjelaskan cara `data/realworld/urls.csv` dibuat dan bagaimana
`scripts/eval_realworld.py` mengukurnya. Semua angka hasil pengukuran ada di
`docs/realworld.json` — tidak ada angka metrik yang ditulis manual di dokumen ini.

## Tujuan

Mengukur model dan lapisan reputasi pada URL yang **tidak berasal dari PhiUSIIL**:

- `model_only` — Model B langsung, melewati allowlist dan uncertainty band.
- `with_reputation` — `predict_url` apa adanya (allowlist + uncertainty band).

Positif = **phishing**. `SUSPICIOUS` dihitung **non-phishing** dan jumlahnya
dilaporkan terpisah agar tidak menutupi keraguan.

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

# 4. Evaluasi — tulis docs/realworld.json
uv run python scripts/eval_realworld.py
```

`build_realworld_set.py` **tidak membuka jaringan**. Ia hanya membaca file lokal.
Label mengikuti dataset PhiUSIIL: `0 = phishing`, `1 = legitimate`.

Kolom `data/realworld/urls.csv`: `url,label,source,collected_at`.

## Isi `docs/realworld.json`

- `generated_at` — waktu evaluasi (UTC).
- `dataset` — path CSV, jumlah total/dievaluasi/dilewati, jumlah per kelas,
  sebaran `source`, dan rentang `collected_at`.
- `definitions` — definisi positif dan perlakuan `SUSPICIOUS`.
- `thresholds` — ambang yang dibaca dari `src/config.py` (bukan angka baru).
- `variants.model_only` dan `variants.with_reputation` — `tp, fp, fn, tn,
  precision, recall, f1`; varian reputasi menambah `suspicious`.

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
- Model dan artefak (`src/model.pkl`, `src/tld_probs.json`) harus sudah ada
  (jalankan `uv run python src/train.py` bila belum).
