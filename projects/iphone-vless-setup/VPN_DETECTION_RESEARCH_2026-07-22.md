# VPN detection research, 2026-07-22

Цель: собрать direct-профили для российских приложений, которые ругаются на VPN, и отделить доменные проблемы от проверки самого VPN-интерфейса iOS.

## Что выяснено

1. ФНС официально использует `lkfl2.nalog.ru/lkfl` для Личного кабинета физлица и приложения «Налоги ФЛ».
2. ФНС использует `lkip.nalog.ru` и `lkip2.nalog.ru/lk` для Личного кабинета индивидуального предпринимателя.
3. МТС в официальной поддержке для проблем приложения «Мой МТС» прямо рекомендует отключить VPN, если он работает. Это сигнал, что приложение может проверять не только IP, но и сам факт VPN-соединения.

## Новый пакет direct-доменов

Новые профили расширены до 230+ direct-доменов:

- ФНС: `lkip.nalog.ru`, `lkip2.nalog.ru`, `lkfl.nalog.ru`, `lkfl2.nalog.ru`, `mobile.nalog.ru`, `service.nalog.ru`, `gnivc.ru`, `nalog.gov.ru`;
- МТС: `mts.ru`, `login.mts.ru`, `oauth.mts.ru`, `api.mts.ru`, `lk.mts.ru`, `profile.mts.ru`, `mtsbank.ru`, `mtsbank.com`, `mtscdn.ru`, `kion.ru`, `mgts.ru`;
- мобильные операторы: Beeline, MegaFon, Tele2/T2;
- гос/идентификация: Госуслуги, ЕСИА, Госключ, ЦБ, НСПК, Мир;
- банки, маркетплейсы, Yandex/VK/Mail, доставка, карты, медицина, кино, travel.

## Профили

```text
D:\AI\airoom-hermes-vds-native-codex-kit\vpn-client-configs\ru-direct-global-hysteria2-vpn-detection-fix.json
D:\AI\airoom-hermes-vds-native-codex-kit\vpn-client-configs\ru-direct-global-vless-reality-vpn-detection-fix.json
```

## Как интерпретировать тест

Если после этих профилей приложение продолжает писать, что включен VPN, вероятная причина — не домен, а проверка iOS VPN-интерфейса приложением. Karing не умеет на iPhone per-app bypass, поэтому такое приложение придется открывать с выключенным VPN или проверять другой клиент с более гибким iOS-поведением.

## Sources

- ФНС: публикации ФНС указывают `lkfl2.nalog.ru/lkfl` как Личный кабинет физлица и «Налоги ФЛ»: https://www.nalog.gov.ru/rn46/news/activities_fts/12405151/
- ФНС/НПД: публикации ФНС и нормативные материалы указывают `lknpd.nalog.ru` и `npd.nalog.ru` для «Мой налог»: https://www.nalog.gov.ru/rn31/news/activities_fts/12325336/
- ФНС/ЛК ИП: публикации ФНС/муниципальные републикации указывают `lkip2.nalog.ru/lk` для ЛК ИП: https://chernyshki.ru/index.php/gosudarstvennye-organy-i-uchrezhdeniya/mezhrajonnaya-ifns-rossii-8/28770-deklaratsiyu-po-usn-udobnee-predstavlyat-cherez-lichnyj-kabinet-individualnogo-predprinimatelya
- МТС: официальная поддержка «Мой МТС» при проблемах с балансом/пакетами рекомендует отключить VPN: https://support.mts.ru/mts_mobilnaya_svyaz/balans-i-spisaniya/chto-delat-esli-balans-ne-pokazivaetsya-v-prilozhenii-moi-mts
- МТС: официальная поддержка по одному сайту/приложению прямо пишет, что некоторые сервисы могут блокировать VPN-трафик: https://support.mts.ru/domashnii_internet_i_tv/ne-rabotaet-domashnii-internet/chto-delat-esli-ne-rabotaet-odin-sait-ili-prilozhenie-chat
