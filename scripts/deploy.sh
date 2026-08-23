#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
HOST="${EM_DEPLOY_HOST:-your-node}"
REMOTE="${EM_REMOTE_DIR:-/opt/embassy-monitor}"

echo "==> sync $HOST:$REMOTE"
ssh -o BatchMode=yes "$HOST" "mkdir -p '$REMOTE' /var/lib/embassy-monitor /var/log/embassy-monitor"
rsync -a --delete \
  --exclude 'var/' \
  --exclude '.git/' \
  "$ROOT/" "$HOST:$REMOTE/"

echo "==> install units"
ssh -o BatchMode=yes "$HOST" bash -s <<EOF
set -euo pipefail
install -m 644 $REMOTE/systemd/embassy-monitor.service /etc/systemd/system/embassy-monitor.service
install -m 644 $REMOTE/systemd/embassy-oracle.service /etc/systemd/system/embassy-oracle.service
install -m 644 $REMOTE/systemd/embassy-oracle.timer /etc/systemd/system/embassy-oracle.timer
install -m 644 $REMOTE/systemd/embassy-kiosk.service /etc/systemd/system/embassy-kiosk.service
chmod +x $REMOTE/scripts/*.sh $REMOTE/scripts/*.py
usermod -aG seat,video,render,input,audio kiosk 2>/dev/null || true
systemctl daemon-reload
systemctl enable --now seatd.service
systemctl enable --now embassy-monitor.service
systemctl enable embassy-oracle.timer
systemctl start embassy-oracle.timer
# HDMI kiosk takes tty1; stop the old PoS kiosk so they don't fight
systemctl disable --now proofofsound-kiosk.service 2>/dev/null || true
systemctl enable embassy-kiosk.service
systemctl stop getty@tty1.service || true
systemctl restart embassy-kiosk.service
systemctl start --no-block embassy-oracle.service || true
sleep 2
systemctl --no-pager --full status embassy-monitor.service | head -16
curl -sS -m 5 http://127.0.0.1:8090/healthz || true
echo
curl -sS -m 8 http://127.0.0.1:8090/api/status | python3 -c "import sys,json; d=json.load(sys.stdin); print('ok', d.get('ok'), 'h', (d.get('chain') or {}).get('height'), 'mp', (d.get('mempool') or {}).get('tx'), 'oracle', (d.get('oracle') or {}).get('state'))"
EOF

echo "Done. HDMI should show the monitor. First UTXOracle pass can take 10–20 min."
