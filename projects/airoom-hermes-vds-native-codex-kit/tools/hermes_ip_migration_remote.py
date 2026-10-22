from pathlib import Path

OLD = "89.40.70.42"
NEW = "78.17.185.85"

FILES = [
    "/srv/hermes/workspace/karing-hysteria2-89.40.70.42-8443.json",
    "/srv/hermes/workspace/hysteria2-ru-8443-karing.json",
    "/srv/hermes/workspace/karing-hysteria2-89.40.70.42-443.yaml",
    "/srv/hermes/workspace/amnezia-wireguard-89.40.70.42-client2.conf",
    "/srv/hermes/workspace/amnezia-vps-connection.md",
    "/srv/hermes/workspace/amnezia-wireguard-89.40.70.42-client2.txt",
    "/srv/hermes/workspace/memory-vault/ops/scripts/Test-HermesUnrealMcpTunnel.ps1",
    "/srv/hermes/workspace/memory-vault/ops/scripts/Watch-HermesUnrealMcpTunnel.ps1",
    "/srv/hermes/workspace/memory-vault/ops/hermes-unreal-mcp-connection.md",
    "/srv/hermes/workspace/memory-vault/ops/vps-service-baseline.md",
]

for name in FILES:
    path = Path(name)
    if not path.exists():
        continue
    text = path.read_text(encoding="utf-8")
    updated = text.replace(OLD, NEW)
    if updated != text:
        path.write_text(updated, encoding="utf-8")
        print(f"updated {path}")

RENAMES = [
    (
        "/srv/hermes/workspace/karing-hysteria2-89.40.70.42-8443.json",
        "/srv/hermes/workspace/karing-hysteria2-78.17.185.85-8443.json",
    ),
    (
        "/srv/hermes/workspace/karing-hysteria2-89.40.70.42-443.yaml",
        "/srv/hermes/workspace/karing-hysteria2-78.17.185.85-443.yaml",
    ),
    (
        "/srv/hermes/workspace/amnezia-wireguard-89.40.70.42-client2.conf",
        "/srv/hermes/workspace/amnezia-wireguard-78.17.185.85-client2.conf",
    ),
    (
        "/srv/hermes/workspace/amnezia-wireguard-89.40.70.42-client2.txt",
        "/srv/hermes/workspace/amnezia-wireguard-78.17.185.85-client2.txt",
    ),
]

for old_name, new_name in RENAMES:
    old_path = Path(old_name)
    new_path = Path(new_name)
    if old_path.exists():
        old_path.replace(new_path)
        print(f"renamed {old_path} -> {new_path}")
