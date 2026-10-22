#!/usr/bin/env bash
set -Eeuo pipefail
IFS=$'\n\t'

if [[ $EUID -ne 0 ]]; then
  echo "Run through sudo/root." >&2
  exit 1
fi

HERMES_USER="${HERMES_USER:-hermes}"

echo "==> Checking Hermes OAuth/config as $HERMES_USER"
sudo -u "$HERMES_USER" -H bash -lc 'export PATH="$HOME/.local/bin:$PATH"; hermes doctor' || true

echo "==> Starting gateway service"
systemctl daemon-reload
systemctl enable --now hermes-gateway.service
sleep 3
systemctl status hermes-gateway.service --no-pager || true

echo "==> Healthcheck"
hermes-healthcheck || true

echo
cat <<'EOF'
Now test Telegram:

/status
/new
Ответь одним словом: OK
EOF
