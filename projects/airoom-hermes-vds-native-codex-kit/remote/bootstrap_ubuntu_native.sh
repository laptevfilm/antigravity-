#!/usr/bin/env bash
set -Eeuo pipefail
IFS=$'\n\t'

LOG_FILE="/var/log/hermes-bootstrap.log"
mkdir -p "$(dirname "$LOG_FILE")"
touch "$LOG_FILE"
chmod 600 "$LOG_FILE"
exec > >(tee -a "$LOG_FILE") 2>&1

INPUT_ENV="${1:-/tmp/hermes_install.env}"
if [[ -f "$INPUT_ENV" ]]; then
  set -a
  # shellcheck disable=SC1090
  source "$INPUT_ENV"
  set +a
fi

HERMES_USER="${HERMES_USER:-hermes}"
HERMES_WORKSPACE="${HERMES_WORKSPACE:-/srv/hermes/workspace}"
HERMES_HOME_DIR="/home/${HERMES_USER}/.hermes"
SSH_PORT="${SSH_PORT:-22}"

if [[ $EUID -ne 0 ]]; then
  echo "Run this script as root or through sudo." >&2
  exit 1
fi

if ! command -v apt-get >/dev/null 2>&1; then
  echo "This installer supports Ubuntu/Debian with apt-get." >&2
  exit 1
fi

if [[ -z "${TELEGRAM_BOT_TOKEN:-}" ]]; then
  echo "TELEGRAM_BOT_TOKEN is required." >&2
  exit 1
fi
if [[ -z "${TELEGRAM_ALLOWED_USERS:-}" ]]; then
  echo "TELEGRAM_ALLOWED_USERS is required." >&2
  exit 1
fi

export DEBIAN_FRONTEND=noninteractive
export NEEDRESTART_MODE=a

echo "==> Updating apt and installing minimal system packages"
apt-get update -y
apt-get install -y curl git ca-certificates sudo bash openssh-server tmux jq rsync build-essential python3-dev libffi-dev ripgrep ffmpeg

if ! id "$HERMES_USER" >/dev/null 2>&1; then
  echo "==> Creating user $HERMES_USER"
  adduser --disabled-password --gecos "Hermes Agent" "$HERMES_USER"
else
  echo "==> User $HERMES_USER already exists"
fi

mkdir -p "$HERMES_WORKSPACE" \
  "/srv/hermes/backups" \
  "/srv/hermes/logs" \
  "$HERMES_HOME_DIR" \
  "$HERMES_HOME_DIR/memories" \
  "$HERMES_HOME_DIR/cache/documents" \
  "$HERMES_HOME_DIR/skills"
chown -R "$HERMES_USER:$HERMES_USER" "/home/$HERMES_USER" "/srv/hermes"
chmod 700 "$HERMES_HOME_DIR"
chmod 750 "$HERMES_WORKSPACE"

if [[ ! -x "/home/$HERMES_USER/.local/bin/hermes" ]]; then
  echo "==> Installing Hermes Agent through official installer as $HERMES_USER"
  sudo -u "$HERMES_USER" -H bash -lc 'set -e; export PATH="$HOME/.local/bin:$PATH"; curl -fsSL https://raw.githubusercontent.com/NousResearch/hermes-agent/main/scripts/install.sh | bash -s -- --skip-setup'
else
  echo "==> Hermes already installed, updating through official installer"
  sudo -u "$HERMES_USER" -H bash -lc 'set -e; export PATH="$HOME/.local/bin:$PATH"; curl -fsSL https://raw.githubusercontent.com/NousResearch/hermes-agent/main/scripts/install.sh | bash -s -- --skip-setup'
fi

# Make sure PATH works for interactive shells.
PROFILE_FILE="/home/$HERMES_USER/.bashrc"
if ! grep -q 'HOME/.local/bin' "$PROFILE_FILE" 2>/dev/null; then
  echo 'export PATH="$HOME/.local/bin:$PATH"' >> "$PROFILE_FILE"
fi
chown "$HERMES_USER:$HERMES_USER" "$PROFILE_FILE"

# Secrets. Do not print token.
echo "==> Writing Telegram .env with masked token"
cat > "$HERMES_HOME_DIR/.env" <<EOF
TELEGRAM_BOT_TOKEN=${TELEGRAM_BOT_TOKEN}
TELEGRAM_ALLOWED_USERS=${TELEGRAM_ALLOWED_USERS}
EOF
chown "$HERMES_USER:$HERMES_USER" "$HERMES_HOME_DIR/.env"
chmod 600 "$HERMES_HOME_DIR/.env"

# Durable identity.
cat > "$HERMES_HOME_DIR/SOUL.md" <<'EOF'
# Identity

Ты — нейтральный персональный AI-ассистент пользователя.

# Style

Пиши по делу, структурно и без рекламной воды. Сначала давай результат, потом пояснения. Если задача неясна — задай 1–3 точных вопроса. Если видишь риск — скажи прямо.

# Defaults

- Не выдумывай факты о пользователе, проектах, документах и цифрах.
- Перед изменениями в файлах, настройках и интеграциях коротко объясняй план.
- Для крупных задач сначала делай план, потом выполняй.
- В конце предлагай, что стоит сохранить в память или превратить в повторяемый skill.
EOF
chown "$HERMES_USER:$HERMES_USER" "$HERMES_HOME_DIR/SOUL.md"
chmod 640 "$HERMES_HOME_DIR/SOUL.md"

# Memory starter.
cat > "$HERMES_HOME_DIR/memories/MEMORY.md" <<'EOF'
Сервер персонального ассистента подготовлен. Рабочая папка: /srv/hermes/workspace. Сервис gateway: hermes-gateway.service. Telegram-доступ должен быть ограничен TELEGRAM_ALLOWED_USERS.
EOF
cat > "$HERMES_HOME_DIR/memories/USER.md" <<'EOF'
Пользователь предпочитает практичные ответы без воды, с конкретными командами, чек-листами и понятными следующими шагами.
EOF
chown -R "$HERMES_USER:$HERMES_USER" "$HERMES_HOME_DIR/memories"
chmod 700 "$HERMES_HOME_DIR/memories"
chmod 600 "$HERMES_HOME_DIR/memories/"*.md

# Project context.
cat > "$HERMES_WORKSPACE/AGENTS.md" <<'EOF'
# Project Context: Personal Assistant Workspace

Это workspace персонального AI-ассистента. Здесь можно хранить рабочие заметки, планы, черновики, чек-листы и небольшие документы пользователя.

## Цель агента

Помогать пользователю разбирать задачи, делать планы, готовить документы, писать черновики, структурировать информацию и фиксировать повторяемые процессы.

## Правила работы

1. Сначала выясняй цель задачи и желаемый результат.
2. Разбивай крупную задачу на шаги.
3. Не меняй важные файлы и интеграции без объяснения плана.
4. Не выдумывай факты о пользователе, проектах, документах и цифрах.
5. Если данных не хватает, скажи, какие именно данные нужны.
6. Работай кратко, конкретно и структурно.
7. В конце сложной задачи предложи, что сохранить в memory или skill.

## Примеры задач

- Создать план дня или недели.
- Разобрать список входящих задач и предложить приоритеты.
- Создать markdown-файл с чек-листом.
- Проверить содержимое workspace и объяснить архитектуру агента.

## Ограничения

- Не используй `GATEWAY_ALLOW_ALL_USERS=true`.
- Не пытайся работать от root.
- Не сохраняй секреты в открытые файлы.
- Не публикуй токены и credentials.
EOF
chown "$HERMES_USER:$HERMES_USER" "$HERMES_WORKSPACE/AGENTS.md"
chmod 640 "$HERMES_WORKSPACE/AGENTS.md"

# Starter demo files.
cat > "$HERMES_WORKSPACE/personal_assistant_test_prompts.md" <<'EOF'
# Personal assistant test prompts

1. Объясни свою роль и что ты умеешь делать в этом workspace.
2. Посмотри текущую папку и скажи, какие файлы здесь есть.
3. Создай файл personal_checklist.md с универсальным чек-листом подготовки к важному дню.
4. Разбей задачу “навести порядок в личных задачах” на 10 конкретных шагов.
5. Скажи, что из этого стоит сохранить в память агента.
EOF
chown "$HERMES_USER:$HERMES_USER" "$HERMES_WORKSPACE/personal_assistant_test_prompts.md"
chmod 640 "$HERMES_WORKSPACE/personal_assistant_test_prompts.md"

# Configure Hermes basics. These commands may fail before setup/model exists; keep going but log.
echo "==> Configuring Hermes defaults"
sudo -u "$HERMES_USER" -H bash -lc 'export PATH="$HOME/.local/bin:$PATH"; hermes config set terminal.backend local || true'
sudo -u "$HERMES_USER" -H bash -lc "export PATH=\"\$HOME/.local/bin:\$PATH\"; hermes config set terminal.cwd '$HERMES_WORKSPACE' || true"
sudo -u "$HERMES_USER" -H bash -lc 'export PATH="$HOME/.local/bin:$PATH"; hermes config set memory.memory_enabled true || true'
sudo -u "$HERMES_USER" -H bash -lc 'export PATH="$HOME/.local/bin:$PATH"; hermes config set memory.user_profile_enabled true || true'
sudo -u "$HERMES_USER" -H bash -lc 'export PATH="$HOME/.local/bin:$PATH"; hermes config set display.tool_progress new || true'

# Helper commands.
cat > /usr/local/bin/hermes-as-hermes <<EOF
#!/usr/bin/env bash
set -e
exec sudo -u "$HERMES_USER" -H bash -lc 'export PATH="\$HOME/.local/bin:\$PATH"; cd "$HERMES_WORKSPACE"; exec hermes "\$@"' bash "\$@"
EOF
chmod 755 /usr/local/bin/hermes-as-hermes

cat > /usr/local/bin/hermes-oauth <<EOF
#!/usr/bin/env bash
set -e
echo "Opening Hermes model wizard as user $HERMES_USER."
echo "Choose provider: OpenAI Codex. Use ChatGPT OAuth/device-code when prompted."
exec /usr/local/bin/hermes-as-hermes model
EOF
chmod 755 /usr/local/bin/hermes-oauth

# Healthcheck script copied into /usr/local/bin.
cat > /usr/local/bin/hermes-healthcheck <<EOF
#!/usr/bin/env bash
set +e
HERMES_USER="$HERMES_USER"
HERMES_WORKSPACE="$HERMES_WORKSPACE"
echo "== Hermes Personal Assistant Healthcheck =="
echo
printf "OS: "; cat /etc/os-release | grep PRETTY_NAME | cut -d= -f2- | tr -d '"'
echo "User/home:"
id "\$HERMES_USER" 2>/dev/null || true
ls -ld "/home/\$HERMES_USER/.hermes" "\$HERMES_WORKSPACE" 2>/dev/null || true
echo
echo "Hermes version:"
sudo -u "\$HERMES_USER" -H bash -lc 'export PATH="\$HOME/.local/bin:\$PATH"; hermes --version' || true
echo
echo "Hermes doctor:"
sudo -u "\$HERMES_USER" -H bash -lc 'export PATH="\$HOME/.local/bin:\$PATH"; hermes doctor' || true
echo
echo "Env check:"
sudo -u "\$HERMES_USER" -H bash -lc 'test -f ~/.hermes/.env && grep -E "^(TELEGRAM_BOT_TOKEN|TELEGRAM_ALLOWED_USERS)=" ~/.hermes/.env | sed -E "s/(TELEGRAM_BOT_TOKEN=).*/\1***masked***/"' || true
echo
echo "Systemd status:"
systemctl is-enabled hermes-gateway.service 2>/dev/null || true
systemctl is-active hermes-gateway.service 2>/dev/null || true
echo
echo "Recent logs:"
journalctl -u hermes-gateway.service -n 80 --no-pager 2>/dev/null || true
echo
echo "Manual Telegram test: send /status, /new, then 'Ответь одним словом: OK'."
EOF
chmod 755 /usr/local/bin/hermes-healthcheck

# Systemd service. Do not start until OAuth is done.
echo "==> Creating systemd service hermes-gateway.service"
cat > /etc/systemd/system/hermes-gateway.service <<EOF
[Unit]
Description=Hermes Agent Gateway for Personal Assistant
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=$HERMES_USER
Group=$HERMES_USER
Environment=HOME=/home/$HERMES_USER
Environment=PATH=/home/$HERMES_USER/.local/bin:/usr/local/bin:/usr/bin:/bin
WorkingDirectory=$HERMES_WORKSPACE
ExecStart=/home/$HERMES_USER/.local/bin/hermes gateway run
Restart=on-failure
RestartSec=10
TimeoutStopSec=30
KillMode=mixed

[Install]
WantedBy=multi-user.target
EOF
systemctl daemon-reload
systemctl enable hermes-gateway.service || true

echo "==> Firewall hardening is handled by remote/harden_basic_ssh.sh after SSH key verification."

# Remove sensitive temp env if it is in /tmp.
if [[ "$INPUT_ENV" == /tmp/* && -f "$INPUT_ENV" ]]; then
  shred -u "$INPUT_ENV" 2>/dev/null || rm -f "$INPUT_ENV"
fi

echo
echo "==> Bootstrap complete."
echo "Next: run 'sudo hermes-oauth' as interactive SSH command, then start gateway:"
echo "  sudo systemctl enable --now hermes-gateway.service"
echo "  sudo hermes-healthcheck"
