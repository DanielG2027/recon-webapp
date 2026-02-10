#!/usr/bin/env bash
# run.sh - Start Postgres (container), toolchain containers, backend, serve SPA.
# Bind: 127.0.0.1:8000. Run preflight first.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

./preflight.sh

# Activate venv if present
if [[ -d .venv ]]; then
  # shellcheck source=/dev/null
  source .venv/bin/activate
fi

# Start Postgres and toolchain via Docker Compose (detached)
export COMPOSE_PROJECT_NAME=recon-webapp
docker compose up -d postgres

# Wait for Postgres
echo "Waiting for PostgreSQL..."
for i in {1..30}; do
  if docker compose exec -T postgres pg_isready -U recon 2>/dev/null; then
    break
  fi
  sleep 1
done
docker compose exec -T postgres pg_isready -U recon

# Load .env if present
if [[ -f .env ]]; then
  set -a
  # shellcheck source=/dev/null
  source .env
  set +a
fi

# Validate required secrets
if [[ -z "${RECON_DB_PASSWORD:-}" ]]; then
  echo -e "\033[1;31mERROR: RECON_DB_PASSWORD is not set.\033[0m" >&2
  echo "Copy .env.example to .env and set your database password." >&2
  exit 1
fi

# Migrations
export PGPASSWORD="${RECON_DB_PASSWORD}"
export PGHOST="${RECON_DB_HOST:-127.0.0.1}"
export PGPORT="${RECON_DB_PORT:-5432}"
export PGUSER="${RECON_DB_USER:-recon}"
export PGDATABASE="${RECON_DB_NAME:-recon}"
export PYTHONPATH="${SCRIPT_DIR}"
python -m alembic -c backend/alembic.ini upgrade head

# Optional: verify toolchain container (nmap) can run
if docker compose build -q nmap 2>/dev/null; then
  docker compose run --rm nmap echo "Toolchain OK" || true
fi

# ---- Blackwall startup banner ----
echo ""
echo -e "\033[1;31m ▄▄▄▄    ██▓    ▄▄▄       ▄████▄   ██ ▄█▀ █     █░ ▄▄▄       ██▓     ██▓    \033[0m"
echo -e "\033[1;31m▓█████▄ ▓██▒   ▒████▄    ▒██▀ ▀█   ██▄█▒ ▓█░ █ ░█░▒████▄    ▓██▒    ▓██▒    \033[0m"
echo -e "\033[1;31m▒██▒ ▄██▒██░   ▒██  ▀█▄  ▒▓█    ▄ ▓███▄░ ▒█░ █ ░█ ▒██  ▀█▄  ▒██░    ▒██░    \033[0m"
echo -e "\033[1;31m▒██░█▀  ▒██░   ░██▄▄▄▄██ ▒▓▓▄ ▄██▒▓██ █▄ ░█░ █ ░█ ░██▄▄▄▄██ ▒██░    ▒██░    \033[0m"
echo -e "\033[1;31m░▓█  ▀█▓░██████▒▓█   ▓██▒▒ ▓███▀ ░▒██▒ █▄░░██▒██▓  ▓█   ▓██▒░██████▒░██████▒\033[0m"
echo -e "\033[1;31m░▒▓███▀▒░ ▒░▓  ░▒▒   ▓▒█░░ ░▒ ▒  ░▒ ▒▒ ▓▒░ ▓░▒ ▒   ▒▒   ▓▒█░░ ▒░▓  ░░ ▒░▓  ░\033[0m"
echo ""
echo -e "\033[0;36m  Wake up, Samurai. We've got a network to burn.\033[0m"
echo ""
echo -e "\033[0;37m  Local Recon Suite v0.1\033[0m"
echo -e "\033[0;37m  Interface:  \033[1;31mhttp://127.0.0.1:8000\033[0m"
echo -e "\033[0;37m  API Docs:   \033[0;36mhttp://127.0.0.1:8000/api/docs\033[0m"
echo ""

# Start backend (serves API + SPA static files)
exec python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
