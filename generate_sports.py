import os
import re
import html
import time
import requests
import xml.etree.ElementTree as ET

from datetime import datetime, timedelta, timezone
from concurrent.futures import ThreadPoolExecutor, as_completed


CHANNEL_FILE = "sports_channels.txt"
OUTPUT_FILE = "guides/sports.xml"

XTREAM_URL = os.environ["XTREAM_URL"].rstrip("/")
USERNAME = os.environ["XTREAM_USERNAME"]
PASSWORD = os.environ["XTREAM_PASSWORD"]


# ---------------------------------
# Normalize Xtream URL
# ---------------------------------

if XTREAM_URL.startswith("https://"):
    XTREAM_URL = XTREAM_URL.replace("https://", "http://")

if ":80" not in XTREAM_URL and ":443" not in XTREAM_URL:
    XTREAM_URL += ":80"


os.makedirs(
    "guides",
    exist_ok=True
)


session = requests.Session()

session.headers.update(
    {
        "User-Agent": "Mozilla/5.0"
    }
)



# ---------------------------------
# Cleaning helpers
# ---------------------------------

def clean_text(text):

    if not text:
        return ""

    text = html.unescape(
        str(text)
    )

    text = re.sub(
        r"<.*?>",
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



def convert_military_time(text):

    def replace(match):

        hour = int(
            match.group(1)
        )

        minute = match.group(2)

        suffix = "AM"

        if hour >= 12:
            suffix = "PM"

        hour12 = hour % 12

        if hour12 == 0:
            hour12 = 12

        return f"{hour12}:{minute} {suffix}"


    return re.sub(
        r"\b(\d{1,2}):(\d{2})\b",
        replace,
        text
    )



def remove_provider_noise(text):

    remove_words = [
        "NO EVENT STREAMING NOW",
        "EXCLUSIVE",
        "UPCOMING",
        "NEXT",
        "STREAM",
        "LIVE",
        "FHD",
        "HD",
        "4K",
        "UHD",
        "GMT"
    ]


    for word in remove_words:

        text = re.sub(
            r"\b" + re.escape(word) + r"\b",
            "",
            text,
            flags=re.I
        )


    # remove dates
    text = re.sub(
        r"\b\d{4}-\d{2}-\d{2}\b",
        "",
        text
    )


    text = re.sub(
        r"\s+",
        " ",
        text
    )


    return text.strip(
        " -|:"
    )



# ---------------------------------
# Channel/event splitter
# ---------------------------------

def split_channel_event(provider_name):

    name = clean_text(
        provider_name
    )


    patterns = [

        r"^(MLB\s*\d+)\s+(.*)",
        r"^(NHL\s*\d+)\s+(.*)",
        r"^(NBA\s*\d+)\s+(.*)",
        r"^(NFL\s*\d+)\s+(.*)",
        r"^(MLS\s*\d+)\s+(.*)",

    ]


    for pattern in patterns:

        match = re.match(
            pattern,
            name,
            flags=re.I
        )

        if match:

            channel = match.group(1).strip()

            event = match.group(2).strip()


            return (
                channel,
                convert_military_time(
                    remove_provider_noise(event)
                )
            )


    return (
        name,
        convert_military_time(
            remove_provider_noise(name)
        )
    )
    # ---------------------------------
# Xtream EPG lookup
# ---------------------------------

def get_epg(stream_id):

    url = (
        f"{XTREAM_URL}/player_api.php"
        f"?username={USERNAME}"
        f"&password={PASSWORD}"
        f"&action=get_short_epg"
        f"&stream_id={stream_id}"
        f"&limit=1"
    )


    for attempt in range(3):

        try:

            response = session.get(
                url,
                timeout=30
            )


            if response.status_code != 200:
                continue


            data = response.json()


            listings = data.get(
                "epg_listings",
                []
            )


            if listings:

                return listings[0]


        except Exception:

            pass


        time.sleep(2)


    return None



# ---------------------------------
# Load sports channel list
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


for attempt in range(1,6):

    try:

        print(
            f"Downloading provider channels (attempt {attempt}/5)..."
        )


        response = session.get(
            streams_url,
            timeout=(30,300)
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
    f"Provider channels: {len(streams)}"
)



provider = {}


for stream in streams:

    provider[
        str(stream.get("stream_id"))
    ] = stream



# ---------------------------------
# Concurrent EPG downloads
# ---------------------------------

epg_results = {}


print(
    "Downloading EPG data..."
)


with ThreadPoolExecutor(
    max_workers=20
) as executor:


    jobs = {}


    for channel_id in wanted:

        if channel_id in provider:

            jobs[
                executor.submit(
                    get_epg,
                    channel_id
                )
            ] = channel_id



    for future in as_completed(jobs):

        channel_id = jobs[future]


        try:

            epg_results[channel_id] = future.result()


        except Exception:

            epg_results[channel_id] = None



print(
    "EPG download complete"
)



# ---------------------------------
# Build XML
# ---------------------------------

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


channel_display = {}



# ---------------------------------
# Create channels
# ---------------------------------

for channel_id, fallback_name in wanted.items():


    if channel_id not in provider:

        continue



    matched += 1


    provider_name = clean_text(
        provider[channel_id].get(
            "name",
            ""
        )
    )


    clean_channel, _ = split_channel_event(
        provider_name
    )


    channel_display[channel_id] = clean_channel



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


    # TiviMate sees this
    display.text = clean_channel
    # ---------------------------------
# Create programmes
# ---------------------------------

for channel_id, fallback_name in wanted.items():

    if channel_id not in provider:
        continue


    provider_name = provider[channel_id].get(
        "name",
        ""
    )


    epg = epg_results.get(
        channel_id
    )


    title_text = ""
    desc_text = ""


    # ---------------------------------
    # Keep real provider EPG untouched
    # ---------------------------------

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


    # ---------------------------------
    # No EPG: parse provider name
    # ---------------------------------

    if not title_text:

        _, event = split_channel_event(
            provider_name
        )


        title_text = event

        desc_text = event



    # Last fallback

    if not title_text:

        title_text = channel_display.get(
            channel_id,
            fallback_name
        )

        desc_text = title_text



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
    f"Matched channels: {matched}"
)
