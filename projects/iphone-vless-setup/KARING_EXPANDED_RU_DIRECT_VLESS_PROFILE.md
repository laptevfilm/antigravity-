# Karing expanded RU direct profile over VLESS Reality

Импортировать этот файл:

```text
D:\AI\airoom-hermes-vds-native-codex-kit\vpn-client-configs\ru-direct-global-vless-reality.json
```

Что делает профиль:

- российские гос-сервисы, MAX, банки, маркетплейсы, Yandex/VK/Mail идут напрямую;
- весь остальной трафик идет через VLESS Reality;
- RU DNS идет напрямую;
- global DNS и загрузка remote ruleset идут через VLESS;
- Hysteria2 и резервный SOCKS5 в этом профиле не используются;
- `50101/tcp` не нужен.

Проверка после импорта:

1. Полностью отключить старый профиль в Karing.
2. Импортировать `ru-direct-global-vless-reality.json`.
3. Подключить новый профиль.
4. `https://ifconfig.me` должен показывать IP VPS.
5. `https://ya.ru/internet` должен работать как российский direct-сегмент.
6. Проверить приложениями: Госуслуги, MAX, банк, Avito/Ozon/WB, Telegram/ChatGPT.

Если VLESS-профиль не подключается, вернуться на Hysteria2-вариант и отдельно проверить, принимает ли Karing VLESS Reality в sing-box custom config на текущей версии iOS.
