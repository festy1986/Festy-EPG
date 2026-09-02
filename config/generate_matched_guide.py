import os
import re
import html
import time
import requests
import xml.etree.ElementTree as ET

from datetime import datetime, timedelta, timezone


CHANNEL_FILE = "config/matcheverychannel.tx"

OUTPUT_FILE = "guides/matched.xml"

DAYS = 14

BLOCK_HOURS = 2


XTREAM_URL = os.environ["XTREAM_URL"].rstrip("/")

USERNAME = os.environ["XTREAM_USERNAME"]

PASSWORD = os.environ["XTREAM_PASSWORD"]


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
# Load selected channels
# ---------------------------------

wanted = {}


with open(

    CHANNEL_FILE,

    "r",

    encoding="utf-8"

) as file:


    for line in file:


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


        channel_name = parts[3]


        # Skip group header lines

        if (

            "######"

            in channel_name

        ):

            continue


        if not stream_id:

            continue


        # Only accept numeric provider IDs

        if not stream_id.isdigit():

            continue


        if not channel_name:

            continue


        wanted[stream_id] = {

            "channel_name":

            channel_name

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


if not isinstance(streams, list):

    print(

        "Unexpected provider response:"

    )


    print(streams)


    raise SystemExit(1)


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
# Match selected channels
# ---------------------------------

matched_channels = []


for stream_id, data in wanted.items():


    if stream_id not in provider:


        print(

            f"NOT FOUND: "

            f"{stream_id} - "

            f"{data['channel_name']}"

        )


        continue


    provider_data = provider[stream_id]


    provider_name = str(

        provider_data.get(

            "name",

            ""

        )

    ).strip()


    if not provider_name:

        provider_name = data[

            "channel_name"

        ]


    matched_channels.append(

        {

            "stream_id":

            stream_id,


            "channel_name":

            provider_name

        }

    )


print(

    f"Matched channels: "

    f"{len(matched_channels)}"

)


# ---------------------------------
# Build XMLTV
# ---------------------------------

tv = ET.Element(

    "tv",

    {

        "generator-info-name":

        "Matched Provider Guide"

    }

)


# ---------------------------------
# Create channels
# ---------------------------------

for channel_data in matched_channels:


    stream_id = channel_data[

        "stream_id"

    ]


    channel_name = channel_data[

        "channel_name"

    ]


    channel = ET.SubElement(

        tv,

        "channel",

        {

            "id":

            stream_id

        }

    )


    display = ET.SubElement(

        channel,

        "display-name"

    )


    display.text = channel_name


# ---------------------------------
# Generate 14 Days
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


blocks_per_day = 24 // BLOCK_HOURS


total_blocks = DAYS * blocks_per_day


for channel_data in matched_channels:


    stream_id = channel_data[

        "stream_id"

    ]


    channel_name = channel_data[

        "channel_name"

    ]


    current = start_date


    for block in range(

        total_blocks

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


        title.text = channel_name


        desc = ET.SubElement(

            programme,

            "desc"

        )


        desc.text = channel_name


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

    f"{total_blocks}"

)
