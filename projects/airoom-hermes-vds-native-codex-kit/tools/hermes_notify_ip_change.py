import os
import sys
import urllib.parse
import urllib.request

token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
allowed = os.environ.get("TELEGRAM_ALLOWED_USERS", "").strip()

if not token or not allowed:
    print("missing telegram config")
    sys.exit(1)

message = (
    "Hermes VDS IP changed: 78.17.185.85. "
    "Old 89.40.70.42 is stale. SSH/VPN/Hermes references were updated."
)

for raw_chat_id in allowed.split(","):
    chat_id = raw_chat_id.strip()
    if not chat_id:
        continue
    data = urllib.parse.urlencode({"chat_id": chat_id, "text": message}).encode()
    request = urllib.request.Request(
        f"https://api.telegram.org/bot{token}/sendMessage",
        data=data,
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=20) as response:
        if response.status != 200:
            raise RuntimeError(f"send failed for {chat_id}: {response.status}")
    print(f"sent:{chat_id}")
