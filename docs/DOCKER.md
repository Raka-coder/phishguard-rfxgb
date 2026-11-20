# PhishGuard — Containerisasi (Docker / Podman)

Paket ini menambahkan containerisasi ke repositori PhishGuard: satu image berisi
API FastAPI dan antarmuka Reflex, di-orkestrasi dengan Compose, dijalankan dengan
**satu command** — baik di Docker maupun Podman.

## Cara pakai

1. Salin seluruh isi folder ini ke **root** repositori PhishGuard
   (sejajar dengan `pyproject.toml`):

   ```
   phishguard-rfxgb/
   ├── Dockerfile
   ├── .dockerignore
   ├── compose.yaml
   ├── run.sh
   └── docker/entrypoint.sh
   ```

2. Jalankan:

   ```bash
   chmod +x run.sh
   ./run.sh up        # otomatis pakai docker ATAU podman
   ```

   Tanpa `run.sh`, ekuivalennya:

   ```bash
   docker compose up -d --build      # Docker
   podman compose up -d --build      # Podman (rootless)
   ```

3. Buka:
   - **http://localhost:3000** — antarmuka PhishGuard (Cek URL, /evaluasi)
   - **http://localhost:8001/health** — API (endpoint `POST /check` di 8001)

## Apa yang terjadi saat run pertama

| Tahap | Penjelasan |
|---|---|
| `setup` service | Mengunduh dataset PhiUSIIL (~150 MB) via kagglehub **tanpa akun/API key**, konversi ke parquet, melatih Model A & B via 5-fold CV, lalu evaluasi test set |
| `api` service | FastAPI di port 8001 (healthcheck `/health`) |
| `ui` service | Reflex di port 3000, memanggil API lewat jaringan internal compose (`http://api:8001/check`) |

Run pertama butuh **internet** (unduh dataset + paket) dan **RAM ~4 GB** saat
training (menit, bukan jam). Dataset dan hasil training tersimpan di volume
`phishguard-data`, sehingga **run berikutnya langsung jalan** — sesuai klausul
offline-first: inferensi tidak pernah membuka jaringan.

Untuk memaksa unduh + training ulang: `./run.sh reset` (menghapus volume data).

## Perintah lain

```bash
./run.sh down    # matikan container
./run.sh logs    # ikuti log gabungan
./run.sh reset   # down + hapus volume (training ulang)
```

## Env opsional (di `compose.yaml` / `.env`)

- `PHISHGUARD_USE_GOOGLE` + `PHISHGUARD_GOOGLE_API_KEY` — Lapisan 0 Google
  Safe Browsing (opt-in, bawaan mati)
- `PHISHGUARD_FEED_MAX_AGE_HOURS` — batas umur umpan denylist (bawaan 24)
- Umpan denylist: jalankan `./run.sh` lalu eksekusi satu kali
  `docker compose exec api uv run python scripts/sync_feeds.py` (satu-satunya
  komponen yang diizinkan mengakses jaringan secara rutin)

## Catatan kompatibilitas

- `compose.yaml` memakai Compose Spec standar (`condition: service_completed_successfully`
  dan `service_healthy`) — didukung Docker Compose v2, `podman compose` (Podman 4+),
  dan podman-compose terbaru.
- Rootless Podman: tidak ada penggunaan port <1024 (3000 dan 8001), jadi aman tanpa root.
- Image build menjalankan `reflex init` + `reflex compile` sehingga frontend
  sudah ter-compile; container runtime tidak mengunduh dependensi UI lagi.
- Sudah divalidasi: struktur repo, entrypoint, versi pustaka, port, dan env var
  dicocokkan langsung dengan isi repositori (api/main.py, app/app_state.py,
  scripts/download_data.py, pyproject.toml). Belum dibangun end-to-end di mesin
  penulis — jika build pertama gagal, jalankan `./run.sh logs` dan periksa
  tahap `setup`.
