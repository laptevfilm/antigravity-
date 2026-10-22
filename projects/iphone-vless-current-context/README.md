# iPhone VLESS / Hermes VPN current context

Дата создания контекста: 2026-08-12, MSK.

Цель проекта: продолжить настройку VLESS Reality на iPhone, сохранив весь рабочий контекст по Hermes, VPS, VPN-профилям, Karing/Clash Verge и ru-split.

## Инфраструктура

- VPS: `78.17.185.85`.
- SSH: `root@78.17.185.85`, порт `22`, ключ `C:\Users\Gray\.ssh\hermes-vds\78.17.185.85_ed25519`.
- Hermes установлен нативно без Docker.
- Hermes service: `hermes-gateway.service`.
- Hermes user: `hermes`.
- Hermes workspace: `/srv/hermes/workspace`.
- Hermes memory-vault: `/srv/hermes/workspace/memory-vault`.
- Git remote memory: `https://github.com/laptevfilm/hermes-brain.git`.

## Безопасность

- Не печатать root password, Telegram token, private keys, UUID, VLESS private key, SOCKS password, Hysteria2 password.
- Не пушить operational notes в GitHub без явного согласия пользователя.
- Не включать `GATEWAY_ALLOW_ALL_USERS=true`.
- Не запускать Hermes gateway от root.
- Не менять SSH-порт.
- Не открывать `50101/tcp` наружу без явной команды пользователя.

## Текущее состояние VPN

Публично должны быть нужны:

- `22/tcp` — SSH.
- `443/tcp` — VLESS Reality.
- `443/udp` — Hysteria2.

Запасные/нежелательные наружу:

- `50101/tcp` — SOCKS5 reserve.
- `51820/udp` — WireGuard/Amnezia reserve.
- `2096/tcp` / x-ui — не нужен, должен быть выключен.

## Что работало

### Hermes

- Hermes установлен и работал через Telegram.
- Сервис запускается от пользователя `hermes`.
- У Hermes есть helper для управления запасными портами по запросу через Telegram.

### Amnezia / WireGuard

- Amnezia работает стабильно.
- Используется как запасной/альтернативный VPN.

### Hysteria2

- Hysteria2 работает на VPS на `443/udp`.
- На iPhone через Karing full-tunnel работал хорошо.
- На Windows Hysteria2 через Clash Verge тоже работал.

### VLESS Reality

- VLESS Reality работает на `443/tcp`.
- На Windows full-profile работал.
- Цель нового проекта — довести VLESS Reality на iPhone.

### Clash Verge / Windows

Рабочий ru-split алгоритм для Windows:

- RU-домены идут напрямую.
- Остальное идёт через VPN.
- `direct-nameserver` должен содержать fallback:
  - `system`
  - `8.8.8.8`
  - `1.1.1.1`
- Только `system` DNS ломался при мобильном интернете/раздаче.

Важные правила:

```yaml
rules:
  - DOMAIN,ipv6-internet.yandex.net,REJECT
  - DOMAIN-SUFFIX,ru,DIRECT
  - DOMAIN-SUFFIX,su,DIRECT
  - DOMAIN-SUFFIX,xn--p1ai,DIRECT
  - DOMAIN-SUFFIX,ya.ru,DIRECT
  - DOMAIN-SUFFIX,yandex.ru,DIRECT
  - DOMAIN-SUFFIX,yandex.net,DIRECT
  - DOMAIN-SUFFIX,yastatic.net,DIRECT
  - DOMAIN-SUFFIX,yandex.com,DIRECT
  - DOMAIN-SUFFIX,avito.ru,DIRECT
  - DOMAIN-SUFFIX,avito.st,DIRECT
  - DOMAIN-SUFFIX,ozon.ru,DIRECT
  - DOMAIN-SUFFIX,ozone.ru,DIRECT
  - DOMAIN-SUFFIX,gosuslugi.ru,DIRECT
  - DOMAIN-SUFFIX,gu-st.ru,DIRECT
  - DOMAIN-SUFFIX,sber.ru,DIRECT
  - DOMAIN-SUFFIX,sberbank.ru,DIRECT
  - DOMAIN-SUFFIX,tbank.ru,DIRECT
  - DOMAIN-SUFFIX,vtb.ru,DIRECT
  - DOMAIN-SUFFIX,vk.com,DIRECT
  - DOMAIN-SUFFIX,mail.ru,DIRECT
  - MATCH,PROXY
```

Для Yandex speedtest:

- `yandex.net`, `yastatic.net`, `yandex.com` тоже нужны напрямую.
- `ipv6-internet.yandex.net` лучше блокировать, чтобы не путал проверку IPv6.

## Что не сработало / слабые места

### Karing / iPhone ru-split

- Hysteria2 full-tunnel в Karing работает.
- Clash YAML ru-split в Karing не дал надёжного результата для приложений.
- Karing Diversion Rules тоже не подтвердили стабильную работу для RU-приложений.
- Браузерная проверка недостаточна: приложения используют API/CDN/push-домены и могут ходить не так, как сайт.

Вывод: Karing оставить как full-tunnel клиент, но не считать надёжным для ru-split на iPhone.

### Hiddify

- Хорош как простой full-tunnel клиент.
- Для тонкого ru-split хуже Karing/Shadowrocket.
- Не основной кандидат для сложного разделения трафика.

### SOCKS5 как RU-upstream

- Идея: RU через SOCKS5, остальное через Hysteria2.
- Проблема: для iPhone нужен доступ к SOCKS снаружи, а открывать `50101/tcp` наружу нежелательно.
- Этот путь отложен.

## Рекомендуемый следующий путь

1. Начать с VLESS Reality full-tunnel на iPhone.
2. Проверить бесплатные iOS-клиенты:
   - Streisand;
   - FoXray;
   - Fair VPN;
   - Hiddify как full-tunnel fallback.
3. Если нужен надёжный ru-split одним профилем:
   - лучший практический кандидат — Shadowrocket, но он платный;
   - либо серверный split с закрытым российским upstream внутри VPS.
4. Не переносить Windows Clash Verge ru-split один в один на iPhone без проверки реальных приложений.

## Критерии проверки iPhone/VLESS

Full-tunnel:

- iPhone подключается.
- Зарубежные сайты открываются.
- Проверка IP показывает VPS.
- Скорость приемлемая.

Ru-split:

- Avito работает в приложении и браузере.
- Yandex Internet показывает ожидаемый RU/IP для российского сегмента, а не VPS.
- Госуслуги/банковские приложения не блокируют вход.
- Зарубежный трафик идёт через VPN.

