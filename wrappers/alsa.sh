#!/usr/bin/env bash
# ALSA wrapper: give Chromium exclusive access to a playback device.
# Usage: source this file, or run with --prepare
set -euo pipefail

VOX_ALSA_DEVICE="${VOX_ALSA_DEVICE:-plughw:0,0}"
VOX_PREFIX="${VOX_PREFIX:-$(cd "$(dirname "$0")/.." && pwd)}"

alsa_prepare() {
  # PipeWire/Pulse will steal the PCM; hide them from this session.
  pkill -u "$(id -u)" -x pipewire-pulse 2>/dev/null || true
  pkill -u "$(id -u)" -x wireplumber 2>/dev/null || true
  pkill -u "$(id -u)" -x pipewire 2>/dev/null || true
  unset PULSE_SERVER || true
  export PIPEWIRE_RUNTIME_DIR="${XDG_RUNTIME_DIR:-/tmp}/vox-no-pipewire"
  mkdir -p "$PIPEWIRE_RUNTIME_DIR"
  if [[ -f "$VOX_PREFIX/wrappers/asound.conf" ]]; then
    cp "$VOX_PREFIX/wrappers/asound.conf" "${HOME}/.asoundrc"
  fi
  amixer -c 0 sset PCM 100% unmute >/dev/null 2>&1 || true
  amixer -c 0 sset Headphone 100% unmute >/dev/null 2>&1 || true
}

if [[ "${1:-}" == "--prepare" ]]; then
  alsa_prepare
fi
