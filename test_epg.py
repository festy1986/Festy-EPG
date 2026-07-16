import os
import requests
import json

CHANNEL_FILE = "sports_channels.txt"

XTREAM_URL = os.environ["XTREAM_URL"].rstrip("/")
USERNAME = os.environ["XTREAM_USERNAME"]
PASSWORD = os.environ["XTREAM_PASSWORD"]


# -----------------------------
# Normalize URL
# -----------------------------

if XTREAM_URL.startswith("https://"):
    XTREAM_URL = XTREAM_URL.replace("https://", "http://")

if ":80" not in XTREAM_URL and ":443" not in XTREAM_URL:
    XTREAM_URL += ":80"


# -----------------------------
# Load one test channel
# -----------------------------

test_channel = None


with open(CHANNEL_FILE, "r", encoding="utf-8") as f:

    for line in f:

        line = line.strip()

        if not line:
            continue

        parts = [
            x.strip()
            for x in line.split("|")
        ]

        if len(parts) >= 2:
            test_channel = parts[0]
            test_name = " ".join(parts[1:])
            break


if not test_channel:
    print("No channel found")
    exit(1)


print("Testing channel:")
print(test_channel)
print(test_name)


# -----------------------------
# Get short EPG
# -----------------------------

epg_url = (
    f"{XTREAM_URL}/player_api.php"
    f"?username={USERNAME}"
    f"&password={PASSWORD}"
    f"&action=get_short_epg"
    f"&stream_id={test_channel}"
    f"&limit=5"
)


print("")
print("Connecting to EPG...")


response = requests.get(
    epg_url,
    timeout=60,
    headers={
        "User-Agent": "Mozilla/5.0"
    }
)


print(
    "EPG status:",
    response.status_code
)


print("")
print("Response preview:")
print(
    response.text[:1000]
)


if response.status_code != 200:
    exit(1)


try:

    data = response.json()

except Exception:

    print("")
    print("Provider did not return JSON")
    exit(1)



print("")
print("JSON OK")


print("")
print(
    json.dumps(
        data,
        indent=2
    )[:3000]
)
