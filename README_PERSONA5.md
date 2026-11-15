# PhishGuard — tema Persona 5

Salin folder `app/` dan `assets/` ini ke root proyek (timpa `app/` lama; logika/State tidak diubah).

- `app/style.py`  : token warna/font Persona 5 (nama token lama dipertahankan, nilainya dipetakan).
- `app/components.py` : kartu (border putih + bayangan merah), header miring, judul kartu.
- `assets/p5.css` + `assets/fonts/...ttf` : font Persona 5 (didaftarkan lewat `STYLESHEETS`).
- `pages/index.py`, `pages/evaluasi.py` : hanya penyesuaian gaya; grafik `rx.recharts` memakai merah (Model B) dan putih (Model A).

Jalankan: `uv run reflex run`.
