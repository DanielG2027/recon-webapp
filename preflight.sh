#!/usr/bin/env bash
# preflight.sh - Shared prerequisite checks for install and run.
# Must exit non-zero and print remediation if any check fails.
# No partial start of the application.

set -euo pipefail

RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

err() { echo -e "${RED}ERROR: $*${NC}" >&2; }
warn() { echo -e "${YELLOW}WARN: $*${NC}" >&2; }

# --- OS detection ---
# Normalise Arch-based derivatives (EndeavourOS, etc.) to "arch"
detect_os() {
  if [[ -f /etc/os-release ]]; then
    # shellcheck source=/dev/null
    . /etc/os-release
    local id="${ID:-unknown}"
    local id_like="${ID_LIKE:-}"
    case "$id" in
      arch|endeavouros) echo "arch" ;;
      fedora)           echo "fedora" ;;
      *)
        # Fall back to ID_LIKE for other derivatives
        if [[ "$id_like" == *arch* ]]; then
          echo "arch"
        elif [[ "$id_like" == *fedora* ]]; then
          echo "fedora"
        else
          echo "$id"
        fi
        ;;
    esac
  elif [[ "$(uname -s)" == "Darwin" ]]; then
    echo "macos"
  else
    echo "unknown"
  fi
}

OS=$(detect_os)

# --- Required base tooling ---
for cmd in bash sudo curl tar git; do
  if ! command -v "$cmd" &>/dev/null; then
    # Windows may not have sudo; allow optional on Windows
    if [[ "$cmd" == "sudo" && "$OS" == "windows" ]]; then
      continue
    fi
    err "Missing required command: $cmd"
    echo "Install $cmd and re-run." >&2
    exit 1
  fi
done

# wget acceptable instead of curl
if ! command -v curl &>/dev/null && ! command -v wget &>/dev/null; then
  err "Either 'curl' or 'wget' is required."
  exit 1
fi

# --- Supported OS ---
case "$OS" in
  fedora)
    if ! command -v dnf &>/dev/null; then
      err "Fedora detected but 'dnf' not found."
      exit 1
    fi
    ;;
  arch)
    if ! command -v pacman &>/dev/null; then
      err "Arch detected but 'pacman' not found."
      exit 1
    fi
    ;;
  macos|windows)
    err "This OS ($OS) is best-effort only. Out-of-box install is not supported."
    echo "Use Docker Desktop and run the app inside Docker, or install dependencies manually." >&2
    exit 1
    ;;
  *)
    err "Unsupported or unknown OS: $OS. Fully supported: Fedora, Arch, EndeavourOS."
    exit 1
    ;;
esac

# --- Disk space (default >= 20 GB free) ---
min_gb=20
if [[ "$(uname -s)" == "Linux" || "$(uname -s)" == "Darwin" ]]; then
  avail_kb=$(df -k . | awk 'NR==2 {print $4}')
  avail_gb=$((avail_kb / 1024 / 1024))
  if [[ $avail_gb -lt $min_gb ]]; then
    err "Insufficient disk space: ${avail_gb}GB free. Need at least ${min_gb}GB."
    exit 1
  fi
fi

# --- Network (best-effort) ---
if ! (command -v curl &>/dev/null && curl -sSf --connect-timeout 3 -o /dev/null http://example.com 2>/dev/null) && \
   ! (command -v wget &>/dev/null && wget -q -O /dev/null --timeout=3 http://example.com 2>/dev/null); then
  warn "Network connectivity check failed. First-time install may need network."
fi

# --- Docker ---
if ! command -v docker &>/dev/null; then
  err "Docker is not installed or not in PATH."
  echo "Install Docker and ensure the daemon is running, then re-run." >&2
  exit 1
fi

if ! docker info &>/dev/null; then
  err "Docker daemon is not running or not accessible."
  echo "Start Docker (e.g. systemctl start docker) and re-run." >&2
  exit 1
fi

if ! docker compose version &>/dev/null; then
  err "Docker Compose (docker compose) is not available."
  echo "Install Docker Compose plugin or standalone and re-run." >&2
  exit 1
fi

# --- PostgreSQL: host or container mode ---
# We allow containerized Postgres (run.sh will start it), so we only require client tools for migrations.
if ! command -v psql &>/dev/null; then
  err "PostgreSQL client (psql) is required for migrations."
  echo "Install postgresql client package and re-run." >&2
  exit 1
fi

echo "Preflight passed (OS=$OS)."
