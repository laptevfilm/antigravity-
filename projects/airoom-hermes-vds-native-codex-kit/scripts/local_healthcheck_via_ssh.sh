#!/usr/bin/env bash
set -Eeuo pipefail
IFS=$'\n\t'

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

ask SERVER_HOST "VPS IP/domain"
ask SSH_USER "SSH user" "root"
ask SSH_PORT "SSH port" "22"
SSH_TARGET="${SSH_USER}@${SERVER_HOST}"

ssh -p "$SSH_PORT" -o StrictHostKeyChecking=accept-new "$SSH_TARGET" 'sudo hermes-healthcheck || true; sudo systemctl status hermes-gateway.service --no-pager || true; sudo journalctl -u hermes-gateway.service -n 80 --no-pager || true'
