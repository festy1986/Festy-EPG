import os
import requests

CHANNEL_FILE = "sports_channels.txt"

XTREAM_URL = os.environ["XTREAM_URL"].rstrip("/")
USERNAME = os.environ["XTREAM_USERNAME"]
PASSWORD = os.environ["XTREAM_PASSWORD"]


# -----------------------------
# Load selected channels
# -----------------------------

print("Loading sports channel list...")

wanted_channels = {}

with open(CHANNEL_FILE, "r", encoding="utf-8") as f:
    for line in f:

        line = line.strip()

        if not line:
            continue

        parts = [x.strip() for x in line.split("|")]

        if len(parts) < 2:
            continue

        channel_id = parts[0]

        display_name = " ".join(parts[1:])

        wanted_channels[channel_id] = display_name


print(f"Channels requested: {len(wanted_channels)}")


# -----------------------------
# Xtream API Test
# -----------------------------

print("")
print("Connecting to Xtream...")


api_url = (
    f"{XTREAM_URL}/player_api.php"
    f"?username={USERNAME}"
    f"&password={PASSWORD}"
)


print("Testing account API...")


response = requests.get(
    api_url,
    timeout=60
)


print("API Status:", response.status_code)

print("Response Preview:")
print(response.text[:500])


if response.status_code != 200:
    print("")
    print("Provider did not return a valid response.")
    exit(1)


try:
    account = response.json()

except Exception:

    print("")
    print("Response was not JSON.")
    exit(1)


print("")
print("Account API OK")


# -----------------------------
# Get Live Channels
# -----------------------------

print("")
print("Downloading live channels...")


channels_url = (
    f"{XTREAM_URL}/player_api.php"
    f"?username={USERNAME}"
    f"&password={PASSWORD}"
    f"&action=get_live_streams"
)


channels_response = requests.get(
    channels_url,
    timeout=120
)


print(
    "Live channel API status:",
    channels_response.status_code
)


if channels_response.status_code != 200:

    print(channels_response.text[:500])
    exit(1)


try:

    channels = channels_response.json()

except Exception:

    print("Live channel response was not JSON")
    print(channels_response.text[:500])
    exit(1)


print(
    f"Provider channels found: {len(channels)}"
)


# -----------------------------
# Match channels
# -----------------------------

provider_ids = {}


for channel in channels:

    stream_id = str(
        channel.get("stream_id")
    )

    provider_ids[stream_id] = channel



found = []
missing = []


for channel_id, name in wanted_channels.items():

    if channel_id in provider_ids:

        found.append(
            (
                channel_id,
                name
            )
        )

    else:

        missing.append(
            (
                channel_id,
                name
            )
        )


print("")
print(
    f"Matched channels: {len(found)}"
)

print(
    f"Missing channels: {len(missing)}"
)


print("")
print("Sample matches:")


for item in found[:25]:

    print(
        item[0],
        "->",
        item[1]
    )


print("")
print("Sample missing:")


for item in missing[:25]:

    print(
        item[0],
        "->",
        item[1]
    )
