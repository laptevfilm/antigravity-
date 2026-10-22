# Karing expanded RU direct profile

Импортировать этот файл:

```text
D:\AI\airoom-hermes-vds-native-codex-kit\vpn-client-configs\karing-singbox-expanded-ru-direct-global-hysteria2.json
```

Чем отличается от прошлого тестового профиля:

- расширен RU direct список для гос-сервисов, MAX, банков, маркетплейсов, Yandex/VK/Mail;
- RU direct домены добавлены и в DNS rules, и в route rules;
- default/final маршрут остается через Hysteria2;
- резервный SOCKS5 не используется;
- `50101/tcp` не нужен.

Проверочный минимум после импорта:

1. `https://ifconfig.me` показывает IP VPS.
2. `https://ya.ru/internet` не должен показывать VPS для Yandex-сегмента.
3. Госуслуги/банк/Avito/Ozon/WB проверять именно приложениями.
4. MAX проверить отдельно: если продолжит ругаться, нужен экран ошибки или домены из Karing connection log.

Если Karing снова частично сплитует трафик, следующий шаг — добирать конкретные домены по connection log, а не добавлять большие ruleset вслепую.
