import os
import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone

CHANNEL_FILE = "sports_channels.txt"
OUTPUT_FILE = "guides/sports.xml"

XTREAM_URL = os.environ["XTREAM_URL"].rstrip("/")
USERNAME = os.environ["XTREAM_USERNAME"]
PASSWORD = os.environ["XTREAM_PASSWORD"]


# Provider endpoint correction
if XTREAM_URL.startswith("https://"):
    XTREAM_URL = XTREAM_URL.replace("https://", "http://")

if ":80" not in XTREAM_URL and ":443" not in XTREAM_URL:
    XTREAM_URL += ":80"


os.makedirs("guides", exist_ok=True)


# -----------------------------
# Load selected channels
# -----------------------------

wanted = {}

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

        wanted[channel_id] = display_name


print(f"Requested channels: {len(wanted)}")


# -----------------------------
# Pull provider channels
# -----------------------------

print("Downloading provider channels...")


url = (
    f"{XTREAM_URL}/player_api.php"
    f"?username={USERNAME}"
    f"&password={PASSWORD}"
    f"&action=get_live_streams"
)


response = requests.get(
    url,
    timeout=120,
    headers={
        "User-Agent": "Mozilla/5.0"
    }
)

response.raise_for_status()

provider_channels = response.json()


print(
    f"Provider channels: {len(provider_channels)}"
)


provider_lookup = {}


for channel in provider_channels:

    provider_lookup[
        str(channel.get("stream_id"))
    ] = channel



# -----------------------------
# Build XMLTV
# -----------------------------

tv = ET.Element(
    "tv",
    {
        "generator-info-name": "Festy Sports Guide"
    }
)


matched = 0


for channel_id, display_name in wanted.items():

    if channel_id not in provider_lookup:
        continue

    matched += 1

    channel = ET.SubElement(
        tv,
        "channel",
        {
            "id": channel_id
        }
    )


    name = ET.SubElement(
        channel,
        "display-name"
    )

    name.text = display_name



# Add simple placeholder programming

start = datetime.now(
    timezone.utc
).replace(
    hour=0,
    minute=0,
    second=0,
    microsecond=0
)


for channel_id, display_name in wanted.items():

    if channel_id not in provider_lookup:
        continue


    programme = ET.SubElement(
        tv,
        "programme",
        {
            "start":
                start.strftime("%Y%m%d%H%M%S +0000"),

            "stop":
                (start + timedelta(days=1))
                .strftime("%Y%m%d%H%M%S +0000"),

            "channel":
                channel_id
        }
    )


    title = ET.SubElement(
        programme,
        "title"
    )

    title.text = display_name


    desc = ET.SubElement(
        programme,
        "desc"
    )

    desc.text = display_name



tree = ET.ElementTree(tv)

ET.indent(
    tree,
    space="  "
)

tree.write(
    OUTPUT_FILE,
    encoding="utf-8",
    xml_declaration=True
)


print("")
print("Created:")
print(OUTPUT_FILE)
print(f"Matched channels: {matched}")
