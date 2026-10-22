#!/usr/bin/env bash
set -Eeuo pipefail
IFS=$'\n\t'

SSH_PORT="${1:-${SSH_PORT:-22}}"

if [[ $EUID -ne 0 ]]; then
  echo "Run this script as root." >&2
  exit 1
fi

if [[ ! -s /root/.ssh/authorized_keys ]]; then
  echo "Refusing to disable password login: /root/.ssh/authorized_keys is empty or missing." >&2
  exit 1
fi

if ! command -v apt-get >/dev/null 2>&1; then
  echo "This hardening script supports Ubuntu/Debian with apt-get." >&2
  exit 1
fi

export DEBIAN_FRONTEND=noninteractive
export NEEDRESTART_MODE=a

echo "==> Installing basic security packages"
apt-get update -y
apt-get install -y ufw fail2ban unattended-upgrades

echo "==> Enabling firewall with SSH allowed"
ufw allow "${SSH_PORT}/tcp"
ufw --force enable

echo "==> Enabling fail2ban"
systemctl enable --now fail2ban

echo "==> Enabling unattended security upgrades"
dpkg-reconfigure -f noninteractive unattended-upgrades || true
cat > /etc/apt/apt.conf.d/20auto-upgrades <<'EOF'
APT::Periodic::Update-Package-Lists "1";
APT::Periodic::Unattended-Upgrade "1";
EOF

SSHD_CONFIG="/etc/ssh/sshd_config"
BACKUP="/etc/ssh/sshd_config.hermes-backup.$(date +%Y%m%d%H%M%S)"
cp "$SSHD_CONFIG" "$BACKUP"

set_sshd_option() {
  local key="$1" value="$2"
  if grep -Eq "^[#[:space:]]*${key}[[:space:]]+" "$SSHD_CONFIG"; then
    sed -i -E "s|^[#[:space:]]*${key}[[:space:]]+.*|${key} ${value}|" "$SSHD_CONFIG"
  else
    printf '\n%s %s\n' "$key" "$value" >> "$SSHD_CONFIG"
  fi
}

echo "==> Disabling SSH password login after key access is confirmed"
set_sshd_option "PermitRootLogin" "prohibit-password"
set_sshd_option "PasswordAuthentication" "no"
set_sshd_option "KbdInteractiveAuthentication" "no"
set_sshd_option "PubkeyAuthentication" "yes"

sshd -t
systemctl reload ssh || systemctl reload sshd

echo "Basic hardening complete."
echo "Backup sshd config: $BACKUP"
