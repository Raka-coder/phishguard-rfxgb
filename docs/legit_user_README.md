# Set legitimate pribadi (T24a)

Dokumen ini menjelaskan cara membuat set URL legitimate dari riwayat/bookmark pribadi
tanpa mempublikasikan URL apa pun. Semua file berada di `data/realworld/` yang
gitignored.

## 1. Taruh ekspor di `data/realworld/raw/`

Buat direktori tersebut (atau pakai `--input`), lalu letakkan ekspor dari browser:

- CSV dengan kolom `url`/`href`/`link`/`uri` (nama kolom lain juga dicoba).
- JSON (termasuk bookmark Chrome: `roots.*.children[].url`).
- HTML bookmark (`<a href="...">`).
- TXT: satu URL per baris.

Jika direktori kosong, skrip membuat direktori dan berhenti.

## 2. Jalankan persiapan

```powershell
uv run python scripts/prepare_legit_user.py --person-label anon-1
```

`--person-label` wajib dan harus anonim (mis. `anon-1`), bukan nama asli. Opsi:

- `--input` (default `data/realworld/raw/`): file atau direktori.
- `--output` (default `data/realworld/legit_review.csv`).
- `--max-per-host` (default 5): batas URL per host.

Yang dilakukan skrip:

1. Hanya skema `http`/`https`; buang query dan fragment; simpan skema+host+path.
2. Buang URL sensitif: host/path mengandung `login`, `signin`, `auth`, `oauth`,
   `account`, `mail`, `inbox`, `token`, `password`, `admin`, `logout`, `signup`,
   `register`, `reset`, `verify`, `otp`, `secret`; host IP privat/loopback/reserved;
   host intranet (`.local`, `.internal`, `.lan`, `.home`, `.corp`, `.intranet`,
   `localhost`); domain email/pembayaran pribadi (gmail, outlook, yahoo, paypal,
   bank, dan sejenisnya); path lebih dari 120 karakter.
3. Dedup URL yang identik setelah normalisasi.
4. Batasi maksimum `--max-per-host` URL per host (pertahankan kemunculan pertama).
5. Tambah kolom `in_allowlist` dari `src/trusted_domains.json`, `host_type`
   (`root`/`berpath`), `person_label`, dan `keep` kosong.

Keluaran hanya agregat (jumlah per kelompok, rasio root/berpath, jumlah di luar
allowlist); **tidak ada URL yang dicetak**.

## 3. Review manual

Kolom `keep` diisi dari `keep_suggestions.csv` (saran agent) plus persetujuan pemilik pada 2026-11-17.
atau `0` (buang). Hanya URL yang benar-benar legitimate dan tidak sensitif yang
diberi `1`. File ini gitignored; jangan commit.

## 4. Bagi dev (70%) dan final (30%)

```powershell
uv run python scripts/prepare_legit_user.py --split
```

Pembagian dikelompokkan per host (seed 42), sehingga satu host tidak terpecah
antara dev dan final. Keluaran: `data/realworld/legit_dev.csv` dan
`data/realworld/legit_final.csv` dengan kolom `url`, `in_allowlist`, `host_type`,
`person_label`. Hanya agregat yang dicetak; tidak ada URL.

## 6. Keterbatasan

- Komposisi set: berita, kampus, pemerintah, dokumentasi; sedikit marketplace, bank, SaaS.
- Crawl terbatas: maksimum 10 halaman per situs, tidak diperiksa terhadap robots.txt, jeda antar halaman tidak diukur ketat.
- Host pendek (rata-rata sekitar 17 karakter), sehingga `DomainLength` bisa memengaruhi penilaian.
- `reg_domain` memakai daftar suffix offline (bukan PSL penuh), jadi suffix baru bisa salah.
- Filter sensitif berbasis kata kunci dan daftar domain; URL sensitif yang tidak mengandung kata kunci bisa lolos. Review manual wajib.
- Batas per reg_domain memakai urutan kemunculan input, bukan prioritas path/root.
- `in_allowlist` memakai exact match dari `src/trusted_domains.json`.
- Set ini pribadi; jangan publikasikan URL atau identitas person_label.
- Pembagian 70/30 per reg_domain tidak stratified menurut `in_allowlist` atau `host_type`; proporsi bisa bergeser.
