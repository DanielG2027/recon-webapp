#!/usr/bin/env bash
# install-arch.sh - Arch-specific dependency installation.
# Idempotent, non-interactive except sudo escalation.
# Docker and PostgreSQL client are handled by install.sh before this runs,
# but guards are kept so this script is safe to run standalone.

set -euo pipefail

echo "Installing dependencies on Arch Linux..."

# Python and pip
sudo pacman -Sy --noconfirm python python-pip

# PostgreSQL client (idempotent; may already be installed by install.sh)
sudo pacman -Sy --noconfirm postgresql-libs postgresql

# Docker (idempotent; may already be installed by install.sh)
if ! command -v docker &>/dev/null; then
  sudo pacman -Sy --noconfirm docker docker-compose
  sudo systemctl enable --now docker
fi

# WeasyPrint / PDF system deps
sudo pacman -Sy --noconfirm \
  cairo \
  pango \
  gdk-pixbuf2 \
  libffi \
  shared-mime-info

# Frontend build
sudo pacman -Sy --noconfirm nodejs npm

# Validate versions
echo "Validating installed versions..."
python3 --version
docker --version
docker compose version
psql --version
node --version
npm --version

echo "Arch dependencies installed successfully."
