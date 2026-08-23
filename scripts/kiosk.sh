#!/usr/bin/env bash
# HDMI kiosk: cage + chromium, ALSA to 3.5mm jack.
set -euo pipefail

URL="${EM_KIOSK_URL:-http://127.0.0.1:8090/}"
PROFILE="${EM_CHROMIUM_PROFILE:-/var/lib/embassy-monitor/chromium}"
LOGDIR="${EM_LOG_DIR:-/var/log/embassy-monitor}"
export XDG_RUNTIME_DIR="${XDG_RUNTIME_DIR:-/run/user/1000}"
mkdir -p "$PROFILE" "$LOGDIR" "$XDG_RUNTIME_DIR"
chmod 700 "$XDG_RUNTIME_DIR" 2>/dev/null || true

log() { echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) [kiosk] $*"; }

# Free the jack from PipeWire so Chromium can open ALSA (same lesson as PoS).
pkill -u "$(id -u)" -x pipewire-pulse 2>/dev/null || true
pkill -u "$(id -u)" -x wireplumber 2>/dev/null || true
pkill -u "$(id -u)" -x pipewire 2>/dev/null || true
sleep 0.4
unset PULSE_SERVER || true
export PIPEWIRE_RUNTIME_DIR="${XDG_RUNTIME_DIR}/em-no-pipewire"
mkdir -p "$PIPEWIRE_RUNTIME_DIR"

if [[ -f /opt/embassy-monitor/scripts/asound.conf ]]; then
  install -m 644 /opt/embassy-monitor/scripts/asound.conf /home/kiosk/.asoundrc 2>/dev/null || \
    cp /opt/embassy-monitor/scripts/asound.conf "$HOME/.asoundrc"
fi
export EM_ALSA_DEVICE="${EM_ALSA_DEVICE:-plughw:0,0}"
amixer -c 0 sset PCM 100% unmute >/dev/null 2>&1 || true
amixer -c 0 sset Headphone 100% unmute >/dev/null 2>&1 || true
log "ALSA $EM_ALSA_DEVICE"

for i in $(seq 1 60); do
  if curl -fsS -m 2 "http://127.0.0.1:8090/healthz" >/dev/null 2>&1; then
    log "monitor ready ${i}s"; break
  fi
  sleep 1
done

export WLR_RENDERER=pixman
export EM_KIOSK_URL="$URL"
export EM_CHROMIUM_PROFILE="$PROFILE"
exec /usr/bin/cage -s -- /opt/embassy-monitor/scripts/kiosk-inner.sh
