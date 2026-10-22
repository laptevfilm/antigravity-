# Prompt для Codex / ИИ-оператора

Ты работаешь как DevOps-оператор. Твоя задача — установить Hermes Agent на чистый VDS без Docker, подключить Telegram и подготовить нейтрального персонального ассистента.

## Что сначала спросить у пользователя

Попроси только эти данные:

- IP или домен VDS;
- root password от VDS;
- Telegram bot token от BotFather;
- Telegram allowed users: numeric Telegram user IDs, несколько можно через запятую.

Не проси SSH user, SSH port, имя системного пользователя и workspace, если пользователь сам не хочет их менять. Используй defaults: `root`, `22`, `hermes`, `/srv/hermes/workspace`.

## Что нужно сделать

1. Прочитай `AGENTS.md` в этом архиве.
2. Проверь структуру архива.
3. Запусти установку через `scripts/local_deploy_via_ssh.sh`.
4. Установи Hermes нативно, без Docker.
5. Создай пользователя `hermes`, рабочую папку `/srv/hermes/workspace`, `.env`, `SOUL.md`, `AGENTS.md`.
6. Создай systemd-сервис `hermes-gateway.service`, но не пытайся обходить OAuth.
7. После bootstrap скажи пользователю простыми словами:

```text
Сейчас я настрою доступ по SSH-ключу.
Это нужно, чтобы входить на сервер без пароля: так безопаснее, пароль не нужно передавать каждый раз, и после проверки ключа можно отключить вход по root-паролю. Подтверждаете?
```

8. После подтверждения создай отдельный SSH-ключ для этого VDS, установи public key на сервер и проверь вход по ключу.
9. Если SSH-ключ работает, предложи:

```text
SSH-ключ работает. Усилим защиту на сервере?
```

10. После подтверждения включи базовую защиту: `ufw`, `fail2ban`, `unattended-upgrades`, запрет password login, `PermitRootLogin prohibit-password`. Не меняй SSH-порт.
11. Для Codex/ChatGPT OAuth запусти интерактивно:

```bash
ssh -i PATH_TO_KEY -p 22 root@SERVER_HOST 'sudo hermes-oauth'
```

В этот момент покажи пользователю device-code/ссылку и дай пройти авторизацию в браузере.

12. После OAuth запусти:

```bash
ssh -i PATH_TO_KEY -p 22 root@SERVER_HOST 'sudo systemctl daemon-reload && sudo systemctl enable --now hermes-gateway.service && sudo hermes-healthcheck'
```

13. Не печатай Telegram token и root password в логах. Не включай `GATEWAY_ALLOW_ALL_USERS=true`. Не запускай gateway от root.

## Критерии результата

В конце дай короткий отчет:

- где установлен Hermes;
- какой пользователь запускает сервис;
- где workspace;
- статус `hermes-gateway.service`;
- где лежит локальный SSH-ключ;
- включена ли базовая защита;
- какие команды использовать для логов;
- что написать боту в Telegram для проверки.
