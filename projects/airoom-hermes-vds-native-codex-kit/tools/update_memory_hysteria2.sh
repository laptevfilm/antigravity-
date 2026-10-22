#!/usr/bin/env bash
set -euo pipefail

sudo -iu hermes bash <<'EOS'
set -euo pipefail
cd /srv/hermes/workspace/memory-vault

if ! grep -q "Hysteria2 fast iPhone profile" ops/vps-service-baseline.md; then
  cat >> ops/vps-service-baseline.md <<'EOF'

## Hysteria2 fast iPhone profile

Added on 2026-07-22 for the user's free iPhone client setup.

- Service: `hysteria-server.service`
- Protocol/port: Hysteria2 on `443/udp`
- Purpose: fast alternate iPhone connection for Karing/Hiddify.
- Existing VLESS Reality remains the main quiet profile on `443/tcp`.
- Firewall: `443/udp` is allowed for Hysteria2; old SOCKS5 `50101` and WireGuard `51820` remain reserve ports controlled separately.
- Server config: `/etc/hysteria/config.yaml`
- Client files without public disclosure: `/root/hermes-hysteria2-client/`
- Local operator copies: `vpn-client-configs/my-hermes-hysteria2-*` and `C:\Users\Gray\Downloads\my-hermes-hysteria2-*`
- Do not print the Hysteria2 auth string or share URI in chat/logs.
EOF
fi

if ! grep -q "Hysteria2 / 443 UDP" ops/hermes-port-control.md; then
  cat >> ops/hermes-port-control.md <<'EOF'

## Hysteria2 / 443 UDP note

Hysteria2 now uses `443/udp` as a fast iPhone path. Leave it open while the user is testing the "fast" Karing profile. Do not close `443/tcp`; it is the main VLESS Reality path.
EOF
fi

if git diff --quiet -- ops/vps-service-baseline.md ops/hermes-port-control.md; then
  echo "memory-no-change"
else
  git add ops/vps-service-baseline.md ops/hermes-port-control.md
  git commit -m "docs: record hysteria2 iphone profile"
  git push
fi
EOS
