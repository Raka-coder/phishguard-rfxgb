Jangan komentari baris .gitignore begitu saja. Hanya sebagian kecil artefak yang perlu dikeluarkan dari daftar abaikan, dan ada beberapa file yang sebaiknya jangan dipublikasikan dulu. Catatan: file .pkl tidak ada di ZIP ini, jadi ukurannya belum saya lihat dan saya hanya mengandalkan README dan konfigurasi.

1. Aman dan perlu di-commit
File/folder	Catatan
src/*.py, src/trusted_domains.json, api/, app/ (termasuk limitations.json), scripts/, tests/	kode inti
pyproject.toml, uv.lock, .python-version, rxconfig.py, .env.example, .gitignore, reflex.lock/	agar proyek bisa dibangun ulang
README.md, AGENTS.md	setelah diperbarui (lihat bagian 4)
docs/*.md hasil evaluasi, docs/*.json (metrics, realworld, model_c, t25, denylist, stats)	sudah berupa agregat. Pemindaian saya tidak menemukan URL feed di dalamnya.
src/tld_probs.json	kecil dan hanya berisi probabilitas per TLD, jadi hapus baris ignore-nya
2. Jangan dipublikasikan (biarkan di-ignore)
data/ (seluruhnya): dataset berlisensi CC BY-NC-SA, snapshot OpenPhish yang dilarang didistribusikan ulang, dan data legit hasil crawl Anda.
.env, .venv/, .web/, .states, *.parquet, *.zip, .megamemory/, skills/.
src/model_full.pkl (Model A). Model A tidak dipakai aplikasi (hanya evaluate.py), dan README menyebutnya Random Forest, yang kemungkinan besar berukuran besar. Cek ukurannya.

Pemindaian saya tidak menemukan kunci atau rahasia nyata. Yang muncul hanya kata seperti “password” di nama fitur dan daftar filter. Tidak ada path lokal atau nama pengguna.

3. Soal file .pkl: ubah dengan pengecualian, jangan dibuka semua

Aplikasi butuh: src/model.pkl, models/experimental/C_host.pkl, dan models/experimental/tld_probs_host.json. Kalau tidak ada, Model B melempar error, sedangkan Model C diam-diam hilang (fallback). Ganti blok artefak di .gitignore dengan:

# artefak model: hanya yang dibutuhkan aplikasi yang di-commit
src/*.pkl
!src/model.pkl
models/experimental/*
!models/experimental/C_host.pkl
!models/experimental/tld_probs_host.json

(dan hapus baris src/tld_probs.json). Bentuk models/experimental/* diperlukan, karena aturan folder models/experimental/ tidak bisa dikecualikan per file.

Cek ukuran dulu (PowerShell): Get-ChildItem src\*.pkl, models\experimental\* | Select Name, Length. GitHub memperingatkan di 50 MB dan menolak di 100 MB. Kalau model.pkl dan C_host.pkl masing-masing di bawah ±25 MB (dugaan saya XGBoost hanya beberapa MB, belum diverifikasi), commit saja. Kalau lebih besar, pakai GitHub Release dan skrip unduh dengan checksum.

Dua hal tambahan:

Pastikan yang di-commit adalah artefak yang menghasilkan angka di laporan. Saya belum memverifikasi bahwa C_host.pkl di jalur itu hasil train_t25.py (dengan normalisasi www.) dan bahwa predict.py menerapkan normalisasi yang sama. Tanyakan ke agent.
Untuk mata kuliah keamanan: joblib memakai pickle, yang bisa menjalankan kode saat dimuat. Tambahkan di README catatan “hanya muat artefak dari repo ini” dan simpan hash SHA256 kedua file di README. Itu nilai tambah untuk laporan.
4. Yang harus dibereskan sebelum push (T27)
README dan AGENTS.md masih versi lama. AGENTS.md masih menyebut alur “allowlist → model” dengan ±60 domain, tanpa denylist atau Model C, dan klausul “no network at inference” belum menyebut sync_feeds.py. README belum menjelaskan sinkronisasi feed, Model C, dan hasil terbaru, dan tabel “Hasil” hanya Model A/B. Penguji akan salah paham.
tests/fixtures/urls.txt masih berlabel PHISHTANK-PLACEHOLDER dan “Tranco”, padahal sumber kita OpenPhish dan tanpa Tranco. Ubah menjadi “contoh sintetis”.
Aset Persona 5 (karya berhak cipta). assets/img/legit.png dan phishing.png (dipakai di index.py:130) dan font Persona5MenuFontPrototype berisiko untuk repo publik. Ganti dengan ilustrasi atau ikon Anda sendiri sebelum repo dibuka, atau biarkan repo private sampai diganti. Lisensi font perlu dicek sendiri.
Tangkapan layar di docs/screenshots/ usang. Yang saya lihat adalah UI lama (bukan tema sekarang) dalam keadaan “Memeriksa...”. Ukuran index-legit.png dan index-features.png persis sama (69.121 byte), kemungkinan duplikat. Buat ulang dari UI terbaru.
docs/instruction.md berisi perintah lama (“PhishTank ditunda, jangan implementasikan”, “keputusan final”) yang kini bertentangan dengan kondisi proyek. Pindahkan ke docs/arsip/ atau jangan dipublikasikan. docs/phishguard-*.md kemungkinan juga usang, jadi tambahkan catatan “dokumen awal” di atasnya.
docs/hasil_evaluasi.md memuat URL contoh FP/FN dari PhiUSIIL (mis. xvsc.my.id, versoflor.de). Itu boleh dengan atribusi dataset, tetapi tambahkan catatan “label dari dataset, belum diverifikasi independen”. Jangan menyebut domain nyata sebagai “phishing” tanpa catatan itu.
5. Urutan yang saya sarankan
Ubah .gitignore seperti di atas, lalu cek dengan git add -n . (simulasi) dan git ls-files --others --exclude-standard. Pastikan data/ dan .env tidak muncul.
Kerjakan butir 1–6 (cepat lewat T27).
Clone ke folder baru, ikuti README apa adanya, jalankan uv run pytest -q, API, dan UI. Kalau ada langkah yang gagal, perbaiki dulu.
Baru push