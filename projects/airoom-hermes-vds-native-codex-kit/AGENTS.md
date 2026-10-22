# Инструкция для Codex / ИИ-оператора

Ты устанавливаешь Hermes Agent на чистый Ubuntu/Debian VDS как нейтрального персонального ассистента.

## Цель

Развернуть нативную, без Docker, установку Hermes Agent:

- отдельный системный пользователь `hermes`;
- официальный Hermes installer;
- Telegram gateway;
- allowlist по Telegram user ID;
- Codex/ChatGPT OAuth через `hermes model`;
- systemd-сервис `hermes-gateway.service`;
- отдельный SSH-ключ для доступа к серверу;
- опциональная базовая защита сервера после подтверждения пользователя;
- healthcheck после установки.

## Входные данные

Codex должен запросить у пользователя только:

- IP или домен VDS;
- root-пароль от чистого VDS;
- Telegram bot token от BotFather;
- numeric Telegram user IDs для allowlist, через запятую для нескольких людей.

Внутренние значения по умолчанию:

- `SSH_USER=root`;
- `SSH_PORT=22`;
- `HERMES_USER=hermes`;
- `HERMES_WORKSPACE=/srv/hermes/workspace`.

## Правила безопасности

1. Не печатай Telegram token и root password в логи и ответы.
2. Не сохраняй root password в `.env`, markdown-файлы, shell history или удаленные файлы.
3. Не включай `GATEWAY_ALLOW_ALL_USERS=true`.
4. Не запускай Hermes gateway от root.
5. Root используй только для системной подготовки: apt, создание пользователя, systemd, SSH и firewall.
6. Перед destructive-командами вроде удаления директорий проверь путь дважды.
7. Если модель/OAuth не настроены, не маскируй ошибку: скажи, что нужно пройти `hermes-oauth`.
8. Отключай SSH password login только после успешной проверки входа по SSH-ключу.

## Рекомендуемый порядок действий

Из корня архива:

```bash
chmod +x scripts/*.sh remote/*.sh tests/*.sh
./scripts/local_deploy_via_ssh.sh
```

Скрипт спросит IP, root password, Telegram token и Telegram allowed users, затем:

1. Подключится к VDS по root password.
2. Загрузит kit во временную папку `/tmp/hermes-personal-assistant-kit-current`.
3. Запустит `remote/bootstrap_ubuntu_native.sh`.
4. Предложит настроить отдельный SSH-ключ и объяснит зачем.
5. Проверит вход по SSH-ключу.
6. Предложит включить базовую защиту сервера.

### OAuth

После bootstrap обязательно пройти интерактивный OAuth:

```bash
sudo hermes-oauth
```

В wizard выбрать OpenAI Codex / ChatGPT OAuth / device-code. Человек должен открыть ссылку в браузере и подтвердить код.

### Финализация

После OAuth:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now hermes-gateway.service
sudo hermes-healthcheck
```

## Критерии готовности

Установка считается готовой, если:

```bash
systemctl is-active hermes-gateway.service
```

возвращает `active`, а в Telegram бот отвечает на:

```text
/status
/new
Ответь одним словом: OK
```

## Что делать, если Telegram молчит

```bash
sudo -iu hermes bash -lc 'grep TELEGRAM_BOT_TOKEN ~/.hermes/.env | sed "s/=.*/=***masked***/"'
sudo -iu hermes bash -lc 'grep TELEGRAM_ALLOWED_USERS ~/.hermes/.env'
sudo systemctl status hermes-gateway.service --no-pager
sudo journalctl -u hermes-gateway.service -n 120 --no-pager
sudo -iu hermes bash -lc 'export PATH="$HOME/.local/bin:$PATH"; hermes doctor'
```

Если OAuth не пройден, выполнить `sudo hermes-oauth`.

## Внешняя память Hermes

В каждой новой сессии по этому проекту Codex должен сначала смотреть репозиторий `laptevfilm/hermes-brain.git`:

```text
https://github.com/laptevfilm/hermes-brain.git
```

Считай этот репозиторий второй памятью Hermes. Перед действиями по Hermes/VPN/личному ассистенту сверяйся с ним, если доступ к интернету и GitHub есть. Если доступа нет — явно скажи пользователю, что память `hermes-brain` сейчас недоступна, и продолжай по локальному контексту.
