#!/usr/bin/env bash
# Deploy to a remote host. Host is *required* — never hardcoded.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
HOST="${VOX_DEPLOY_HOST:?set VOX_DEPLOY_HOST (ssh destination)}"
REMOTE="${VOX_PREFIX:-/opt/vox-templi}"
ENV_SRC="${VOX_ENV_FILE:-$ROOT/config.example.env}"

echo "==> sync $HOST:$REMOTE"
ssh -o BatchMode=yes "$HOST" "mkdir -p '$REMOTE' /var/lib/vox-templi /etc/vox-templi"
rsync -a --delete \
  --exclude '.git/' \
  --exclude 'var/' \
  --exclude '__pycache__/' \
  "$ROOT/" "$HOST:$REMOTE/"

echo "==> units + env"
ssh -o BatchMode=yes "$HOST" bash -s <<EOF
set -euo pipefail
install -m 644 $REMOTE/systemd/vox-templi.service /etc/systemd/system/vox-templi.service
install -m 644 $REMOTE/systemd/vox-oracle.service /etc/systemd/system/vox-oracle.service
install -m 644 $REMOTE/systemd/vox-oracle.timer /etc/systemd/system/vox-oracle.timer
install -m 644 $REMOTE/systemd/vox-kiosk.service /etc/systemd/system/vox-kiosk.service
chmod +x $REMOTE/wrappers/*.sh $REMOTE/scripts/*.sh
if [[ ! -f /etc/vox-templi/env ]]; then
  install -m 600 $REMOTE/config.example.env /etc/vox-templi/env
  echo "NOTE: edit /etc/vox-templi/env (cookie path)" >&2
fi
if [[ -n "${VOX_KIOSK_USER:-}" ]]; then
  mkdir -p /etc/systemd/system/vox-kiosk.service.d
  printf '[Service]\nUser=%s\nGroup=%s\n' "$VOX_KIOSK_USER" "$VOX_KIOSK_USER" \
    > /etc/systemd/system/vox-kiosk.service.d/user.conf
fi
systemctl daemon-reload
systemctl disable --now embassy-monitor.service embassy-kiosk.service embassy-oracle.timer 2>/dev/null || true
systemctl enable --now vox-templi.service
systemctl enable vox-oracle.timer
systemctl start vox-oracle.timer
systemctl enable vox-kiosk.service
systemctl restart vox-kiosk.service
systemctl start --no-block vox-oracle.service || true
sleep 2
systemctl --no-pager --full status vox-templi.service | head -16
curl -sS -m 5 http://127.0.0.1:8090/healthz || true
echo
EOF
echo "Done. Edit /etc/vox-templi/env on the node if this is the first install."
