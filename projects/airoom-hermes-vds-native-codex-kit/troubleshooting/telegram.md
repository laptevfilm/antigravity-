# Telegram troubleshooting

## Бот молчит

Проверь сервис:

```bash
sudo systemctl status hermes-gateway.service --no-pager
sudo journalctl -u hermes-gateway.service -n 120 --no-pager
```

Проверь env:

```bash
sudo -iu hermes bash -lc 'grep -E "^(TELEGRAM_BOT_TOKEN|TELEGRAM_ALLOWED_USERS)=" ~/.hermes/.env | sed -E "s/(TELEGRAM_BOT_TOKEN=).*/\1***masked***/"'
```

## Unauthorized

Значит numeric Telegram user ID не входит в `TELEGRAM_ALLOWED_USERS`.

Проверь свой ID через @userinfobot и обнови:

```bash
sudo -iu hermes bash -lc 'nano ~/.hermes/.env'
sudo systemctl restart hermes-gateway.service
```

## В личке работает, в группе нет

Telegram privacy mode включён. Для первичной проверки лучше тестировать в личке. Для групп: BotFather → `/mybots` → Bot Settings → Group Privacy → Turn off, затем удалить и заново добавить бота в группу.
