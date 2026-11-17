# PhishGuard v2 — PRD ringkas

Dokumen ini dibaca agent bersama `AGENTS.md` dan `docs/TASKS.md` sebelum mengerjakan tugas apa pun.

## 1. Tujuan

Mengubah PhishGuard dari "model leksikal yang skornya bagus di test set" menjadi "detektor yang benar-benar menangkap phishing dunia nyata, dan jujur soal batasnya".

Tiga hal yang harus tercapai:

1. **Deteksi nyata**: URL phishing segar dari feed publik ditangkap, termasuk peniruan merek (typosquatting).
2. **Kejujuran data**: UI dan laporan menampilkan performa sebenarnya, termasuk kelemahan, dibandingkan antara test set PhiUSIIL dan uji dunia nyata.
3. **Kemudahan dipahami**: setiap vonis menampilkan jejak keputusan (lapisan mana yang memutuskan dan kenapa).

## 2. Bukan tujuan (sengaja tidak dikerjakan)

- Tidak melatih ulang atau mengganti model (kecuali ada persetujuan eksplisit dari pemilik proyek).
- Tidak memakai daftar peringkat domain (Tranco, Umbrella, dll.).
- Tidak ada whois/umur domain, Google Safe Browsing, atau ekstensi browser (future work di laporan).
- Tidak membuka, me-resolve, atau memprobe URL yang diperiksa.

## 3. Alur keputusan target

Urutan evaluasi (berhenti di lapisan pertama yang memutuskan):

| # | Lapisan | Hasil | Sumber data |
|---|---------|-------|-------------|
| 1 | Denylist feed | PHISHING | file feed lokal di `data/feeds/` (dicocokkan offline) |
| 2 | Allowlist domain tepercaya | LEGITIMATE | `src/trusted_domains.json` (sudah ada) |
| 3 | Peniruan merek | PHISHING atau SUSPICIOUS | aturan string murni (jarak edit, homoglyph, punycode) |
| 4 | Aturan shortener | SUSPICIOUS | daftar shortener kecil |
| 5 | Model XGBoost (19 fitur, tidak diubah) | sesuai skor | `models/` |
| 6 | Uncertainty band 0,40–0,65 | SUSPICIOUS | sudah ada |

Setiap respons API mengembalikan `trail`: daftar langkah `{layer, result, detail}` yang dilewati sampai vonis. Field lama (`verdict`, `decision_source`, `reason`) tetap ada.

## 4. Prinsip kejujuran (wajib)

- Dilarang menulis angka metrik di kode, template, atau UI. Semua angka dibaca dari file JSON yang dihasilkan skrip evaluasi (`docs/metrics.json`, `docs/realworld.json`).
- Hasil yang jelek tetap ditampilkan. Tidak ada pemilahan data demi angka bagus.
- Setiap klaim di UI harus punya sumber file/skrip yang bisa ditunjuk.
- Set uji dunia nyata dibuat terpisah dari data latih, dan cara membuatnya didokumentasikan (sumber, tanggal pengambilan, jumlah, aturan pelabelan).

## 5. Konfigurasi

Satu-satunya variabel wajib adalah yang sudah ada. Tambahan opsional (semua punya default aman):

```ini
PHISHGUARD_API_URL=http://localhost:8001/check
PHISHGUARD_FEED_DIR=data/feeds
PHISHGUARD_FEED_MAX_AGE_HOURS=24
```

Kunci API (jika sebuah feed membutuhkannya) hanya boleh ada di `.env`, tidak pernah di `.env.example` atau di commit.

## 6. Keputusan yang belum diambil pemilik proyek

Agent **tidak boleh memutuskan** hal ini sendiri; tanyakan jika tugas menyentuhnya:

- Feed denylist yang dipakai (OpenPhish, PhishTank, URLhaus, atau kombinasi). Cek lisensi/syarat pakai sebelum dipilih.
- Sumber URL legitimate untuk set uji dunia nyata (tanpa Tranco).
- Perubahan klausul etika di `AGENTS.md` (ditunda; jangan edit bagian itu).

## 7. Definisi selesai untuk proyek

- `uv run pytest` hijau.
- Halaman evaluasi menampilkan test set dan uji dunia nyata berdampingan, dibaca dari JSON.
- Minimal satu fixture berisi URL phishing nyata dari feed dan URL legitimate modern (GitHub/Vercel/YouTube), terdokumentasi.
- Laporan bisa menjelaskan setiap lapisan, kelemahannya, dan hasil ukurnya.
