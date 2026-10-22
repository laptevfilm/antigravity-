import json
from pathlib import Path


ROOT = Path(r"D:\AI\airoom-hermes-vds-native-codex-kit")
HY_CLIENT = ROOT / "vpn-client-configs" / "my-hermes-hysteria2-client.yaml"
SOCKS_CLIENT = ROOT / "vpn-client-configs" / "clash-verge-socks5.yaml"
OUT = ROOT / "vpn-client-configs" / "karing-singbox-ru-socks-global-hysteria2.json"


RU_TLD_REGEX = [
    r"(^|.+\.)(ru|su|xn--p1ai)$",
]


RU_DOMAIN_SUFFIXES = [
    "ya.ru",
    "yandex.ru",
    "yandex.net",
    "yastatic.net",
    "yandex.com",
    "avito.ru",
    "avito.st",
    "ozon.ru",
    "ozone.ru",
    "gosuslugi.ru",
    "gu-st.ru",
    "sberbank.ru",
    "sber.ru",
    "tbank.ru",
    "vtb.ru",
    "alfabank.ru",
    "raiffeisen.ru",
    "mts.ru",
    "megafon.ru",
    "beeline.ru",
    "tele2.ru",
    "vk.com",
    "vk.ru",
    "ok.ru",
    "mail.ru",
    "mycdn.me",
]


def read_flat_yaml(path: Path) -> dict[str, str]:
    result: dict[str, str] = {}
    in_proxy = False
    in_tls = False

    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.rstrip()
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue

        if stripped == "proxies:":
            in_proxy = True
            in_tls = False
            continue
        if not line.startswith(" ") and stripped.endswith(":"):
            in_tls = stripped == "tls:"
            if stripped != "tls:":
                in_proxy = False
            continue
        if ":" not in stripped:
            continue

        key, value = stripped.split(":", 1)
        key = key.strip().lstrip("- ").strip()
        value = value.strip().strip('"').strip("'")
        if not value:
            continue

        if in_tls:
            result[f"tls.{key}"] = value
        elif in_proxy or not line.startswith(" "):
            result[key] = value

    return result


def main() -> None:
    hy = read_flat_yaml(HY_CLIENT)
    socks = read_flat_yaml(SOCKS_CLIENT)

    hy_server, hy_port_text = hy["server"].rsplit(":", 1)
    hy_port = int(hy_port_text)

    config = {
        "log": {
            "level": "info",
            "timestamp": True,
        },
        "dns": {
            "servers": [
                {
                    "type": "udp",
                    "tag": "ru-dns",
                    "server": "77.88.8.8",
                    "server_port": 53,
                    "detour": "ru-socks",
                },
                {
                    "type": "tls",
                    "tag": "global-dns",
                    "server": "1.1.1.1",
                    "server_port": 853,
                    "detour": "global-hysteria2",
                },
            ],
            "rules": [
                {
                    "domain_regex": RU_TLD_REGEX,
                    "domain_suffix": RU_DOMAIN_SUFFIXES,
                    "action": "route",
                    "server": "ru-dns",
                }
            ],
            "final": "global-dns",
            "strategy": "ipv4_only",
            "reverse_mapping": True,
        },
        "inbounds": [
            {
                "type": "tun",
                "tag": "tun-in",
                "address": ["172.19.0.1/30"],
                "auto_route": True,
                "strict_route": True,
                "sniff": True,
                "sniff_override_destination": True,
            }
        ],
        "outbounds": [
            {
                "type": "hysteria2",
                "tag": "global-hysteria2",
                "server": hy_server,
                "server_port": hy_port,
                "password": hy["auth"],
                "tls": {
                    "enabled": True,
                    "server_name": hy.get("tls.sni", "222468.com"),
                    "insecure": True,
                },
            },
            {
                "type": "socks",
                "tag": "ru-socks",
                "server": socks["server"],
                "server_port": int(socks["port"]),
                "version": "5",
                "username": socks.get("username", ""),
                "password": socks.get("password", ""),
            },
            {
                "type": "direct",
                "tag": "direct",
            },
            {
                "type": "block",
                "tag": "block",
            },
        ],
        "route": {
            "auto_detect_interface": True,
            "rules": [
                {
                    "protocol": ["dns"],
                    "action": "hijack-dns",
                },
                {
                    "ip_is_private": True,
                    "outbound": "direct",
                },
                {
                    "domain": ["ipv6-internet.yandex.net"],
                    "outbound": "block",
                },
                {
                    "domain_regex": RU_TLD_REGEX,
                    "domain_suffix": RU_DOMAIN_SUFFIXES,
                    "outbound": "ru-socks",
                },
                {
                    "rule_set": [
                        "geosite-category-ru",
                        "geosite-category-bank-ru",
                        "geosite-category-ecommerce-ru",
                        "geosite-category-entertainment-ru",
                        "geosite-category-gov-ru",
                        "geosite-category-media-ru",
                        "geosite-category-retail-ru",
                        "geosite-category-travel-ru",
                        "geoip-ru",
                    ],
                    "outbound": "ru-socks",
                },
            ],
            "rule_set": [
                {
                    "type": "remote",
                    "tag": "geosite-category-ru",
                    "format": "binary",
                    "url": "https://raw.githubusercontent.com/MetaCubeX/meta-rules-dat/sing/geo/geosite/category-ru.srs",
                    "download_detour": "global-hysteria2",
                    "update_interval": "24h",
                },
                {
                    "type": "remote",
                    "tag": "geosite-category-bank-ru",
                    "format": "binary",
                    "url": "https://raw.githubusercontent.com/MetaCubeX/meta-rules-dat/sing/geo/geosite/category-bank-ru.srs",
                    "download_detour": "global-hysteria2",
                    "update_interval": "24h",
                },
                {
                    "type": "remote",
                    "tag": "geosite-category-ecommerce-ru",
                    "format": "binary",
                    "url": "https://raw.githubusercontent.com/MetaCubeX/meta-rules-dat/sing/geo/geosite/category-ecommerce-ru.srs",
                    "download_detour": "global-hysteria2",
                    "update_interval": "24h",
                },
                {
                    "type": "remote",
                    "tag": "geosite-category-entertainment-ru",
                    "format": "binary",
                    "url": "https://raw.githubusercontent.com/MetaCubeX/meta-rules-dat/sing/geo/geosite/category-entertainment-ru.srs",
                    "download_detour": "global-hysteria2",
                    "update_interval": "24h",
                },
                {
                    "type": "remote",
                    "tag": "geosite-category-gov-ru",
                    "format": "binary",
                    "url": "https://raw.githubusercontent.com/MetaCubeX/meta-rules-dat/sing/geo/geosite/category-gov-ru.srs",
                    "download_detour": "global-hysteria2",
                    "update_interval": "24h",
                },
                {
                    "type": "remote",
                    "tag": "geosite-category-media-ru",
                    "format": "binary",
                    "url": "https://raw.githubusercontent.com/MetaCubeX/meta-rules-dat/sing/geo/geosite/category-media-ru.srs",
                    "download_detour": "global-hysteria2",
                    "update_interval": "24h",
                },
                {
                    "type": "remote",
                    "tag": "geosite-category-retail-ru",
                    "format": "binary",
                    "url": "https://raw.githubusercontent.com/MetaCubeX/meta-rules-dat/sing/geo/geosite/category-retail-ru.srs",
                    "download_detour": "global-hysteria2",
                    "update_interval": "24h",
                },
                {
                    "type": "remote",
                    "tag": "geosite-category-travel-ru",
                    "format": "binary",
                    "url": "https://raw.githubusercontent.com/MetaCubeX/meta-rules-dat/sing/geo/geosite/category-travel-ru.srs",
                    "download_detour": "global-hysteria2",
                    "update_interval": "24h",
                },
                {
                    "type": "remote",
                    "tag": "geoip-ru",
                    "format": "binary",
                    "url": "https://raw.githubusercontent.com/MetaCubeX/meta-rules-dat/sing/geo/geoip/ru.srs",
                    "download_detour": "global-hysteria2",
                    "update_interval": "24h",
                },
            ],
            "final": "global-hysteria2",
        },
        "experimental": {
            "cache_file": {
                "enabled": True,
            }
        },
    }

    OUT.write_text(json.dumps(config, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(str(OUT))


if __name__ == "__main__":
    main()
