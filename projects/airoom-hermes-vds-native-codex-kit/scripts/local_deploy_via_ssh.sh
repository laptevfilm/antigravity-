#!/usr/bin/env bash
set -Eeuo pipefail
IFS=$'\n\t'

KIT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

quote_env() { printf "%q" "$1"; }

ask() {
  local var="$1" prompt="$2" default="${3:-}"
  local current="${!var:-}"
  if [[ -n "$current" ]]; then return 0; fi
  if [[ -n "$default" ]]; then
    read -r -p "$prompt [$default]: " current || true
    current="${current:-$default}"
  else
    read -r -p "$prompt: " current
  fi
  printf -v "$var" '%s' "$current"
}

ask_secret() {
  local var="$1" prompt="$2"
  local current="${!var:-}"
  if [[ -n "$current" ]]; then return 0; fi
  read -r -s -p "$prompt: " current
  echo
  printf -v "$var" '%s' "$current"
}

confirm() {
  local prompt="$1" answer
  read -r -p "$prompt [y/N]: " answer || true
  case "$answer" in
    y|Y|yes|YES|Yes|д|Д|да|Да|ДА) return 0 ;;
    *) return 1 ;;
  esac
}

ask SERVER_HOST "VPS IP/domain"
ROOT_PASSWORD="${ROOT_PASSWORD:-${SSH_PASSWORD:-}}"
ask_secret ROOT_PASSWORD "Root password for the fresh VPS"
ask_secret TELEGRAM_BOT_TOKEN "Telegram bot token from BotFather"
ask TELEGRAM_ALLOWED_USERS "Telegram allowed numeric user IDs, comma-separated"

SSH_USER="${SSH_USER:-root}"
SSH_PORT="${SSH_PORT:-22}"
HERMES_USER="${HERMES_USER:-hermes}"
HERMES_WORKSPACE="${HERMES_WORKSPACE:-/srv/hermes/workspace}"

if [[ -z "$SERVER_HOST" || -z "$ROOT_PASSWORD" || -z "$TELEGRAM_BOT_TOKEN" || -z "$TELEGRAM_ALLOWED_USERS" ]]; then
  echo "Missing required input: VPS IP/domain, root password, Telegram bot token, and Telegram allowed users are required." >&2
  exit 1
fi

if ! command -v sshpass >/dev/null 2>&1; then
  cat >&2 <<'EOF'
sshpass is required for the password-first setup flow.

Install it locally, then run this script again. The root password is passed through
SSHPASS for the current command only; it is not written to files by this kit.
EOF
  exit 1
fi

if ! command -v ssh-keygen >/dev/null 2>&1; then
  echo "ssh-keygen is required to create the dedicated SSH key." >&2
  exit 1
fi

TMP_DIR="$(mktemp -d)"
trap 'rm -rf "$TMP_DIR"' EXIT
TARBALL="$TMP_DIR/hermes-personal-assistant-kit.tgz"
ENVFILE="$TMP_DIR/hermes_install.env"

tar --exclude='.git' --exclude='*.zip' -czf "$TARBALL" -C "$KIT_DIR" .
chmod 600 "$TARBALL"

{
  echo "TELEGRAM_BOT_TOKEN=$(quote_env "$TELEGRAM_BOT_TOKEN")"
  echo "TELEGRAM_ALLOWED_USERS=$(quote_env "$TELEGRAM_ALLOWED_USERS")"
  echo "HERMES_USER=$(quote_env "$HERMES_USER")"
  echo "HERMES_WORKSPACE=$(quote_env "$HERMES_WORKSPACE")"
  echo "SSH_PORT=$(quote_env "$SSH_PORT")"
} > "$ENVFILE"
chmod 600 "$ENVFILE"

REMOTE_TMP="/tmp/hermes-personal-assistant-kit-current"
SSH_TARGET="${SSH_USER}@${SERVER_HOST}"
SSH_OPTS=(-p "$SSH_PORT" -o StrictHostKeyChecking=accept-new -o UserKnownHostsFile="$HOME/.ssh/known_hosts")

ssh_password() {
  SSHPASS="$ROOT_PASSWORD" sshpass -e ssh "${SSH_OPTS[@]}" "$SSH_TARGET" "$@"
}

scp_password() {
  SSHPASS="$ROOT_PASSWORD" sshpass -e scp -P "$SSH_PORT" -o StrictHostKeyChecking=accept-new -o UserKnownHostsFile="$HOME/.ssh/known_hosts" "$@"
}

setup_ssh_key() {
  local safe_host key_dir key_path key_comment public_key quoted_public_key
  safe_host="$(printf '%s' "$SERVER_HOST" | tr -c 'A-Za-z0-9_.-' '_')"
  key_dir="${HERMES_SSH_KEY_DIR:-$HOME/.ssh/hermes-vds}"
  key_path="${HERMES_SSH_KEY_PATH:-$key_dir/${safe_host}_ed25519}"
  key_comment="hermes-${SERVER_HOST}"

  mkdir -p "$key_dir"
  chmod 700 "$key_dir"

  if [[ -e "$key_path" || -e "$key_path.pub" ]]; then
    echo "==> Dedicated SSH key already exists: $key_path"
  else
    echo "==> Creating dedicated SSH key: $key_path"
    ssh-keygen -t ed25519 -f "$key_path" -N "" -C "$key_comment"
    chmod 600 "$key_path"
    chmod 644 "$key_path.pub"
  fi

  public_key="$(<"$key_path.pub")"
  quoted_public_key="$(quote_env "$public_key")"

  echo "==> Installing SSH public key for root on the VPS"
  ssh_password "public_key=$quoted_public_key; install -d -m 700 /root/.ssh && touch /root/.ssh/authorized_keys && chmod 600 /root/.ssh/authorized_keys && grep -qxF \"\$public_key\" /root/.ssh/authorized_keys || printf '%s\n' \"\$public_key\" >> /root/.ssh/authorized_keys"

  echo "==> Verifying SSH key login"
  ssh -i "$key_path" -p "$SSH_PORT" -o BatchMode=yes -o StrictHostKeyChecking=accept-new "$SSH_TARGET" 'true'

  HERMES_SSH_KEY_PATH="$key_path"
  export HERMES_SSH_KEY_PATH
  echo "SSH key works: $key_path"
}

run_hardening() {
  local key_path="${HERMES_SSH_KEY_PATH:-}"
  if [[ -z "$key_path" ]]; then
    echo "Hardening skipped: SSH key path is not available." >&2
    return 1
  fi

  echo "==> Running basic server hardening"
  ssh -i "$key_path" -p "$SSH_PORT" -o BatchMode=yes -o StrictHostKeyChecking=accept-new "$SSH_TARGET" "bash '$REMOTE_TMP/remote/harden_basic_ssh.sh' '$SSH_PORT'"

  echo "==> Re-checking SSH key login after hardening"
  ssh -i "$key_path" -p "$SSH_PORT" -o BatchMode=yes -o StrictHostKeyChecking=accept-new "$SSH_TARGET" 'true'
}

if [[ "$REMOTE_TMP" != /tmp/hermes-personal-assistant-kit-current ]]; then
  echo "Refusing to clean unexpected remote path: $REMOTE_TMP" >&2
  exit 1
fi

echo "==> Preparing remote directory: $REMOTE_TMP"
ssh_password "rm -rf '$REMOTE_TMP' && mkdir -p '$REMOTE_TMP' && chmod 700 '$REMOTE_TMP'"

echo "==> Uploading kit"
scp_password "$TARBALL" "$SSH_TARGET:$REMOTE_TMP/kit.tgz"
scp_password "$ENVFILE" "$SSH_TARGET:$REMOTE_TMP/hermes_install.env"
ssh_password "chmod 600 '$REMOTE_TMP/hermes_install.env'"

echo "==> Running remote bootstrap"
ssh_password "cd '$REMOTE_TMP' && tar xzf kit.tgz && chmod +x remote/*.sh scripts/*.sh tests/*.sh || true && bash remote/bootstrap_ubuntu_native.sh '$REMOTE_TMP/hermes_install.env'"

cat <<'EOF'

Bootstrap completed.

Сейчас я настрою доступ по SSH-ключу.
Это нужно, чтобы входить на сервер без пароля: так безопаснее, пароль не нужно
передавать каждый раз, и после проверки ключа можно отключить вход по root-паролю.
EOF

if confirm "Подтверждаете настройку SSH-ключа?"; then
  setup_ssh_key

  if confirm "SSH-ключ работает. Усилим защиту на сервере?"; then
    run_hardening
  else
    echo "Basic hardening skipped by user."
  fi
else
  echo "SSH key setup skipped by user. Password login remains the only configured access method."
fi

SSH_COMMAND="ssh -p $SSH_PORT $SSH_TARGET"
if [[ -n "${HERMES_SSH_KEY_PATH:-}" ]]; then
  SSH_COMMAND="ssh -i $HERMES_SSH_KEY_PATH -p $SSH_PORT $SSH_TARGET"
fi

cat <<EOF

Next required step: run Codex/ChatGPT OAuth interactively:

  $SSH_COMMAND 'sudo hermes-oauth'

After OAuth, start gateway and run healthcheck:

  $SSH_COMMAND 'sudo systemctl daemon-reload && sudo systemctl enable --now hermes-gateway.service && sudo hermes-healthcheck'

Remote kit path:
  $REMOTE_TMP

EOF
