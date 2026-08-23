#!/usr/bin/env bash
# Compositor + browser wrapper (cage + Chromium). No site-specific paths.
set -euo pipefail

VOX_PREFIX="${VOX_PREFIX:-$(cd "$(dirname "$0")/.." && pwd)}"
# shellcheck disable=SC1091
source "$VOX_PREFIX/wrappers/alsa.sh"
alsa_prepare

URL="${VOX_KIOSK_URL:-http://127.0.0.1:8090/}"
PROFILE="${VOX_CHROMIUM_PROFILE:-${HOME}/.local/share/vox-templi/chromium}"
export XDG_RUNTIME_DIR="${XDG_RUNTIME_DIR:-/run/user/$(id -u)}"
mkdir -p "$PROFILE" "$XDG_RUNTIME_DIR"
chmod 700 "$XDG_RUNTIME_DIR" 2>/dev/null || true

log() { echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) [kiosk] $*"; }

hostport="${URL#http://}"; hostport="${hostport%%/*}"
for i in $(seq 1 60); do
  if curl -fsS -m 2 "http://${hostport}/healthz" >/dev/null 2>&1; then
    log "httpd ready (${i}s)"; break
  fi
  sleep 1
done

export WLR_RENDERER="${WLR_RENDERER:-pixman}"
export VOX_KIOSK_URL="$URL"
export VOX_CHROMIUM_PROFILE="$PROFILE"
export VOX_ALSA_DEVICE="${VOX_ALSA_DEVICE:-plughw:0,0}"

CAGE="${VOX_CAGE:-$(command -v cage)}"
exec "$CAGE" -s -- "$VOX_PREFIX/wrappers/chromium.sh"
