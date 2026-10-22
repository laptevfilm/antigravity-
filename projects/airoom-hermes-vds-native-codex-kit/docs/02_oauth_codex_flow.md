# Codex OAuth flow в Hermes

Hermes поддерживает настройку провайдера модели через interactive command:

```bash
hermes model
```

Для этой сборки нужен путь:

```text
Provider: OpenAI Codex
Auth: ChatGPT OAuth / Device Code
```

## Почему это не полностью автоматизируется

OAuth/device-code специально требует действия человека:

1. Hermes показывает ссылку и код.
2. Пользователь открывает ссылку в браузере.
3. Входит в ChatGPT/OpenAI аккаунт.
4. Подтверждает авторизацию.
5. Hermes сохраняет credentials в `$HERMES_HOME`, обычно в `~/.hermes/auth.json`.

## Команда на сервере

```bash
sudo hermes-oauth
```

или вручную:

```bash
sudo -iu hermes bash -lc 'export PATH="$HOME/.local/bin:$PATH"; cd /srv/hermes/workspace; hermes model'
```

## После OAuth

```bash
sudo systemctl restart hermes-gateway.service
sudo hermes-healthcheck
```

## Ошибка: gateway не видит OAuth

Проверь, что OAuth был выполнен именно от пользователя `hermes`, а не от root:

```bash
sudo ls -la /home/hermes/.hermes/auth.json
sudo ls -la /root/.hermes/auth.json
```

Правильно: credentials должны быть в `/home/hermes/.hermes/`, потому что systemd-сервис работает от пользователя `hermes`.
