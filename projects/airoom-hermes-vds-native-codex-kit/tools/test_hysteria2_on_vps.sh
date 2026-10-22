#!/usr/bin/env bash
set -euo pipefail

AUTH="$(tr -d '\r\n' < /etc/hysteria/auth.txt)"
PIN="$(awk '/pinSHA256:/ {print $2; exit}' /etc/hysteria/cert-info.txt)"
TEST_CONFIG="/tmp/hysteria2-client-test.yaml"
TEST_LOG="/tmp/hysteria2-client-test.log"

cat > "$TEST_CONFIG" <<EOF
server: 127.0.0.1:443
auth: ${AUTH}

tls:
  sni: 222468.com
  insecure: true
  pinSHA256: ${PIN}

socks5:
  listen: 127.0.0.1:19080
EOF

chmod 0600 "$TEST_CONFIG"
rm -f "$TEST_LOG"

timeout 25s /usr/local/bin/hysteria client --config "$TEST_CONFIG" >"$TEST_LOG" 2>&1 &
CLIENT_PID="$!"

for _ in $(seq 1 30); do
  if ss -t -l -n | grep -q '127.0.0.1:19080'; then
    break
  fi
  sleep 0.5
done

if ! ss -t -l -n | grep -q '127.0.0.1:19080'; then
  cat "$TEST_LOG"
  kill "$CLIENT_PID" 2>/dev/null || true
  exit 1
fi

HTTP_CODE="$(curl --max-time 15 -sS -o /dev/null -w '%{http_code}' --proxy socks5h://127.0.0.1:19080 https://www.cloudflare.com/cdn-cgi/trace)"
kill "$CLIENT_PID" 2>/dev/null || true
wait "$CLIENT_PID" 2>/dev/null || true

echo "client-socks-listening"
echo "client-test-http-code=${HTTP_CODE}"
