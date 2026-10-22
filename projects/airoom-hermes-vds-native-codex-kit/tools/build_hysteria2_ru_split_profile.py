from pathlib import Path


ROOT = Path(r"D:\AI\airoom-hermes-vds-native-codex-kit")
VLESS_RU = ROOT / "vpn-client-configs" / "clash-verge-vless-reality-ru-split.yaml"
HY_CLIENT = ROOT / "vpn-client-configs" / "my-hermes-hysteria2-client.yaml"
OUT = ROOT / "vpn-client-configs" / "clash-verge-hysteria2-ru-split.yaml"


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


def replace_proxies_block(source: str, proxy_block: str) -> str:
    start = source.index("\nproxies:\n") + 1
    end = source.index("\nproxy-groups:\n")
    return source[:start] + proxy_block + source[end + 1 :]


def main() -> None:
    client = read_hysteria_client(HY_CLIENT)
    server, port = client["server"].rsplit(":", 1)
    auth = client["auth"]
    sni = client.get("tls.sni", "222468.com")

    source = VLESS_RU.read_text(encoding="utf-8")
    source = source.replace("Hermes-VLESS-Reality", "Hermes-Hysteria2-Fast")

    proxy_block = f"""proxies:
  - name: Hermes-Hysteria2-Fast
    type: hysteria2
    server: {server}
    port: {port}
    password: {auth}
    sni: {sni}
    skip-cert-verify: true
    udp: true
"""

    result = replace_proxies_block(source, proxy_block)
    OUT.write_text(result, encoding="utf-8")
    print(str(OUT))


if __name__ == "__main__":
    main()
