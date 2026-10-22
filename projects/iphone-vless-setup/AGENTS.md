# Codex rules for this project

Проект посвящён настройке VLESS Reality на iPhone.

## Session start

Перед действиями по Hermes/VPN/личному ассистенту синхронизировать memory-vault на VPS:

```powershell
ssh -i C:\Users\Gray\.ssh\hermes-vds\78.17.185.85_ed25519 -p 22 root@78.17.185.85 "sudo -iu hermes bash -lc 'cd /srv/hermes/workspace/memory-vault && git status --short --branch && git pull --ff-only'"
```

Если сервер или GitHub недоступны, явно сказать об этом и продолжить по локальному контексту.

## Security

- Не печатать токены, root password, приватные ключи, UUID, SOCKS password, VLESS private key.
- Не пушить operational notes в GitHub без явного согласия пользователя.
- Не открывать `50101/tcp` наружу без явной команды пользователя.
- Не менять SSH-порт.
- Не отключать рабочие VPN-сервисы без подтверждения.

## Known working state

- VPS: `78.17.185.85`.
- VLESS Reality: `443/tcp`.
- Hysteria2: `443/udp`, работает быстро на iPhone через Karing.
- SOCKS5: `50101/tcp`, работает как резерв, но публично открывать нежелательно.
- Amnezia/WireGuard работает, но не является целью этого проекта.

## Lessons learned

- Windows Clash Verge ru-split работает после правки DNS fallback:
  - `direct-nameserver: system, 8.8.8.8, 1.1.1.1`.
- Для Yandex speedtest нужны direct-правила:
  - `ya.ru`,
  - `yandex.ru`,
  - `yandex.net`,
  - `yastatic.net`,
  - `yandex.com`,
  - и блок `ipv6-internet.yandex.net`.
- Karing на iPhone не подтвердил надёжную работу ru-split для приложений через импортированный YAML/Diversion Rules.
- Для iPhone не считать браузерную проверку достаточной: обязательно проверять приложения.

## Preferred next direction

1. Настроить и проверить VLESS Reality full-tunnel на iPhone.
2. Подобрать бесплатный iOS-клиент для VLESS Reality:
   - Streisand;
   - FoXray;
   - Fair VPN;
   - Hiddify как простой full-tunnel кандидат.
3. Если нужен качественный ru-split одним профилем:
   - лучший практический кандидат — Shadowrocket, но он платный;
   - бесплатные клиенты проверять только по факту логов/поведения.

