# Denylist feed (T19)

## Sumber dan lisensi
Feed diunduh dari OpenPhish (`https://openphish.com/feed.txt`). **Feed tidak boleh
didistribusikan ulang** — simpan hanya di mesin lokal (`data/feeds/`, gitignored).
Lihat syarat pakai OpenPhish sebelum dipakai untuk keperluan lain.

## Cara sync (satu-satunya skrip yang boleh memakai jaringan)
```powershell
uv run python scripts/sync_feeds.py
```
Setiap run menyimpan snapshot bertanggal `data/feeds/openphish-YYYYMMDD-HHMMSS.txt`
dan tidak menimpa snapshot lama. Untuk evaluasi (capture rate), jalankan dua kali
dengan jeda agar ada snapshot A dan B.

## Cara kerja offline
- `src/denylist.py` memuat snapshot terbaru, menormalisasi URL (host+path,
  lowercase, query/fragment dibuang), dan mencocokkan secara offline.
- `predict_url` memeriksa lapisan denylist pertama: cocok ⇒ PHISHING
  (`decision_source="denylist"`, `risk_level="tinggi"`).
- Jika feed tidak ada atau basi (lewat `PHISHGUARD_FEED_MAX_AGE_HOURS`, default 24
  jam), lapisan dilewati dengan aman dan `trail` mencatat alasan; inference tetap
  jalan tanpa jaringan.

## Konfigurasi (opsional, default aman)
```ini
PHISHGUARD_FEED_DIR=data/feeds
PHISHGUARD_FEED_MAX_AGE_HOURS=24
```

## Evaluasi
```powershell
uv run python scripts/eval_denylist.py
```
Hasil ke `docs/denylist.json` (tanpa URL).

### Metrik T19b
- **Tumpang tindih**: antar pasangan snapshot terurut (A→B, A→C, …) — overlap proporsi
  URL, host, dan domain (www. di-stripping), plus jumlah URL baru di snapshot B.
- **Kurva umur entri**: untuk snapshot pertama, % entri yang masih muncul di snapshot
  berikutnya + selang waktu antar snapshot (jam).
- **False positive**: denylist pada `legit_dev`/`legit_final` (seharusnya 0).

### Evaluasi sistem penuh (aturan)
Evaluasi sistem penuh (`full_system`) **hanya** dijalankan dengan salah satu:
1. denylist **dimatikan**, atau
2. denylist memakai **snapshot yang bukan sumber set uji** (bukan `data/realworld/openphish.txt`).

Aturan ini ditulis di `docs/denylist.json` (`full_system.rule`) dan di sini.
Mod yang dijalankan: `denylist_disabled`, `denylist_external_snapshot`.

### Output JSON (`docs/denylist.json`)
Tanpa URL. Berisi: `generated_at`, `snapshots` (nama + jumlah URL), `overlap` (per pasangan),
`age_curve`, `false_positives`, `full_system`. Semua angka dari skrip.
