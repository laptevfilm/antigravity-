# Hermes Personal Assistant Native VDS Kit для Codex

Это сборка для установки Hermes Agent на чистый Ubuntu/Debian VDS **без Docker**.

Задача архива: дать Codex все, что нужно, чтобы по IP и root-паролю подключиться к чистому серверу, установить Hermes, подключить Telegram, настроить SSH-ключ, при подтверждении включить базовую защиту и оставить понятные команды проверки.

## Что получится после установки

- На сервере создан пользователь `hermes`.
- Hermes установлен нативно в `/home/hermes/.hermes/hermes-agent`.
- Рабочая папка агента: `/srv/hermes/workspace`.
- Telegram token и allowlist лежат в `/home/hermes/.hermes/.env`.
- Project context лежит в `/srv/hermes/workspace/AGENTS.md`.
- Agent identity лежит в `/home/hermes/.hermes/SOUL.md`.
- Gateway запускается systemd-сервисом `hermes-gateway.service`.
- Есть helper-команды:
  - `hermes-as-hermes ...`
  - `hermes-oauth`
  - `hermes-healthcheck`

## Быстрый путь для Codex

1. Открой `CODEX_INSTALL_PROMPT.md`.
2. Передай Codex реальные значения: IP сервера, root password, Telegram bot token, Telegram user ID.
3. Codex запускает `scripts/local_deploy_via_ssh.sh`.
4. После bootstrap Codex предлагает настроить SSH-ключ и объясняет, что это нужно для безопасного входа без пароля.
5. После проверки SSH-ключа Codex предлагает включить базовую защиту сервера.
6. После этого нужно интерактивно пройти OAuth:

```bash
ssh -i ~/.ssh/hermes-vds/SERVER_ed25519 -p 22 root@SERVER_IP 'sudo hermes-oauth'
```

В wizard выбери провайдера **OpenAI Codex** и пройди ChatGPT OAuth/device-code в браузере.

7. После OAuth:

```bash
ssh -i ~/.ssh/hermes-vds/SERVER_ed25519 -p 22 root@SERVER_IP 'sudo systemctl daemon-reload && sudo systemctl enable --now hermes-gateway.service && sudo hermes-healthcheck'
```

## Быстрый запуск локального deploy-скрипта

На своей машине:

```bash
cd hermes-personal-assistant-vds-kit
chmod +x scripts/*.sh remote/*.sh tests/*.sh
./scripts/local_deploy_via_ssh.sh
```

Скрипт спросит:

- IP/host сервера;
- root password;
- Telegram bot token;
- Telegram allowed numeric user IDs.

Для password-first flow локально нужен `sshpass`. Скрипт передает root password через `SSHPASS` только для текущих SSH/SCP-команд и не пишет пароль в файлы.

## Базовая защита

После проверки входа по SSH-ключу скрипт спросит:

```text
SSH-ключ работает. Усилим защиту на сервере?
```

При подтверждении будет включено:

- `ufw` с разрешенным текущим SSH-портом;
- `fail2ban`;
- `unattended-upgrades`;
- запрет SSH-входа по паролю;
- `PermitRootLogin prohibit-password`, чтобы root оставался доступен только по ключу.

Порт SSH не меняется.

## Важное ограничение

Codex/ChatGPT OAuth нельзя полноценно автоматизировать без участия человека. Hermes запускает device-code flow через `hermes model`; человек должен открыть ссылку, войти в аккаунт и подтвердить код.

## Где смотреть логи

```bash
sudo journalctl -u hermes-gateway.service -f
sudo tail -n 200 /var/log/hermes-bootstrap.log
sudo hermes-healthcheck
```

## Не делаем в этой сборке

- Не используем Docker.
- Не включаем `GATEWAY_ALLOW_ALL_USERS=true`.
- Не запускаем gateway от root.
- Не отключаем password login до проверки SSH-ключа.
