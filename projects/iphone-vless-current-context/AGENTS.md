# Codex project rules

Этот проект продолжает настройку VLESS Reality на iPhone с учётом уже найденных правил Hermes/VPN.

## Start-of-session checklist

Перед действиями по Hermes/VPN/личному ассистенту попытаться синхронизировать Hermes memory-vault:

```powershell
ssh -i C:\Users\Gray\.ssh\hermes-vds\78.17.185.85_ed25519 -p 22 root@78.17.185.85 "sudo -iu hermes bash -lc 'cd /srv/hermes/workspace/memory-vault && git status --short --branch && git pull --ff-only'"
```

Если SSH/GitHub недоступны, явно сказать об этом и продолжить по локальному контексту.

## Safety rules

- Не печатать секреты: root password, Telegram token, auth files, private keys, UUID, VLESS keys, SOCKS/Hysteria2 passwords.
- Не пушить operational context в GitHub без явного согласия пользователя.
- Не открывать `50101/tcp` наружу без явной команды пользователя.
- Не менять SSH-порт.
- Не отключать рабочие VPN-сервисы без подтверждения.
- Не запускать gateway от root.

## Known good facts

- VPS: `78.17.185.85`.
- VLESS Reality: `443/tcp`.
- Hysteria2: `443/udp`, хорошо работает на iPhone full-tunnel через Karing.
- Amnezia/WireGuard работает.
- Hermes работает через Telegram.
- Windows Clash Verge ru-split работает с DNS fallback `system`, `8.8.8.8`, `1.1.1.1`.

## iPhone lessons

- Karing full-tunnel подходит.
- Karing ru-split через Clash YAML/Diversion Rules не подтвердился для приложений.
- Hiddify рассматривать как full-tunnel fallback, не как основной ru-split клиент.
- Для бесплатного VLESS Reality на iPhone проверить Streisand, FoXray, Fair VPN.
- Для максимально надёжного ru-split одним профилем вероятный лучший клиент — Shadowrocket, но он платный.

## Working direction

Главный следующий шаг: собрать и проверить VLESS Reality full-tunnel профиль для iPhone, затем уже отдельно решать ru-split.

