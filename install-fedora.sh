#!/usr/bin/env bash
# install-fedora.sh - Fedora-specific dependency installation.
# Idempotent, non-interactive except sudo escalation.
# Docker and PostgreSQL client are handled by install.sh before this runs,
# but guards are kept so this script is safe to run standalone.

set -euo pipefail

echo "Installing dependencies on Fedora..."

# Python 3.12+ and pip
sudo dnf install -y python3 python3-pip python3-devel

# PostgreSQL client (idempotent; may already be installed by install.sh)
sudo dnf install -y postgresql

# Docker (idempotent; may already be installed by install.sh)
if ! command -v docker &>/dev/null; then
  sudo dnf install -y dnf-plugins-core
  sudo dnf config-manager -y --add-repo https://download.docker.com/linux/fedora/docker-ce.repo
  sudo dnf install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
  sudo systemctl enable --now docker
fi

# HTML→PDF (WeasyPrint) system deps
sudo dnf install -y \
  cairo \
  pango \
  gdk-pixbuf2 \
  libffi \
  shared-mime-info

# Frontend build
sudo dnf install -y nodejs npm

# Validate versions
echo "Validating installed versions..."
python3 --version
docker --version
docker compose version
psql --version
node --version
npm --version

echo "Fedora dependencies installed successfully."
