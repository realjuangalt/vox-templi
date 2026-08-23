#!/usr/bin/env bash
# Chromium wrapper: flags for a low-power Wayland kiosk + ALSA.
set -euo pipefail

URL="${VOX_KIOSK_URL:-http://127.0.0.1:8090/}"
PROFILE="${VOX_CHROMIUM_PROFILE:-${HOME}/.local/share/vox-templi/chromium}"
ALSA_DEV="${VOX_ALSA_DEVICE:-plughw:0,0}"
BIN="${VOX_CHROMIUM:-$(command -v chromium || command -v chromium-browser)}"

if command -v wlr-randr >/dev/null 2>&1 && [[ -n "${VOX_OUTPUT:-}" ]]; then
  sleep 0.3
  wlr-randr --output "$VOX_OUTPUT" --mode "${VOX_MODE:-1280x720}" || true
fi

export PIPEWIRE_RUNTIME_DIR="${PIPEWIRE_RUNTIME_DIR:-${XDG_RUNTIME_DIR}/vox-no-pipewire}"
mkdir -p "$PIPEWIRE_RUNTIME_DIR"
unset PULSE_SERVER || true

exec nice -n -5 "$BIN" \
  --user-data-dir="$PROFILE" \
  --ozone-platform=wayland \
  --kiosk \
  --no-first-run \
  --noerrdialogs \
  --disable-infobars \
  --disable-session-crashed-bubble \
  --hide-crash-restore-bubble \
  --disable-features=TranslateUI,InfiniteSessionRestore,BackForwardCache,HeavyAdIntervention,WebGL,WebGL2,AudioServiceSandbox \
  --autoplay-policy=no-user-gesture-required \
  --disable-dev-shm-usage \
  --start-fullscreen \
  --no-default-browser-check \
  --num-raster-threads=1 \
  --force-device-scale-factor=1 \
  --disable-background-networking \
  --disable-sync \
  --disable-component-update \
  --disable-default-apps \
  --metrics-recording-only \
  --js-flags=--max-old-space-size=192 \
  --renderer-process-limit=2 \
  --disable-webgl \
  --disable-webgl2 \
  --audio-buffer-size=8192 \
  --disable-gpu \
  --disable-gpu-compositing \
  --alsa-output-device="$ALSA_DEV" \
  --log-level=3 \
  "$URL"
