# Set legit Barat & Lokal (T31.1)

Berkas input mentah: `data/realworld/legit_barat_lokal.txt` (gitignored, mengikuti
konvensi `data/realworld/`). Berisi 40 URL: 20 Barat dan 20 lokal.

## Sumber

| Kelompok | Sumber | Catatan |
|---|---|---|
| Barat (20) | `data/realworld/urls.csv` label `1` (`source=manual`) dan `data/realworld/legit_final.csv` | URL publik yang sudah dipakai evaluasi sebelumnya, bukan URL baru yang dikarang |
| Barat, hosting modern | `vercel.com`, `nextjs.org`, `pages.cloudflare.com`, `digitalocean.com` | Mewakili deploy cloud dan hosting statis |
| Lokal (20) | `data/realworld/urls.csv` label `1`, `data/realworld/legit_final.csv`, dan domain publik yang sudah dikenal | Media, bank, e-commerce, kampus, pemerintah |
| UTM panjang (2) | `tokopedia.com/search` dan `kompas.com` | URL publik nyata dengan parameter UTM contoh; bukan halaman baru, hanya query string untuk menguji pengaruh UTM |

URL tidak pernah dibuka, di-resolve, atau di-probe. Pipeline hanya membaca string URL
(offline). Evaluasi memaksa `PHISHGUARD_USE_GOOGLE=false` agar hasil tidak bergantung
pada kuota atau jawaban Google Safe Browsing; Layer 0 diuji terpisah di
`tests/test_google_sb.py` dan `docs/layer_tests.json`.

## Menjalankan

```powershell
uv run python scripts/eval_legit_set.py
```

Keluaran: `results/data/legit_barat_lokal_results.json` (per URL: verdict, risk_level,
decision_source, probability, trail ringkas) dan ringkasan distribusi band. Skrip tidak
mengubah `docs/`.

## Batas tafsir

- 40 URL adalah sampel kecil dan tidak acak; angka tidak boleh digeneralisasi ke seluruh
  web.
- Beberapa domain lokal ada di allowlist, sehingga `probability=null` dan vonis
  `LEGITIMATE` berasal dari allowlist, bukan model.
- UTM contoh dibuat untuk menguji pengaruh query string, bukan bukti bahwa halaman itu
  sedang memakai kampanye tersebut.
