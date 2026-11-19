# Daftar tugas PhishGuard v2

## Cara kerja agent (berlaku untuk semua tugas)

1. Baca `AGENTS.md`, `docs/PRD-v2.md`, dan file ini. Kerjakan **hanya satu tugas** per sesi.
2. Sebelum menulis kode, ringkas rencana dalam maksimal 5 baris dan tunggu konfirmasi pemilik proyek.
3. Hanya ubah file yang tercantum di "Boleh diubah". Butuh file lain? Tanya dulu.
4. Jangan menambah dependensi tanpa bertanya.
5. Jangan mengubah atau melatih ulang model.
6. Jangan menulis angka metrik secara manual di mana pun.
7. Satu tugas = satu commit dengan pesan jelas.
8. Di akhir, laporkan tiga hal: apa yang diubah, perintah tes yang benar-benar dijalankan beserta hasilnya, dan apa yang tidak bisa diverifikasi.

Pemilik proyek ingin memahami setiap perubahan: jelaskan keputusan desain secara singkat dan jujur, jangan hanya menyerahkan kode.

---

## T17 — Uji hipotesis bias `www.`

**Tujuan:** Mengecek apakah model menganggap URL tanpa `www.` lebih mungkin phishing (mis. `https://github.com` skor 0,9987 PHISHING).

**Boleh diubah:** `scripts/analyze_www_bias.py` (baru), `docs/analisis_www.md` (baru).

**Langkah:**
1. Hitung dari data latih (DuckDB/Parquet yang sudah ada di repo) proporsi URL legitimate dan phishing yang berawalan `www.`.
2. Ambil 30 domain legitimate populer (dari `src/trusted_domains.json`), skor tiap domain dalam dua bentuk: `https://domain` dan `https://www.domain`, memakai model yang ada.
3. Tulis tabel perbandingan dan kesimpulan (hipotesis terbukti, terbantah, atau tidak konklusif) di `docs/analisis_www.md`.

**Selesai jika:** skrip bisa dijalankan ulang, hasilnya tertulis di dokumen, dan kesimpulan didukung angka dari skrip. Tidak ada perubahan pada model atau `src/`.

---

## T18 — Set uji dunia nyata dan evaluasi

**Tujuan:** Mengukur performa model dan lapisan reputasi pada URL yang tidak berasal dari PhiUSIIL.

**Boleh diubah:** `scripts/build_realworld_set.py`, `scripts/eval_realworld.py`, `data/realworld/` (baru), `docs/realworld.json` (dihasilkan), `docs/realworld_README.md`, `tests/`.

**Langkah:**
1. `build_realworld_set.py` membuat `data/realworld/urls.csv` dengan kolom `url,label,source,collected_at`. Phishing diambil dari feed yang dipilih pemilik proyek; legitimate dari sumber yang disetujui pemilik proyek, dengan penekanan pada URL berpath (repo, video, dokumentasi). **Tanyakan sumbernya sebelum mengerjakan.**
2. `eval_realworld.py` menghitung precision, recall, F1, FP, FN untuk: (a) model saja, (b) model + lapisan reputasi yang ada. Hasil ditulis ke `docs/realworld.json` bersama metadata (jumlah, tanggal, sumber).
3. `realworld_README.md` menjelaskan cara data dibuat dan keterbatasannya (jujur, termasuk risiko label salah).

**Selesai jika:** `uv run pytest` hijau, kedua skrip jalan end-to-end, dan JSON memuat angka beserta metadata. Tidak ada angka yang ditulis manual.

---

## T19 — Denylist dari feed lokal

**Tujuan:** URL yang ada di feed phishing divonis PHISHING secara offline saat inference.

**Boleh diubah:** `scripts/sync_feeds.py`, `src/denylist.py`, `src/predict.py`, `src/config.py`, `.env.example`, `.gitignore`, `tests/`.

**Langkah:**
1. `sync_feeds.py` mengunduh feed yang dipilih pemilik proyek ke `data/feeds/` dan menulis stempel waktu. Ini satu-satunya skrip yang boleh memakai jaringan.
2. `src/denylist.py` memuat feed, menormalisasi URL, dan mencocokkan (URL persis dan domain+path). Tanpa jaringan.
3. Integrasikan sebagai lapisan 1 di `predict_url`, `decision_source="denylist"`. Jika feed tidak ada atau basi, lapisan dilewati dengan aman (bukan error).
4. Tambahkan variabel di `.env.example` sesuai PRD bagian 5. Pastikan `data/feeds/` masuk `.gitignore`.

**Catatan:** Jangan mengedit klausul etika di `AGENTS.md`. Jika diperlukan, laporkan ke pemilik proyek.

**Selesai jika:** tes mencakup URL yang ada/tidak ada di feed, feed hilang, dan feed basi; `predict_url` tidak membuka jaringan.

---

## T20 — Deteksi peniruan merek

**Tujuan:** Menangkap domain yang meniru merek terkenal tanpa jaringan.

**Boleh diubah:** `src/brand_impersonation.py` (baru), `src/predict.py`, `tests/`.

**Aturan yang diimplementasikan (murni string):**
- Normalisasi homoglyph (`1`→`l`, `0`→`o`, `rn`→`m`, dll.) lalu bandingkan dengan nama merek di allowlist.
- Jarak edit kecil (1–2) antara label domain dan nama merek, selama domain bukan milik merek itu sendiri.
- Nama merek muncul di subdomain atau path padahal registered domain bukan miliknya (mis. `paypal.com.evil.xyz`).
- Domain punycode (`xn--`) dilaporkan sebagai SUSPICIOUS.

**Selesai jika:** ada tes positif dan negatif, **termasuk domain sah yang mirip tetapi benar** (mis. `google.com`, `goo.gl` tidak boleh ditandai), dan `reason` menjelaskan aturan mana yang memicu. Laporkan jumlah FP baru yang muncul pada set T18 setelah tugas ini.

---

## T21 — Jejak keputusan (`trail`) di API dan UI

**Tujuan:** Menampilkan lapisan mana yang memutuskan dan kenapa.

**Boleh diubah:** `api/main.py`, `src/predict.py`, `app/` (komponen hasil), `tests/`.

**Langkah:**
1. `predict_url` mengumpulkan `trail`: list `{layer, result, detail}`.
2. API menambahkan field `trail` tanpa menghapus field lama.
3. UI menampilkan trail sebagai daftar langkah dengan ikon status, plus skor model dan zona ragu 0,40–0,65.

**Selesai jika:** respons lama tetap kompatibel, tes API mencakup `trail`, dan UI menampilkan kelima lapisan untuk satu URL contoh.

---

## T22 — Halaman evaluasi jujur

**Tujuan:** Halaman evaluasi yang bisa dipahami orang awam dan memuat data apa adanya.

**Boleh diubah:** `app/` (halaman evaluasi), `scripts/export_metrics.py` jika perlu, `tests/`.

**Isi halaman:**
- Kartu metrik (precision, recall, F1, jumlah salah) untuk test set dan untuk uji dunia nyata, berdampingan.
- Kalimat sederhana (mis. "Dari 100 URL phishing, model menangkap N").
- Grafik rincian hasil (benar/salah per kelas) dan grafik perbandingan test set vs dunia nyata, sebelum vs sesudah lapisan reputasi.
- Daftar contoh FP dan FN nyata dari set T18, lengkap dengan alasan vonis.
- Panel keterbatasan yang jujur (bias dataset, shortener, domain baru, ukuran set uji).

**Selesai jika:** semua angka berasal dari `docs/metrics.json` dan `docs/realworld.json`; mengubah JSON mengubah halaman; tidak ada angka hardcoded (cek dengan pencarian di kode).

---

## T23 — Fixture dan bahan laporan

**Tujuan:** Bukti nyata untuk laporan dan video.

**Boleh diubah:** `tests/fixtures/urls.txt`, `docs/`, `scripts/test_live_urls.py` jika perlu.

**Langkah:**
1. Ganti entri placeholder dengan URL phishing nyata dari feed (disimpan sebagai teks, tidak dibuka) dan URL legitimate modern (GitHub/Vercel/YouTube).
2. Tulis draf `docs/bahan_laporan.md`: setiap lapisan, kelemahannya, hasil ukur, serta contoh FP/FN dan penjelasannya.

**Selesai jika:** fixture tidak lagi berisi placeholder dan setiap klaim di draf menunjuk ke file/angka sumbernya.

---

## T30 — Pengujian berlapis L0–L4 (selesai)

**Status:** selesai. Semua angka ada di `docs/layer_tests.json`, dihasilkan oleh `scripts/test_layers.py` — jangan menyalin angka ke dokumen lain.

**Yang diuji:** L0 Google Safe Browsing (opt-in `PHISHGUARD_USE_GOOGLE`, HTTP di-mock), L1 denylist feed lokal, L2 allowlist, L3 Model B+C dengan zona band 0,40/0,65, L4 shortener. Tidak ada perubahan logika keputusan, skema verdict, atau `risk_level`.

**Berkas:**
- `tests/test_layers.py` — celah per lapisan: trail L0 saat tidak cocok/gagal/off, flag tanpa key, default mati tanpa env, feed basi lewat `predict_url`, varian `www.` dan lookalike allowlist, zona band deterministik dengan pipeline palsu, shortener tidak menurunkan risiko tinggi.
- `tests/test_layer_eval.py` — guard anti-melingkar dan paritas vonis skrip vs `predict_url` pada tingkatan L1..L4.
- `scripts/test_layers.py` — mode isolasi (tiap lapisan sendirian) dan kumulatif (L1 → L1+L2 → … → L0+L1..L4 mock), keluaran konsol + JSON.
- `docs/layer_tests.json` — artefak angka (dataset, guard, isolasi, kumulatif, catatan).

**Cara jalan:** `uv run python scripts/test_layers.py` (opsi `--max-age-hours`, default 168 jam karena snapshot feed historis). Guard membatalkan run bila lebih dari 5% URL set uji ada di snapshot feed yang dipakai (anti-melingkar).

**Celah yang dicatat, bukan ditutup:**
- T20 (deteksi peniruan merek) belum diimplementasikan, jadi item 11/13 `docs/command.md` tidak punya lapisan untuk diuji; `g0ithub.com`/`paypa1-secure.xyz` belum ditandai aturan khusus.
- Model B/C tidak pernah memvonis `PHISHING` (desain T26); `SUSPICIOUS` dihitung non-phishing dan dilaporkan terpisah.
- L0 hanya diuji dengan mock label-aware sebagai skenario batas atas, bukan akurasi Google Safe Browsing.
- Nama flag di `docs/command.md` (`PHISHGUARD_GSB_ENABLED`) tidak ada di kode; yang dipakai `PHISHGUARD_USE_GOOGLE`.
- Jumlah set dunia nyata mengikuti `data/realworld/urls.csv` (bukan 150/137 seperti `docs/command.md`).
