# Источники, по которым сверена сборка

Актуально на 7 мая 2026.

- Hermes Quickstart: https://hermes-agent.nousresearch.com/docs/getting-started/quickstart
- Hermes Installation: https://hermes-agent.nousresearch.com/docs/getting-started/installation
- Hermes CLI Commands Reference: https://hermes-agent.nousresearch.com/docs/reference/cli-commands
- Hermes Telegram Setup: https://hermes-agent.nousresearch.com/docs/user-guide/messaging/telegram
- Hermes Messaging Gateway: https://github.com/NousResearch/hermes-agent/blob/main/website/docs/user-guide/messaging/index.md
- Hermes Configuration: https://hermes-agent.nousresearch.com/docs/user-guide/configuration
- Hermes Persistent Memory: https://hermes-agent.nousresearch.com/docs/user-guide/features/memory
- Hermes Skills System: https://hermes-agent.nousresearch.com/docs/user-guide/features/skills
- Hermes Context Files: https://hermes-agent.nousresearch.com/docs/user-guide/features/context-files
- SOUL.md guide: https://hermes-agent.nousresearch.com/docs/guides/use-soul-with-hermes

Ключевые решения в этой сборке:

1. Не используем Docker. Устанавливаем Hermes нативно через официальный installer.
2. Не запускаем агента от root. Root нужен только для подготовки сервера, создания пользователя и systemd-сервиса.
3. Основной пользователь сервиса: `hermes`.
4. Gateway запускается через systemd как `hermes gateway run`.
5. Telegram доступ ограничен через `TELEGRAM_ALLOWED_USERS`.
6. Codex/ChatGPT OAuth нельзя полностью “зашить” в скрипт: нужно интерактивно пройти `hermes model` и подтвердить device-code в браузере.
