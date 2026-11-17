Saya membuka CSV-nya dan menghitung komposisinya. Datanya cukup untuk dilanjutkan, tetapi ada tiga masalah yang harus dibereskan dulu, dan satu pekerjaan manual yang hanya bisa Anda lakukan.

## 1. Temuan dari CSV

| Hal | Hasil | Artinya |
|---|---|---|
| URL / host / **domain terdaftar** | 200 / 143 / **61** | Keragaman sebenarnya 61, bukan 143. `detik.com` saja 15 URL. |
| Komposisi | 99 berakhiran `.id`, 21 `.org`, 74 `.com`; didominasi berita, kampus, pemerintah, dokumentasi | Mewakili "situs Indonesia yang lazim", bukan seluruh web. |
| Panjang host | rata-rata 17 karakter, maksimum 32 | Pendek, padahal `DomainLength` adalah fitur yang paling mendorong FP dan membuat baseline sederhana terlihat bagus. Set ini bisa memuji model yang kebetulan membaca panjang host. |
| Root / berpath | 45 / 155 | Bagus untuk menguji kelemahan model. |
| Kolom `keep` | semua kosong | Belum ada satu pun label yang Anda setujui. |

## 2. Tiga masalah yang harus dibenahi

**a. Pembagian dev/final per host akan bocor.** `ui.ac.id`, `unp.ac.id`, dan yang lain punya banyak subdomain. Kalau dev dan final dibagi per host, domain yang sama bisa muncul di kedua sisi, dan hasil akhir jadi terlalu optimis. Kelompokkan per **domain terdaftar** (public suffix, mis. `ui.ac.id`) dan batasi maksimum 5 URL per domain terdaftar, bukan per host.

**b. Ada kategori yang hilang**, dan justru itu tempat model lemah: marketplace dan e-commerce, bank (halaman publik), layanan SaaS, domain panjang atau bersubdomain berlapis, dan situs yang jauh lebih "biasa" daripada media besar. Tambahkan ±40–60 URL dari kategori itu lewat bookmark Anda sendiri (jalur 1), karena URL dari tautan sebuah portal berita punya bias "dirujuk situs tepercaya".

**c. Provenans dan etika crawl.** `source_site` hanya mengulang host URL itu sendiri, dan agent mengakui `robots.txt` serta jeda 2 detik tidak diperiksa ketat. Tulis jujur di laporan: "dikumpulkan dengan crawl terbatas, tidak diverifikasi terhadap robots.txt". Jangan crawl lagi untuk tambahan; pakai bookmark.

## 3. Yang perlu Anda tandai `keep=0` (dari yang terlihat di file)

- **`maps.app.goo.gl/...`**: shortener. Sistem sengaja memvonis shortener sebagai SUSPICIOUS, jadi bukan contoh "legit biasa".
- **5 URL `tiktok.com/@...`, 2 URL `bsky.app/profile/...`, dan `wa.me`**: profil dan konten buatan pengguna di platform besar. Ini tempat phisher suka bersembunyi, dan labelnya tidak bisa dijamin.
- **`ir-bri.com/acgs.html`**: domainnya mirip merek BRI tetapi bukan `bri.co.id`. Saya tidak bisa memastikan sah atau tidaknya. Cek dari situs resmi BRI. Kalau tidak bisa memastikan, beri `0`. Sebagian domain ini juga berpotensi jadi contoh uji peniruan merek.
- **`cnnchile.com` dan `cnnmexico.com` (http)**: kemungkinan sah, tapi pastikan dulu. Kalau ragu, `0`.
- Satu URL `.pdf` boleh dipertahankan atau dibuang, tidak berpengaruh besar.

Untuk sisanya, aturannya sederhana: **kalau Anda yakin situs itu sah, tulis `1`; kalau ada keraguan sekecil apa pun, `0`.** Anda tidak perlu membuka URL. Cukup baca domainnya. Perkiraan waktu 20–30 menit, dan ini pekerjaan yang tidak boleh diserahkan ke agent karena menentukan "kebenaran" evaluasi.

## 4. Tempel ke agent (T24b)
```
Baca AGENTS.md, docs/PRD-v2.md, docs/TASKS.md. Kerjakan HANYA T24b.
Ringkas rencana 5 baris dulu, tunggu konfirmasi. Tanpa jaringan.
Boleh diubah/dibuat: scripts/prepare_legit_user.py, scripts/split_legit.py,
tests/, docs/legit_user_README.md. Data tetap di data/realworld/ (gitignored).
1. Tambahkan kolom reg_domain (domain terdaftar memakai public suffix list,
   mis. tldextract tanpa jaringan/offline snapshot; jika dependensi baru
   dibutuhkan, tanyakan dulu).
2. Terapkan batas maksimum 5 URL per reg_domain pada legit_review.csv
   (jangan menghapus baris yang sudah saya beri keep=1; laporkan baris yang
   dibuang dan alasannya secara agregat).
3. Ubah split_legit.py: bagi baris keep=1 menjadi dev 70% / final 30%
   dikelompokkan per reg_domain (seed 42), bukan per host. Laporkan bahwa
   tidak ada reg_domain yang muncul di kedua file.
4. Cetak hanya agregat: jumlah URL dan reg_domain per file, rasio root vs
   berpath, jumlah di luar allowlist, rata-rata dan median panjang host
   per file. Jangan mencetak URL.
5. Tambahkan di docs/legit_user_README.md bagian "Keterbatasan": komposisi
   (berita/kampus/pemerintah/dokumentasi), crawl terbatas, robots.txt tidak
   diperiksa, host pendek.
Laporkan yang dijalankan dan yang tidak diverifikasi.
```

## 5. Urutan kerja Anda sekarang
1. Isi kolom `keep` di `legit_review.csv` (aturan di atas), ±30 menit.
2. Ekspor bookmark Chrome ke `data/realworld/raw/` dan jalankan `prepare_legit_user.py` untuk kategori yang hilang (marketplace, bank, SaaS, subdomain). Gabungkan hasilnya ke `legit_review.csv`, lalu beri `keep`.
3. Jalankan T24b di atas.
4. Jalankan T25c (perbaikan syarat lantai recall-terjaring), lalu jalankan ulang T25b.
5. Kirim ke saya **agregat saja** dari T24b: jumlah URL dan domain terdaftar per file (dev/final), rasio root vs berpath, jumlah di luar allowlist, dan rata-rata panjang host per file.

Kalau setelah dibersihkan jumlahnya tinggal sekitar 100–150 URL dari ±40–50 domain terdaftar, itu masih bisa dipakai. Laporkan angka sebenarnya dan interval kepercayaan yang lebar, dan jangan memaksakan ke 200. Yang tidak boleh adalah menyatakan hasil lebih pasti daripada yang didukung data.