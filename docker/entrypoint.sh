#!/usr/bin/env bash
set -euo pipefail

cd /app

run_setup() {
  mkdir -p data/feeds
  if [ ! -f data/PhiUSIIL.csv ]; then
    echo "[entrypoint] Dataset belum ada, mengunduh via kagglehub..."
    uv run python scripts/download_data.py
  fi
  if [ ! -f data/PhiUSIIL.parquet ]; then
    echo "[entrypoint] Mengonversi CSV ke Parquet..."
    uv run python scripts/convert_parquet.py
  fi
  if [ ! -f src/model.pkl ]; then
    echo "[entrypoint] Melatih model..."
    uv run python src/train.py
    uv run python src/evaluate.py
  fi
}

case "${SERVICE:-both}" in
  setup)
    run_setup
    echo "[entrypoint] Setup selesai."
    exit 0
    ;;
  api)
    run_setup
    echo "[entrypoint] Menjalankan API di :8001"
    exec uv run uvicorn api.main:app --host 0.0.0.0 --port 8001
    ;;
  ui)
    echo "[entrypoint] Menjalankan UI di :3000 (backend :8000)"
    export PHISHGUARD_API_URL="${PHISHGUARD_API_URL:-http://api:8001/check}"
    exec uv run reflex run --env prod --frontend-port 3000 --backend-port 8000 --backend-host 0.0.0.0
    ;;
  both)
    run_setup
    echo "[entrypoint] Menjalankan API + UI dalam satu kontainer"
    uv run uvicorn api.main:app --host 0.0.0.0 --port 8001 &
    export PHISHGUARD_API_URL="${PHISHGUARD_API_URL:-http://127.0.0.1:8001/check}"
    exec uv run reflex run --env prod --frontend-port 3000 --backend-port 8000 --backend-host 0.0.0.0
    ;;
  *)
    echo "[entrypoint] SERVICE tidak dikenal: ${SERVICE}" >&2
    exit 1
    ;;
esac