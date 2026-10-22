# iPhone VLESS Reality test runbook

Цель: быстро проверить VLESS Reality full-tunnel на iPhone, не трогая запасной SOCKS5 порт и не смешивая проверку full-tunnel с ru-split.

## Порядок теста

1. Сначала проверить full-tunnel.
2. Только после стабильного full-tunnel переходить к ru-split.
3. Браузерной проверки недостаточно: обязательно тестировать реальные приложения.

## Клиенты iOS

Рекомендуемый порядок:

1. Hiddify
   - Бесплатный, open-source, простой интерфейс.
   - Поддерживает VLESS Reality и обычные V2Ray/Xray/Clash/Sing-box профили.
   - Лучший первый кандидат для full-tunnel.

2. Streisand
   - Бесплатный гибкий proxy-клиент.
   - Поддерживает VLESS Reality, Hysteria2, WireGuard и правила маршрутизации.
   - Хороший второй кандидат, если Hiddify не импортирует профиль или ведёт себя нестабильно.

3. Shadowrocket
   - Платный, но практически сильный кандидат для ru-split.
   - Использовать после бесплатных клиентов, если нужен один удобный профиль с правилами.

Karing оставить как подтверждённый рабочий вариант для Hysteria2 full-tunnel. Не считать Karing доказанным решением для ru-split на iPhone.

## Импорт full-tunnel профиля

Источник локального VLESS Reality профиля:

- `D:\AI\airoom-hermes-vds-native-codex-kit\vpn-client-configs\clash-verge-vless-reality-link.txt`

Не публиковать содержимое файла: внутри есть чувствительные параметры подключения.

Практический способ:

1. Открыть файл локально на компьютере.
2. Скопировать всю строку `vless://...`.
3. Передать её на iPhone приватным способом.
4. В Hiddify выбрать импорт из буфера обмена или импорт ссылки.
5. Включить VPN-профиль и разрешить iOS добавить VPN-конфигурацию.

Если Hiddify не принимает ссылку:

1. Повторить импорт в Streisand.
2. Если Streisand тоже не принимает ссылку, использовать Clash YAML full profile:
   - `D:\AI\airoom-hermes-vds-native-codex-kit\vpn-client-configs\clash-verge-vless-reality-full.yaml`
3. Если YAML импортируется, проверить, что итоговый режим именно full-tunnel.

## Проверка full-tunnel

После подключения:

1. Открыть `https://ifconfig.me` или аналог.
2. Убедиться, что внешний IP совпадает с VPS: `78.17.185.85`.
3. Проверить несколько зарубежных сайтов.
4. Проверить Telegram/ChatGPT/YouTube или другой реальный app-трафик.
5. Запустить speedtest и записать:
   - клиент;
   - сеть: Wi-Fi или мобильная;
   - ping;
   - download;
   - upload;
   - были ли отваливающиеся приложения.

## Проверка ru-split

Переходить сюда только после успешного full-tunnel.

Минимальный набор direct-доменов:

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

Проверки ru-split:

1. Yandex Internet показывает ожидаемый российский маршрут.
2. Avito работает в приложении и браузере.
3. Госуслуги и банковские приложения не блокируют вход.
4. Зарубежные сайты продолжают идти через VPN.

## Стоп-условия

Не открывать публично `50101/tcp`.

Не менять SSH-порт.

Не отключать Hysteria2: это уже рабочий быстрый запасной вариант для iPhone.

Если VLESS full-tunnel не работает ни в Hiddify, ни в Streisand, сначала проверить на VPS, слушает ли VLESS Reality `443/tcp` и какой systemd-сервис его обслуживает.
