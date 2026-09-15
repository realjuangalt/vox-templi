#!/usr/bin/env bash
# Deploy to a remote host. Host is *required* — never hardcoded.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
HOST="${VOX_DEPLOY_HOST:?set VOX_DEPLOY_HOST (ssh destination)}"
REMOTE="${VOX_PREFIX:-/opt/vox-templi}"

echo "==> sync $HOST:$REMOTE"
ssh -o BatchMode=yes "$HOST" "mkdir -p '$REMOTE' /var/lib/vox-templi /etc/vox-templi"
rsync -a --delete \
  --exclude '.git/' \
  --exclude 'var/' \
  --exclude '__pycache__/' \
  --exclude 'chromium/' \
  --exclude '.env' \
  --exclude '.env.*' \
  --exclude 'config.env' \
  --include 'config.example.env' \
  --exclude '*.env' \
  --exclude '*.cookie' \
  --exclude '.cookie' \
  --exclude 'secrets/' \
  --exclude '*.log' \
  "$ROOT/" "$HOST:$REMOTE/"

echo "==> install units on $HOST"
ssh -o BatchMode=yes "$HOST" \
  env VOX_PREFIX="$REMOTE" VOX_KIOSK_USER="${VOX_KIOSK_USER:-}" \
  bash "$REMOTE/scripts/install.sh"
echo "Done. Edit /etc/vox-templi/env on the node if this is the first install."
