from pathlib import Path


ROOT = Path(r"D:\AI\airoom-hermes-vds-native-codex-kit")
HY_CLIENT = ROOT / "vpn-client-configs" / "my-hermes-hysteria2-client.yaml"
OUT = ROOT / "vpn-client-configs" / "karing-hysteria2-ru-simple.yaml"


RU_DIRECT_DOMAINS = [
    "local",
    "ru",
    "su",
    "xn--p1ai",
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


DIRECT_IP_RULES = [
    "IP-CIDR,10.0.0.0/8,DIRECT,no-resolve",
    "IP-CIDR,172.16.0.0/12,DIRECT,no-resolve",
    "IP-CIDR,192.168.0.0/16,DIRECT,no-resolve",
    "IP-CIDR,127.0.0.0/8,DIRECT,no-resolve",
]


def read_hysteria_client(path: Path) -> dict[str, str]:
    data: dict[str, str] = {}
    section = ""
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.rstrip()
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if not line.startswith(" ") and stripped.endswith(":"):
            section = stripped[:-1]
            continue
        if ":" not in stripped:
            continue
        key, value = stripped.split(":", 1)
        value = value.strip().strip('"').strip("'")
        if section == "tls":
            data[f"tls.{key.strip()}"] = value
        elif not line.startswith(" "):
            data[key.strip()] = value
    return data


def main() -> None:
    client = read_hysteria_client(HY_CLIENT)
    server, port = client["server"].rsplit(":", 1)
    auth = client["auth"]
    sni = client.get("tls.sni", "222468.com")

    domain_rules = "\n".join(f"  - DOMAIN-SUFFIX,{domain},DIRECT" for domain in RU_DIRECT_DOMAINS)
    ip_rules = "\n".join(f"  - {rule}" for rule in DIRECT_IP_RULES)

    profile = f"""mixed-port: 7890
allow-lan: false
mode: rule
log-level: info
ipv6: false

dns:
  enable: true
  ipv6: false
  default-nameserver:
    - 1.1.1.1
    - 8.8.8.8
  nameserver:
    - https://cloudflare-dns.com/dns-query
    - https://dns.google/dns-query

proxies:
  - name: Hermes-Hysteria2-Fast
    type: hysteria2
    server: {server}
    port: {port}
    password: {auth}
    sni: {sni}
    skip-cert-verify: true
    udp: true

proxy-groups:
  - name: PROXY
    type: select
    proxies:
      - Hermes-Hysteria2-Fast
      - DIRECT

rules:
  - DOMAIN,ipv6-internet.yandex.net,REJECT
{ip_rules}
{domain_rules}
  - MATCH,PROXY
"""

    OUT.write_text(profile, encoding="utf-8")
    print(str(OUT))


if __name__ == "__main__":
    main()
