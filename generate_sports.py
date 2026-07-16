import os
import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
import re
import html

CHANNEL_FILE = "sports_channels.txt"
OUTPUT_FILE = "guides/sports.xml"

XTREAM_URL = os.environ["XTREAM_URL"].rstrip("/")
USERNAME = os.environ["XTREAM_USERNAME"]
PASSWORD = os.environ["XTREAM_PASSWORD"]


# -----------------------------
# Normalize provider URL
# -----------------------------

if XTREAM_URL.startswith("https://"):
    XTREAM_URL = XTREAM_URL.replace("https://", "http://")

if ":80" not in XTREAM_URL and ":443" not in XTREAM_URL:
    XTREAM_URL += ":80"


os.makedirs("guides", exist_ok=True)


# -----------------------------
# Helpers
# -----------------------------

def clean_text(text):
    if not text:
        return ""

    text = html.unescape(text)
    text = re.sub("<.*?>", "", text)
    text = text.replace("\n", " ")

    return text.strip()


def clean_event_name(name):

    name = clean_text(name)

    remove_words = [
        "NO EVENT STREAMING NOW",
        "EXCLUSIVE",
        "NEXT",
        "STREAM",
        "GMT"
    ]

    for word in remove_words:
        name = name.replace(word, "")

    name = re.sub(
        r"\s+",
        " ",
        name
    )

    return name.strip(" -|:")


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


print(
    f"Requested channels: {len(wanted)}"
)


# -----------------------------
# Download provider channels
# -----------------------------

print("Downloading provider channels...")


streams_url = (
    f"{XTREAM_URL}/player_api.php"
    f"?username={USERNAME}"
    f"&password={PASSWORD}"
    f"&action=get_live_streams"
)


streams_response = requests.get(
    streams_url,
    timeout=120,
    headers={
        "User-Agent": "Mozilla/5.0"
    }
)


print(
    "Live API status:",
    streams_response.status_code
)


if streams_response.status_code != 200:

    print(
        streams_response.text[:500]
    )

    exit(1)


try:

    streams = streams_response.json()

except Exception:

    print("Provider returned invalid JSON")

    print(
        streams_response.text[:500]
    )

    exit(1)



print(
    f"Provider channels: {len(streams)}"
)



provider = {}


for stream in streams:

    provider[
        str(stream.get("stream_id"))
    ] = stream



# -----------------------------
# Create XMLTV
# -----------------------------

tv = ET.Element(
    "tv",
    {
        "generator-info-name":
        "Festy Sports Guide"
    }
)



matched = 0



for channel_id, display_name in wanted.items():

    if channel_id not in provider:
        continue

    matched += 1


    channel = ET.SubElement(
        tv,
        "channel",
        {
            "id": channel_id
        }
    )


    display = ET.SubElement(
        channel,
        "display-name"
    )


    # TiviMate assignment name
    display.text = display_name



# -----------------------------
# Temporary event data
# -----------------------------

start = datetime.now(
    timezone.utc
).replace(
    hour=0,
    minute=0,
    second=0,
    microsecond=0
)



for channel_id, display_name in wanted.items():

    if channel_id not in provider:
        continue


    stream = provider[channel_id]


    event = clean_event_name(
        stream.get("name", "")
    )


    if not event:
        event = display_name



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

    title.text = event



    desc = ET.SubElement(
        programme,
        "desc"
    )

    desc.text = event



# -----------------------------
# Save file
# -----------------------------

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
print(
    f"Matched channels: {matched}"
)
