#!/usr/bin/env bash
set +e
sudo hermes-healthcheck || true
sudo systemctl status hermes-gateway.service --no-pager || true
sudo journalctl -u hermes-gateway.service -n 120 --no-pager || true
