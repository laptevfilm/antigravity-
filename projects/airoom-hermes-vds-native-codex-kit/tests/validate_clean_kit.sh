#!/usr/bin/env bash
set -Eeuo pipefail
IFS=$'\n\t'

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

for script in scripts/*.sh remote/*.sh; do
  bash -n "$script"
done

old_markers='AI'' Room|AI''ROOM|ai''room|ворк''шоп|Day'' 1|day''1|Cl''ub|бизнес''-агент|business''_agent'

if rg -n "$old_markers" . \
  --glob '!tests/validate_clean_kit.sh'; then
  echo "Found old branded or event-specific references." >&2
  exit 1
fi

rg -q "ROOT_PASSWORD" scripts/local_deploy_via_ssh.sh
rg -q "setup_ssh_key" scripts/local_deploy_via_ssh.sh
rg -q "harden_basic_ssh.sh" scripts/local_deploy_via_ssh.sh
test -f remote/harden_basic_ssh.sh
test -f templates/personal_assistant_test_prompts.md

echo "Clean kit validation passed."
