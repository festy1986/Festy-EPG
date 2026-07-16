import os
import requests

CHANNEL_FILE = "sports_channels.txt"

# -----------------------------
# Xtream Connection
# -----------------------------

XTREAM_URL = os.environ["XTREAM_URL"].rstrip("/")
USERNAME = os.environ["XTREAM_USERNAME"]
PASSWORD = os.environ["XTREAM_PASSWORD"]


# Provider reports HTTP port 80
if XTREAM_URL.startswith("https://"):
    XTREAM_URL = XTREAM_URL.replace("https://", "http://")

if ":80" not in XTREAM_URL and ":443" not in XTREAM_URL:
    XTREAM_URL = XTREAM_URL + ":80"


print("Xtream server:")
print(XTREAM_URL)


# -----------------------------
# Load Sports Channels
# -----------------------------

print("")
print("Loading sports channel list...")


wanted_channels = {}


with open(CHANNEL_FILE, "r", encoding="utf-8") as f:

    for line in f:

        line = line.strip()

        if not line:
            continue

        parts = [
            x.strip()
            for x in line.split("|")
        ]

        if len(parts) < 2:
            continue


        channel_id = parts[0]

        display_name = " ".join(parts[1:])


        wanted_channels[channel_id] = display_name



print(
    f"Channels requested: {len(wanted_channels)}"
)



# -----------------------------
# Test Account API
# -----------------------------

print("")
print("Connecting to Xtream...")


account_url = (
    f"{XTREAM_URL}/player_api.php"
    f"?username={USERNAME}"
    f"&password={PASSWORD}"
)


response = requests.get(
    account_url,
    timeout=60,
    headers={
        "User-Agent": "Mozilla/5.0"
    }
)


print(
    "Account API status:",
    response.status_code
)


print(
    "Response preview:"
)

print(
    response.text[:300]
)


if response.status_code != 200:

    print("")
    print("Account API failed.")
    exit(1)



try:

    account = response.json()

except Exception:

    print("Invalid JSON response")
    exit(1)



print("")
print("Account API OK")



# -----------------------------
# Get Live Streams
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
    timeout=120,
    headers={
        "User-Agent": "Mozilla/5.0"
    }
)



print(
    "Live API status:",
    channels_response.status_code
)



if channels_response.status_code != 200:

    print(
        channels_response.text[:500]
    )

    exit(1)



try:

    channels = channels_response.json()

except Exception:

    print("Live channel response not JSON")

    print(
        channels_response.text[:500]
    )

    exit(1)



print(
    f"Provider channels found: {len(channels)}"
)



# -----------------------------
# Match Selected Channels
# -----------------------------

provider_channels = {}


for channel in channels:

    stream_id = str(
        channel.get("stream_id")
    )

    provider_channels[stream_id] = channel



found = []

missing = []



for channel_id, display_name in wanted_channels.items():

    if channel_id in provider_channels:

        found.append(
            (
                channel_id,
                display_name
            )
        )

    else:

        missing.append(
            (
                channel_id,
                display_name
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


for channel in found[:25]:

    print(
        channel[0],
        "->",
        channel[1]
    )



print("")
print("Sample missing:")


for channel in missing[:25]:

    print(
        channel[0],
        "->",
        channel[1]
    )
