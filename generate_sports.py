import os
import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
import re
import html
import time


CHANNEL_FILE = "sports_channels.txt"
OUTPUT_FILE = "guides/sports.xml"


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



os.makedirs(
    "guides",
    exist_ok=True
)



# -----------------------------
# Helpers
# -----------------------------

def clean_text(text):

    if not text:
        return ""

    text = html.unescape(text)

    text = re.sub(
        "<.*?>",
        "",
        text
    )

    text = text.replace(
        "\n",
        " "
    )

    return re.sub(
        r"\s+",
        " ",
        text
    ).strip()



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
        name = name.replace(
            word,
            ""
        )


    name = re.sub(
        r"\s+",
        " ",
        name
    )


    return name.strip(
        " -|:"
    )



def get_epg(stream_id):

    url = (
        f"{XTREAM_URL}/player_api.php"
        f"?username={USERNAME}"
        f"&password={PASSWORD}"
        f"&action=get_short_epg"
        f"&stream_id={stream_id}"
        f"&limit=5"
    )


    try:

        r = requests.get(
            url,
            timeout=30,
            headers={
                "User-Agent":
                "Mozilla/5.0"
            }
        )


        if r.status_code != 200:
            return None


        data = r.json()


        listings = data.get(
            "epg_listings",
            []
        )


        if listings:
            return listings[0]


    except Exception:

        return None



    return None




# -----------------------------
# Load channels
# -----------------------------

wanted = {}


with open(
    CHANNEL_FILE,
    "r",
    encoding="utf-8"
) as f:


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


        display_name = " ".join(
            parts[1:]
        )


        wanted[channel_id] = display_name



print(
    f"Requested channels: {len(wanted)}"
)



# -----------------------------
# Provider channels
# -----------------------------

print(
    "Downloading provider channels..."
)


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
        "User-Agent":
        "Mozilla/5.0"
    }
)


response.raise_for_status()



streams = response.json()



provider = {}


for stream in streams:

    provider[
        str(stream.get("stream_id"))
    ] = stream



print(
    f"Provider channels: {len(provider)}"
)




# -----------------------------
# XMLTV
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



matched = 0



# -----------------------------
# Channels
# -----------------------------

for channel_id, display_name in wanted.items():


    if channel_id not in provider:
        continue


    matched += 1


    channel = ET.SubElement(
        tv,
        "channel",
        {
            "id":
            channel_id
        }
    )


    display = ET.SubElement(
        channel,
        "display-name"
    )


    # TiviMate assignment name
    display.text = display_name




# -----------------------------
# Program data
# -----------------------------

for channel_id, display_name in wanted.items():


    if channel_id not in provider:
        continue


    stream = provider[channel_id]


    title_text = None
    desc_text = None



    # First choice:
    # Real provider EPG

    epg = get_epg(
        channel_id
    )


    if epg:


        title_text = clean_text(
            epg.get(
                "title"
            )
        )


        desc_text = clean_text(
            epg.get(
                "description"
            )
        )



    # Fallback:
    # Use provider channel name

    if not title_text:


        title_text = clean_event_name(
            stream.get(
                "name",
                ""
            )
        )


        desc_text = title_text



    if not title_text:

        title_text = display_name
        desc_text = display_name




    programme = ET.SubElement(
        tv,
        "programme",
        {
            "start":
            start.strftime(
                "%Y%m%d%H%M%S +0000"
            ),

            "stop":
            (
                start +
                timedelta(days=1)
            ).strftime(
                "%Y%m%d%H%M%S +0000"
            ),

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



    # Avoid hammering provider

    time.sleep(
        0.05
    )




# -----------------------------
# Save
# -----------------------------

tree = ET.ElementTree(
    tv
)


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
print(
    "Created:"
)

print(
    OUTPUT_FILE
)

print(
    f"Matched channels: {matched}"
)
