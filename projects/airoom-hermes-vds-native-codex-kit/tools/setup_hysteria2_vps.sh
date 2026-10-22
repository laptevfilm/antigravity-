#!/usr/bin/env bash
set -euo pipefail

HOST_IP="78.17.185.85"
TLS_NAME="222468.com"
CLIENT_DIR="/root/hermes-hysteria2-client"

install -d -m 0750 -o hysteria -g hysteria /etc/hysteria
install -d -m 0700 "$CLIENT_DIR"

/usr/local/bin/hysteria cert \
  --host "${TLS_NAME},${HOST_IP}" \
  --cert /etc/hysteria/server.crt \
  --key /etc/hysteria/server.key \
  --valid-for 87600h \
  --overwrite >/etc/hysteria/cert-info.txt
chown hysteria:hysteria /etc/hysteria/server.crt /etc/hysteria/server.key
chmod 0640 /etc/hysteria/server.crt /etc/hysteria/server.key
chmod 0600 /etc/hysteria/cert-info.txt

if [ ! -s /etc/hysteria/auth.txt ]; then
  openssl rand -hex 24 > /etc/hysteria/auth.txt
  chown root:hysteria /etc/hysteria/auth.txt
  chmod 0640 /etc/hysteria/auth.txt
fi

AUTH="$(tr -d '\r\n' < /etc/hysteria/auth.txt)"
PIN="$(awk '/pinSHA256:/ {print $2; exit}' /etc/hysteria/cert-info.txt)"

umask 027
cat > /etc/hysteria/config.yaml <<EOF
listen: :443

tls:
  cert: /etc/hysteria/server.crt
  key: /etc/hysteria/server.key

auth:
  type: password
  password: ${AUTH}

masquerade:
  type: proxy
  proxy:
    url: https://www.apple.com/
    rewriteHost: true
EOF

chown root:hysteria /etc/hysteria/config.yaml
chmod 0640 /etc/hysteria/config.yaml

cat > "${CLIENT_DIR}/my-hermes-hysteria2-client.yaml" <<EOF
server: ${HOST_IP}:443
auth: ${AUTH}

tls:
  sni: ${TLS_NAME}
  insecure: true
  pinSHA256: ${PIN}

socks5:
  listen: 127.0.0.1:10808

http:
  listen: 127.0.0.1:10809
EOF

/usr/local/bin/hysteria share --config "${CLIENT_DIR}/my-hermes-hysteria2-client.yaml" > "${CLIENT_DIR}/my-hermes-hysteria2-link.txt"
/usr/local/bin/hysteria share --config "${CLIENT_DIR}/my-hermes-hysteria2-client.yaml" --qr --notext > "${CLIENT_DIR}/my-hermes-hysteria2-qr.txt"

chmod 0600 "${CLIENT_DIR}/my-hermes-hysteria2-client.yaml" "${CLIENT_DIR}/my-hermes-hysteria2-link.txt" "${CLIENT_DIR}/my-hermes-hysteria2-qr.txt"

systemctl daemon-reload
systemctl enable --now hysteria-server.service >/dev/null
ufw allow 443/udp comment "VPN Hysteria2" >/dev/null
systemctl restart hysteria-server.service

systemctl is-active hysteria-server.service
ss -u -l -n | awk '{print $4}' | grep -E '(^|:|\*)443$' >/dev/null
echo "udp443-listening"
ufw status | grep -E '443/udp' >/dev/null
echo "ufw-udp443-open"
