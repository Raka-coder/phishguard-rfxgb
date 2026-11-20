#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

if command -v docker >/dev/null 2>&1; then
  ENGINE="docker"
elif command -v podman >/dev/null 2>&1; then
  ENGINE="podman"
else
  echo "Tidak ditemukan docker atau podman. Instal salah satu terlebih dahulu." >&2
  exit 1
fi

COMPOSE="${ENGINE} compose"

case "${1:-up}" in
  up)
    ${COMPOSE} up -d --build
    echo "PhishGuard berjalan: UI http://localhost:3000  API http://localhost:8001"
    ;;
  down)
    ${COMPOSE} down
    ;;
  logs)
    ${COMPOSE} logs -f
    ;;
  reset)
    ${COMPOSE} down -v
    echo "Volume phishguard-data dihapus; run berikutnya akan unduh & latih ulang."
    ;;
  *)
    echo "Penggunaan: $0 {up|down|logs|reset}" >&2
    exit 1
    ;;
esac