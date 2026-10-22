# Operator checklist для установки через Codex

## До запуска

Проверь, что есть:

- IP или домен чистого Ubuntu/Debian VDS;
- root password от VDS;
- Telegram bot token от @BotFather;
- numeric Telegram user ID от @userinfobot;
- доступ к ChatGPT/Codex аккаунту для OAuth;
- локально установлен `sshpass` для password-first flow.

## Что вводить Codex

Дай Codex:

1. весь архив;
2. prompt из `CODEX_INSTALL_PROMPT.md`;
3. IP VDS, root password, Telegram bot token, Telegram allowed user IDs.

## Как обращаться с root password

- Не сохраняй root password в `.env`, `.md`, shell history или репозиторий.
- Передавай пароль Codex только для текущей установки.
- После настройки SSH-ключа и базовой защиты вход по root password должен быть отключен.

## После bootstrap

Codex предложит настроить отдельный SSH-ключ. Это нужно, чтобы:

- входить на сервер без пароля;
- не передавать root password в будущих командах;
- безопасно отключить password login.

## После проверки SSH-ключа

Codex предложит базовую защиту сервера:

- firewall `ufw`;
- `fail2ban`;
- автоматические security updates;
- запрет SSH-входа по паролю;
- root login только по SSH-ключу.

SSH-порт не меняется.

## OAuth

Запусти OAuth:

```bash
ssh -i PATH_TO_KEY -p 22 root@SERVER_IP 'sudo hermes-oauth'
```

Выбери провайдера `OpenAI Codex`, затем пройди device-code в браузере.

## После OAuth

```bash
ssh -i PATH_TO_KEY -p 22 root@SERVER_IP 'sudo systemctl enable --now hermes-gateway.service && sudo hermes-healthcheck'
```

## Telegram-проверка

В личке с ботом:

```text
/status
/new
Ответь одним словом: OK
```

## Если бот не отвечает

```bash
ssh -i PATH_TO_KEY -p 22 root@SERVER_IP 'sudo journalctl -u hermes-gateway.service -n 150 --no-pager'
ssh -i PATH_TO_KEY -p 22 root@SERVER_IP 'sudo hermes-healthcheck'
```
