import os
import re
import html
import time
import requests
import xml.etree.ElementTree as ET

from datetime import datetime, timedelta, timezone


CHANNEL_FILE = "config/channels.txt"
OUTPUT_FILE = "guides/24-7.xml"

XTREAM_URL = os.environ["XTREAM_URL"].rstrip("/")
USERNAME = os.environ["XTREAM_USERNAME"]
PASSWORD = os.environ["XTREAM_PASSWORD"]

DAYS = 14
BLOCK_HOURS = 2


# ---------------------------------
# Normalize Xtream URL
# ---------------------------------

if XTREAM_URL.startswith("https://"):

    XTREAM_URL = XTREAM_URL.replace(
        "https://",
        "http://"
    )


if ":80" not in XTREAM_URL and ":443" not in XTREAM_URL:

    XTREAM_URL += ":80"


# ---------------------------------
# Create guides folder
# ---------------------------------

os.makedirs(
    "guides",
    exist_ok=True
)


# ---------------------------------
# Session
# ---------------------------------

session = requests.Session()

session.headers.update(
    {
        "User-Agent": "Mozilla/5.0"
    }
)


# ---------------------------------
# Clean channel name
# ---------------------------------

def clean_channel_name(name):

    if not name:

        return ""


    name = html.unescape(
        str(name)
    )


    name = re.sub(
        r"<.*?>",
        "",
        name
    )


    name = name.strip()


    # Remove country prefix

    name = re.sub(
        r"^(US|UK|CA|AU|EXYU):\s*",
        "",
        name,
        flags=re.IGNORECASE
    )


    # Remove 24/7 prefix

    name = re.sub(
        r"^24/7\s*[:\-]?\s*",
        "",
        name,
        flags=re.IGNORECASE
    )


    # Remove RAW marker

    name = name.replace(
        "ᴿᴬᵂ",
        ""
    )


    # Remove 60 FPS marker

    name = name.replace(
        "⁶⁰ᶠᵖˢ",
        ""
    )


    # Normalize whitespace

    name = re.sub(
        r"\s+",
        " ",
        name
    )


    return name.strip()


# ---------------------------------
# Load channels.txt
# ---------------------------------

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


        if len(parts) < 4:

            continue


        stream_id = parts[0]

        original_name = parts[3]


        if not stream_id:

            continue


        cleaned_name = clean_channel_name(
            original_name
        )


        if not cleaned_name:

            continue


        wanted[stream_id] = {

            "original_name":
            original_name,

            "cleaned_name":
            cleaned_name

        }


print(
    f"Requested channels: "
    f"{len(wanted)}"
)


# ---------------------------------
# Download provider channels
# ---------------------------------

streams_url = (

    f"{XTREAM_URL}/player_api.php"

    f"?username={USERNAME}"

    f"&password={PASSWORD}"

    f"&action=get_live_streams"

)


streams = None


for attempt in range(1, 6):

    try:


        print(

            f"Downloading provider channels "

            f"(attempt {attempt}/5)..."

        )


        response = session.get(

            streams_url,

            timeout=(30, 300)

        )


        response.raise_for_status()


        streams = response.json()


        break


    except Exception as e:


        print(e)


        time.sleep(10)


if streams is None:

    raise SystemExit(

        "Provider download failed"

    )


print(

    f"Provider channels: "

    f"{len(streams)}"

)


# ---------------------------------
# Index provider channels
# ---------------------------------

provider = {}


for stream in streams:


    stream_id = str(

        stream.get(

            "stream_id",

            ""

        )

    )


    if stream_id:


        provider[stream_id] = stream


# ---------------------------------
# Match requested channels
# ---------------------------------

matched_channels = []


for stream_id, data in wanted.items():


    if stream_id not in provider:


        print(

            f"NOT FOUND: "

            f"{stream_id} - "

            f"{data['cleaned_name']}"

        )


        continue


    matched_channels.append(

        {

            "stream_id":

            stream_id,


            "original_name":

            data["original_name"],


            "cleaned_name":

            data["cleaned_name"],


            "provider_name":

            provider[stream_id].get(

                "name",

                ""

            )

        }

    )


print(

    f"Matched channels: "

    f"{len(matched_channels)}"

)


# ---------------------------------
# Build XML
# ---------------------------------

tv = ET.Element(

    "tv",

    {

        "generator-info-name":

        "24/7"

    }

)


# ---------------------------------
# Create channels
# ---------------------------------

for channel_data in matched_channels:


    stream_id = channel_data[

        "stream_id"

    ]


    cleaned_name = channel_data[

        "cleaned_name"

    ]


    original_name = channel_data[

        "original_name"

    ]


    channel = ET.SubElement(

        tv,

        "channel",

        {

            "id":

            stream_id

        }

    )


    # Clean name shown in guide

    display = ET.SubElement(

        channel,

        "display-name"

    )


    display.text = cleaned_name


    # Original provider name remains
    # available as an alternate name
    # for matching purposes

    if original_name != cleaned_name:


        display_original = ET.SubElement(

            channel,

            "display-name"

        )


        display_original.text = original_name


# ---------------------------------
# Generate Programming
# 14 Days / 336 Hours
# 2 Hour Blocks
# ---------------------------------

start_date = datetime.now(

    timezone.utc

).replace(

    hour=0,

    minute=0,

    second=0,

    microsecond=0

)


for channel_data in matched_channels:


    stream_id = channel_data[

        "stream_id"

    ]


    cleaned_name = channel_data[

        "cleaned_name"

    ]


    current = start_date


    # 14 days × 12 blocks per day
    # = 168 total 2-hour blocks

    for block in range(
        DAYS * 24 // BLOCK_HOURS
    ):


        stop = current + timedelta(

            hours=BLOCK_HOURS

        )


        programme = ET.SubElement(

            tv,

            "programme",

            {

                "start":

                current.strftime(

                    "%Y%m%d%H%M%S +0000"

                ),


                "stop":

                stop.strftime(

                    "%Y%m%d%H%M%S +0000"

                ),


                "channel":

                stream_id

            }

        )


        title = ET.SubElement(

            programme,

            "title"

        )


        title.text = cleaned_name


        desc = ET.SubElement(

            programme,

            "desc"

        )


        desc.text = cleaned_name


        current = stop


# ---------------------------------
# Save XML
# ---------------------------------

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

    f"Channels: "

    f"{len(matched_channels)}"

)


print(

    f"Days: "

    f"{DAYS}"

)


print(

    f"Hours: "

    f"{DAYS * 24}"

)


print(

    f"Block size: "

    f"{BLOCK_HOURS} hours"

)


print(

    f"Programmes per channel: "

    f"{DAYS * 24 // BLOCK_HOURS}"

)
