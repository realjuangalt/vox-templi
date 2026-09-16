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

# Prefer a connected HDMI connector and the DRM card that owns it
# (Pi card0/card1 swap across boots: HDMI vs V3D).
detect_hdmi() {
  local conn card out enabled=""
  for conn in /sys/class/drm/card*-HDMI-*; do
    [[ -f "$conn/status" ]] || continue
    [[ "$(cat "$conn/status" 2>/dev/null)" == "connected" ]] || continue
    if [[ "$(cat "$conn/enabled" 2>/dev/null)" == "enabled" ]]; then
      enabled=$conn
      break
    fi
    [[ -n "$enabled" ]] || enabled=$conn
  done
  [[ -n "$enabled" ]] || return 1
  card=$(basename "$enabled")
  card=${card%%-*}
  out=${enabled##*/}
  out=${out#card*-}
  export WLR_DRM_DEVICES="/dev/dri/$card"
  export WLR_BACKENDS=drm
  export VOX_OUTPUT="$out"
  export VOX_MODE="${VOX_MODE:-1920x1080}"
  log "hdmi $VOX_OUTPUT on $WLR_DRM_DEVICES mode=$VOX_MODE"
}

export WLR_RENDERER="${WLR_RENDERER:-pixman}"
export VOX_KIOSK_URL="$URL"
export VOX_CHROMIUM_PROFILE="$PROFILE"
export VOX_ALSA_DEVICE="${VOX_ALSA_DEVICE:-plughw:0,0}"
detect_hdmi || log "hdmi detect: no connected connector (using env)"

CAGE="${VOX_CAGE:-$(command -v cage)}"
exec "$CAGE" -s -- "$VOX_PREFIX/wrappers/chromium.sh"
