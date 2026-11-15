# Ringkasan Masalah/Isu PhishGuard

**Proyek:** PhishGuard — Deteksi Phishing Berbasis URL  
**Repository:** https://github.com/Raka-coder/phishguard-rfxgb  
**Status:** Model bekerja sesuai desain, tetapi memiliki keterbatasan fundamental.

## Inti Masalah

URL legitimate modern seperti Vercel, YouTube, dan GitHub terdeteksi sebagai phishing oleh model XGBoost. Ini bukan bug, melainkan keterbatasan deteksi leksikal murni karena model hanya membaca 19 fitur teks URL tanpa mengakses internet atau mengetahui reputasi/umur domain.

## Akar Penyebab

Model B XGBoost hanya menggunakan 19 fitur leksikal URL, seperti panjang URL, panjang domain, jumlah subdomain, jumlah karakter khusus, rasio karakter khusus, dan probabilitas TLD. Model tidak tahu bahwa `github.com` atau `youtube.com` adalah domain terpercaya. Model hanya melihat pola: URL panjang, banyak simbol, atau banyak subdomain dianggap mirip phishing karena pola tersebut dominan pada data latih PhiUSIIL.

Contoh kasus GitHub: URL `https://github.com/Raka-coder/phishguard-rfxgb` memiliki panjang 46 karakter dan 7 karakter khusus. Di mata model, pola ini mirip phishing sehingga menghasilkan false positive.

Contoh kasus Vercel: URL `https://my-project.vercel.app` memiliki satu subdomain dan nama yang terlihat acak. Model menganggap subdomain sebagai ciri spoofing sehingga menghasilkan false positive.

## Solusi yang Diusulkan

Gunakan pendekatan hybrid: online + offline.

**Lapisan 1 — Cek Online:** Lakukan Whois lookup, DNS, dan opsional threat intelligence API. Jika domain sudah berumur lebih dari 365 hari dan terpercaya, langsung vonis LEGITIMATE tanpa perlu model ML. Jika domain baru atau tidak dikenal, lanjut ke Lapisan 2.

**Lapisan 2 — Model XGBoost Offline:** Model tetap membaca 19 fitur leksikal dan menghasilkan prediksi PHISHING, LEGITIMATE, atau PERLU VERIFIKASI MANUAL. Tambahkan uncertainty band: probabilitas 0,40–0,65 tidak langsung divonis phishing, tetapi ditandai untuk verifikasi manual.

## Dampak ke Dataset dan Evaluasi

Dataset PhiUSIIL tetap relevan dan tidak perlu diganti. Model XGBoost tidak perlu dilatih ulang. Evaluasi tetap memakai test set lama dengan F1-score 0,9963, serta 28 false positive dan 122 false negative. Yang berubah hanya arsitektur sistem: menambahkan lapisan online di depan model ML untuk mencegah false positive pada URL dunia nyata.

## Dampak ke Laporan

Analisis false positive dan false negative menjadi lebih kuat karena dapat menjelaskan keterbatasan model leksikal dan mitigasinya melalui pendekatan hybrid. Narasi Bab Pembahasan dapat menjelaskan bahwa false positive terjadi karena URL legitimate modern menggunakan shared hosting, subdomain, atau parameter query panjang, lalu dimitigasi dengan Whois lookup dan uncertainty band.

## Rekomendasi Implementasi

1. Implementasikan Whois lookup di `src/predict.py`.
2. Tambahkan uncertainty band dengan `THRESHOLD_SUSPICIOUS = 0.40` dan `THRESHOLD_PHISHING = 0.65`.
3. Update response model di `api/main.py` dengan field `decision_source` dan `reason`.
4. Update UI Reflex untuk menampilkan sumber keputusan dan alasan.
5. Tulis narasi analisis FP/FN di Bab 3 laporan.
6. Rekam video demo dengan tiga anggota tampil.

## Kesimpulan

False positive pada PhishGuard bukan kegagalan model, melainkan keterbatasan fundamental deteksi leksikal murni. Solusi hybrid online + offline adalah pendekatan realistis yang mempertahankan performa model sekaligus meningkatkan robustness terhadap URL legitimate modern. Dataset PhiUSIIL tetap valid, model XGBoost tetap dipakai, dan laporan final project menjadi lebih kuat karena menunjukkan pemahaman keterbatasan serta mitigasinya.