#!/usr/bin/env bash
# install.sh - Single entrypoint: distro-detect, install deps (Docker, DB, Python,
# Node, WeasyPrint), then validate with preflight.
# On Fedora/Arch/EndeavourOS: ./install.sh then ./run.sh for a working UI at
# http://127.0.0.1:8000

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

RED='\033[0;31m'
GREEN='\033[0;32m'
NC='\033[0m'
err() { echo -e "${RED}ERROR: $*${NC}" >&2; }
info() { echo -e "${GREEN}>> $*${NC}"; }

# ---------------------------------------------------------------------------
# 1. OS detection (same normalisation as preflight)
# ---------------------------------------------------------------------------
if [[ -f /etc/os-release ]]; then
  # shellcheck source=/dev/null
  . /etc/os-release
  _id="${ID:-unknown}"
  _id_like="${ID_LIKE:-}"
  case "$_id" in
    arch|endeavouros) OS="arch" ;;
    fedora)           OS="fedora" ;;
    *)
      if [[ "$_id_like" == *arch* ]]; then
        OS="arch"
      elif [[ "$_id_like" == *fedora* ]]; then
        OS="fedora"
      else
        OS="$_id"
      fi
      ;;
  esac
elif [[ "$(uname -s)" == "Darwin" ]]; then
  OS="macos"
else
  OS="unknown"
fi

if [[ "$OS" != "fedora" && "$OS" != "arch" ]]; then
  err "Unsupported OS for install: $OS (supported: Fedora, Arch, EndeavourOS)"
  exit 1
fi

info "Detected OS family: $OS"

# ---------------------------------------------------------------------------
# 2. Minimal bootstrap checks (just the package manager + sudo)
# ---------------------------------------------------------------------------
for cmd in bash sudo; do
  if ! command -v "$cmd" &>/dev/null; then
    err "Missing required command: $cmd — install it and re-run."
    exit 1
  fi
done

if [[ "$OS" == "fedora" ]] && ! command -v dnf &>/dev/null; then
  err "Fedora detected but 'dnf' not found."
  exit 1
fi
if [[ "$OS" == "arch" ]] && ! command -v pacman &>/dev/null; then
  err "Arch detected but 'pacman' not found."
  exit 1
fi

# ---------------------------------------------------------------------------
# 3. Install Docker (if missing)
# ---------------------------------------------------------------------------
install_docker_fedora() {
  info "Installing Docker on Fedora..."
  sudo dnf install -y dnf-plugins-core
  sudo dnf config-manager -y --add-repo \
    https://download.docker.com/linux/fedora/docker-ce.repo
  sudo dnf install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
  sudo systemctl enable --now docker
}

install_docker_arch() {
  info "Installing Docker on Arch..."
  sudo pacman -Sy --noconfirm docker docker-compose
  sudo systemctl enable --now docker
}

if ! command -v docker &>/dev/null; then
  case "$OS" in
    fedora) install_docker_fedora ;;
    arch)   install_docker_arch ;;
  esac
else
  info "Docker already installed ($(docker --version))"
fi

# Ensure daemon is running
if ! docker info &>/dev/null 2>&1; then
  info "Starting Docker daemon..."
  sudo systemctl enable --now docker
  sleep 2
  if ! docker info &>/dev/null 2>&1; then
    err "Docker daemon failed to start. Check 'systemctl status docker'."
    exit 1
  fi
fi

# Verify docker compose
if ! docker compose version &>/dev/null 2>&1; then
  info "Installing Docker Compose plugin..."
  case "$OS" in
    fedora) sudo dnf install -y docker-compose-plugin ;;
    arch)   sudo pacman -Sy --noconfirm docker-compose ;;
  esac
fi

# ---------------------------------------------------------------------------
# 4. Install PostgreSQL client (if missing)
# ---------------------------------------------------------------------------
if ! command -v psql &>/dev/null; then
  info "Installing PostgreSQL client..."
  case "$OS" in
    fedora) sudo dnf install -y postgresql ;;
    arch)   sudo pacman -Sy --noconfirm postgresql-libs postgresql ;;
  esac
else
  info "PostgreSQL client already installed ($(psql --version))"
fi

# ---------------------------------------------------------------------------
# 5. Distro-specific remaining deps (Python, Node, WeasyPrint libs)
# ---------------------------------------------------------------------------
case "$OS" in
  fedora) ./install-fedora.sh ;;
  arch)   ./install-arch.sh ;;
esac

# ---------------------------------------------------------------------------
# 6. Full preflight validation (everything should be present now)
# ---------------------------------------------------------------------------
info "Running full preflight validation..."
./preflight.sh

# ---------------------------------------------------------------------------
# 7. Python virtual environment and backend deps
# ---------------------------------------------------------------------------
info "Setting up Python virtual environment..."
if [[ ! -d .venv ]]; then
  python3 -m venv .venv
fi
# shellcheck source=/dev/null
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# ---------------------------------------------------------------------------
# 8. Frontend build
# ---------------------------------------------------------------------------
if command -v node &>/dev/null && command -v npm &>/dev/null; then
  info "Building frontend..."
  cd frontend && npm ci && npm run build && cd ..
else
  err "Node.js/npm not found after install. Install Node 20+ and run: cd frontend && npm ci && npm run build"
  exit 1
fi

# ---------------------------------------------------------------------------
# Done
# ---------------------------------------------------------------------------
info "Install complete. Run ./run.sh to start the application."
