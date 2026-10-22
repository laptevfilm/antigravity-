# Codex/OAuth troubleshooting

## Gateway пишет, что нет модели или auth

Проверь, от какого пользователя проходили OAuth:

```bash
sudo ls -la /home/hermes/.hermes/auth.json
sudo ls -la /root/.hermes/auth.json
```

OAuth должен быть в `/home/hermes/.hermes`, потому что gateway работает от пользователя `hermes`.

Правильный запуск:

```bash
sudo hermes-oauth
```

## `hermes: command not found`

```bash
sudo -iu hermes bash -lc 'export PATH="$HOME/.local/bin:$PATH"; which hermes; hermes --version'
```

## После OAuth всё равно ошибка

```bash
sudo systemctl restart hermes-gateway.service
sudo journalctl -u hermes-gateway.service -n 120 --no-pager
sudo -iu hermes bash -lc 'export PATH="$HOME/.local/bin:$PATH"; hermes doctor'
```
