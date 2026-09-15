#!/usr/bin/env bash
# Install Vox Templi on this machine (copy tree, units, env, enable services).
# Run as root. Safe to re-run.
set -euo pipefail

if [[ "${EUID}" -ne 0 ]]; then
  echo "run as root: sudo $0" >&2
  exit 1
fi

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PREFIX="${VOX_PREFIX:-/opt/vox-templi}"
STATE="${VOX_STATE_DIR:-/var/lib/vox-templi}"
ENV_DST="/etc/vox-templi/env"

rsync_excludes=(
  --exclude '.git/'
  --exclude 'var/'
  --exclude '__pycache__/'
  --exclude 'chromium/'
  --exclude '.env'
  --exclude '.env.*'
  --exclude 'config.env'
  --include 'config.example.env'
  --exclude '*.env'
  --exclude '*.cookie'
  --exclude '.cookie'
  --exclude 'secrets/'
  --exclude '*.log'
)

if [[ "$ROOT" != "$PREFIX" ]]; then
  echo "==> sync $ROOT -> $PREFIX"
  mkdir -p "$PREFIX"
  rsync -a --delete "${rsync_excludes[@]}" "$ROOT/" "$PREFIX/"
fi

echo "==> dirs + units"
mkdir -p "$STATE" /etc/vox-templi
install -m 644 "$PREFIX/systemd/vox-templi.service" /etc/systemd/system/vox-templi.service
install -m 644 "$PREFIX/systemd/vox-oracle.service" /etc/systemd/system/vox-oracle.service
install -m 644 "$PREFIX/systemd/vox-oracle.timer" /etc/systemd/system/vox-oracle.timer
install -m 644 "$PREFIX/systemd/vox-kiosk.service" /etc/systemd/system/vox-kiosk.service
install -m 644 "$PREFIX/systemd/vox-history.service" /etc/systemd/system/vox-history.service
install -m 644 "$PREFIX/systemd/vox-history.timer" /etc/systemd/system/vox-history.timer
chmod +x "$PREFIX"/wrappers/*.sh "$PREFIX"/scripts/*.sh

if [[ ! -f "$ENV_DST" ]]; then
  install -m 600 "$PREFIX/config.example.env" "$ENV_DST"
  echo "NOTE: edit $ENV_DST (bitcoin cookie path must be readable by the service)" >&2
fi

if [[ -n "${VOX_KIOSK_USER:-}" ]]; then
  mkdir -p /etc/systemd/system/vox-kiosk.service.d
  printf '[Service]\nUser=%s\nGroup=%s\n' "$VOX_KIOSK_USER" "$VOX_KIOSK_USER" \
    > /etc/systemd/system/vox-kiosk.service.d/user.conf
fi

systemctl daemon-reload
# Optional: stop legacy unit names from older installs of this project
systemctl disable --now embassy-monitor.service embassy-kiosk.service embassy-oracle.timer 2>/dev/null || true

systemctl enable --now vox-templi.service
systemctl enable vox-oracle.timer
systemctl start vox-oracle.timer
systemctl enable vox-history.timer
systemctl start vox-history.timer
systemctl start --no-block vox-history.service || true

if systemctl cat vox-kiosk.service >/dev/null 2>&1; then
  systemctl enable vox-kiosk.service
  # Do not fail the whole install if HDMI/cage is missing; HTTP still works.
  systemctl restart vox-kiosk.service || echo "NOTE: vox-kiosk did not start (HDMI/cage optional)" >&2
fi
systemctl start --no-block vox-oracle.service || true

sleep 2
systemctl --no-pager --full status vox-templi.service | head -16 || true
curl -sS -m 5 http://127.0.0.1:8090/healthz || true
echo
echo "Done. Cookie path: $ENV_DST"
echo "Browser: http://127.0.0.1:8090/   Space toggles sound."
