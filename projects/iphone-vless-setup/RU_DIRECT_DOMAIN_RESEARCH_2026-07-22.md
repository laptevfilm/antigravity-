# RU direct domain research, 2026-07-22

Цель: расширить Karing direct-правила для iPhone так, чтобы российские гос-приложения, MAX, банки и маркетплейсы по возможности обходили VPN и шли напрямую через Wi-Fi/мобильную сеть.

## Вывод

Karing на iOS нельзя считать per-app split решением. Рабочий путь — direct по доменам, domain suffix и при необходимости IP/ruleset. Поэтому нужно расширять direct-список не только `.ru`, а экосистемными доменами приложений.

## Приоритет 1: добавить вручную в Karing Direct

Госуслуги и государственные сервисы:

```text
gosuslugi.ru
esia.gosuslugi.ru
gu-st.ru
dom.gosuslugi.ru
cdn.dom.gosuslugi.ru
goskey.ru
nalog.ru
cbr.ru
ebs.ru
mos.ru
mosreg.ru
emias.info
mgfoms.ru
```

MAX:

```text
max.ru
web.max.ru
dev.max.ru
platform-api.max.ru
platform-api2.max.ru
```

Сбер:

```text
sber.ru
sberbank.ru
sberbank.com
sbrf.ru
id.ru
sberbank-insurance.ru
sberbankins.ru
sberspasibo.ru
spasibo.digital
sbermegamarket.ru
megamarket.ru
megamarket.tech
sberhealth.ru
sbermobile.ru
sberdevices.ru
sberdisk.ru
sbercloud.ru
cloud.ru
giga.chat
kuper.ru
samokat.ru
eapteka.ru
```

T-Bank / Tinkoff / Rosbank group:

```text
tbank.ru
tinkoff.ru
tcsbank.ru
tbank-online.com
t-static.ru
cdn-tinkoff.ru
my-tbank.ru
t-bank-app.ru
t-dengi.ru
t-finance.ru
t-investlab.ru
t-j.ru
dolyame.ru
koshelek.app
rosbank.ru
bankline.ru
```

Другие банки:

```text
vtb.ru
pochtabank.ru
alfabank.ru
alfabank.st
alfa.me
gazprombank.ru
gazprombank.com
gpb.ru
mkb.ru
psbank.ru
psb.ru
raiffeisen.ru
raiffeisen-media.ru
open.ru
akbars.ru
uralsib.ru
sovcombank.ru
homecredit.ru
nspk.ru
mironline.ru
```

Маркетплейсы:

```text
avito.ru
avito.st
ozon.ru
ozone.ru
o3.ru
o3t.ru
ozonusercontent.com
ozon-dostavka.ru
ozon-credit.ru
ozon.tech
ozon.travel
wildberries.ru
wb.ru
wbstatic.ru
wbstatic.net
wbcontent.net
wbbasket.ru
geobasket.ru
wb-basket.ru
wb-bank.ru
wbpay.ru
paywb.ru
paywb.com
rwb.ru
```

Yandex/VK/Mail ecosystem:

```text
ya.ru
yandex.ru
yandex.net
yandex.com
yandex.st
yastatic.net
yastat.net
yccdn.ru
vk.com
vk.ru
vk.me
vkmessenger.app
vkmessenger.com
userapi.com
userapi.ru
vk-cdn.net
vk-cdn.ru
vkuser.net
vkusercdn.ru
vkpay.ru
mail.ru
mycdn.me
ok.ru
```

## Karing notes

1. Добавлять как `Domain Suffix` там, где Karing просит тип правила.
2. Для точных хостов вроде `platform-api2.max.ru` можно использовать `Domain`.
3. После изменения правил полностью переподключить VPN.
4. Сначала тестировать без тяжелого `antizapret.srs`: на iOS такие ruleset могут упереться в память.
5. Если конкретное приложение все равно ругается на VPN, нужен лог/экран Karing connections или точное имя приложения для следующей итерации.

## Sources

- MAX docs mention migration to `platform-api2.max.ru` for API requests.
- Gosuslugi/ESIA pages use `gosuslugi.ru`, `esia.gosuslugi.ru`, and assets under `gu-st.ru`.
- v2fly/domain-list-community contains current category lists for Russian government, banks, ecommerce, Sber, T-Bank, Avito, Ozon, Wildberries, Yandex, VK.
