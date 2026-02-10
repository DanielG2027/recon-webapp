#!/usr/bin/env bash
# uninstall.sh - Remove app artifacts and containers. Does not remove system packages by default.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

export COMPOSE_PROJECT_NAME=recon-webapp

echo "Stopping and removing containers..."
docker compose down -v 2>/dev/null || true

echo "Removing artifact and report data..."
rm -rf data/artifacts data/reports 2>/dev/null || true

echo "Optionally remove venv: rm -rf .venv"
echo "Optionally remove node_modules: rm -rf frontend/node_modules frontend/dist"
echo "Uninstall complete. System packages (Docker, PostgreSQL client, etc.) were not removed."
