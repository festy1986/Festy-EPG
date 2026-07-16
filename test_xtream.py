import os
import requests

CHANNEL_FILE = "sports_channels.txt"

XTREAM_URL = os.environ["XTREAM_URL"].rstrip("/")
USERNAME = os.environ["XTREAM_USERNAME"]
PASSWORD = os.environ["XTREAM_PASSWORD"]


print("Loading sports channel list...")

wanted_channels = {}

with open(CHANNEL_FILE, "r", encoding="utf-8") as f:
    for line in f:
        line = line.strip()

        if not line:
            continue

        parts = line.split("|")

        if len(parts) < 2:
            continue

        channel_id = parts[0].strip()
        display_name = " | ".join(parts[1:]).strip()

        wanted_channels[channel_id] = display_name


print(f"Channels requested: {len(wanted_channels)}")


print("Connecting to Xtream...")

url = (
    f"{XTREAM_URL}/player_api.php"
    f"?username={USERNAME}"
    f"&password={PASSWORD}"
    f"&action=get_live_streams"
)


response = requests.get(url, timeout=60)

response.raise_for_status()

channels = response.json()


print(f"Provider channels found: {len(channels)}")


found = []
missing = []


provider_ids = {}

for channel in channels:

    stream_id = str(channel.get("stream_id"))

    provider_ids[stream_id] = channel


for channel_id, name in wanted_channels.items():

    if channel_id in provider_ids:
        found.append((channel_id, name))
    else:
        missing.append((channel_id, name))


print("")
print(f"Matched channels: {len(found)}")
print(f"Missing channels: {len(missing)}")


print("")
print("Sample matches:")

for item in found[:20]:
    print(
        item[0],
        "->",
        item[1]
    )


print("")
print("Sample missing:")

for item in missing[:20]:
    print(
        item[0],
        "->",
        item[1]
    )
