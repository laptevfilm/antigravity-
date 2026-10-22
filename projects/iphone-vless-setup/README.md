# iPhone VLESS setup

Цель проекта: подобрать стабильную настройку VLESS Reality для iPhone с понятным разделением трафика и без лишнего открытия запасных портов на VPS.

## Текущая инфраструктура

- VPS: `78.17.185.85`.
- Основной публичный порт: `443/tcp` для VLESS Reality.
- Быстрый запасной транспорт: Hysteria2 на `443/udp`.
- SOCKS5 на `50101/tcp` существует как резервный выход, но держать его открытым наружу нежелательно.
- WireGuard/Amnezia работает, но для текущего проекта цель — именно VLESS на iPhone.

## Что уже успешно работало

### Windows / Clash Verge

Рабочий подход для Windows:

- полный VLESS Reality профиль работает;
- Hysteria2 профиль работает и даёт хорошую скорость;
- ru-split в Clash Verge работает, если:
  - `.ru`, `.su`, `.рф` идут напрямую;
  - Yandex-домены идут напрямую;
  - `ipv6-internet.yandex.net` блокируется;
  - для прямого DNS используются `system`, `8.8.8.8`, `1.1.1.1`, потому что только `system` ломался на мобильном интернете;
  - rule-provider `.mrs` можно использовать в Clash Verge, но не стоит переносить этот подход на iPhone без проверки.

Минимальные полезные правила:

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

### Karing / iPhone

Что выяснили:

- Hysteria2 full-tunnel в Karing работает.
- Импорт Clash YAML с ru-split не даёт надёжного результата для iOS-приложений.
- Даже Karing Diversion Rules не дали ожидаемый результат в текущих тестах.
- Для приложений на iPhone нельзя полагаться только на браузерную проверку: приложения используют API/CDN/push-домены и иногда неочевидные маршруты.

Вывод: для iPhone лучше тестировать нативный VLESS-клиент/профиль, а не переносить Windows Clash-логику один в один.

## Рабочие гипотезы для нового проекта

1. Основной путь: VLESS Reality full-tunnel на iPhone.
2. Для ru-split на iPhone сначала проверить клиенты:
   - Shadowrocket — лучший кандидат, но платный;
   - Streisand / FoXray / Fair VPN — бесплатные кандидаты, проверить VLESS Reality и rules;
   - Karing оставить как рабочий full-tunnel/Hysteria2 клиент, но не считать надёжным для ru-split.
3. Не открывать публично SOCKS5 `50101/tcp` без отдельного решения пользователя.
4. Если нужен настоящий ru-split “одним профилем” без капризов iOS-клиента, рассмотреть серверный split с отдельным российским upstream, скрытым внутри VPS.

## Проверки успеха

Для full-tunnel:

- iPhone подключается;
- зарубежные сайты открываются;
- `https://ifconfig.me` или аналог показывает IP VPS;
- скорость приемлемая.

Для ru-split:

- Yandex Internet показывает ожидаемый RU/IP для российского сегмента, а не VPS;
- Avito открывается в приложении и браузере;
- Госуслуги/банковские приложения не блокируют вход;
- зарубежные сайты продолжают идти через VPN.

