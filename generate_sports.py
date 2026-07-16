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

    remove = [
        "NO EVENT STREAMING NOW",
        "EXCLUSIVE",
        "NEXT",
        "STREAM",
        "GMT"
    ]

    for word in remove:
        name = name.replace(word, "")

    name = re.sub(
        r"\s+",
        " ",
        name
    )

    return name.strip(" -|:")



# -----------------------------
# Load requested channels
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
# Get provider channels
# -----------------------------

print("Downloading provider channels...")


streams_url = (
    f"{XTREAM_URL}/player_api.php"
    f"?username={USERNAME}"
    f"&password={PASSWORD}"
    f"&action=get_live_streams"
)


streams = requests.get(
    streams_url,
    timeout=120
).json()



provider = {}


for stream in streams:

    provider[
        str(stream.get("stream_id"))
    ] = stream



print(
    f"Provider channels: {len(provider)}"
)



# -----------------------------
# XMLTV setup
# -----------------------------

tv = ET.Element(
    "tv",
    {
        "generator-info-name":
        "Festy Sports Guide"
    }
)



start = datetime.now(
    timezone.utc
).replace(
    hour=0,
    minute=0,
    second=0,
    microsecond=0
)



# -----------------------------
# Build channels
# -----------------------------

for channel_id, display_name in wanted.items():

    if channel_id not in provider:
        continue


    ch = ET.SubElement(
        tv,
        "channel",
        {
            "id": channel_id
        }
    )


    name = ET.SubElement(
        ch,
        "display-name"
    )


    # This is what TiviMate sees
    name.text = display_name



# -----------------------------
# Build programs
# -----------------------------

for channel_id, display_name in wanted.items():

    if channel_id not in provider:
        continue


    stream = provider[channel_id]


    provider_name = clean_event_name(
        stream.get("name", "")
    )


    title_text = provider_name

    desc_text = provider_name


    # One day placeholder until EPG pull is added
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

    title.text = title_text



    desc = ET.SubElement(
        programme,
        "desc"
    )

    desc.text = desc_text



# -----------------------------
# Save
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
