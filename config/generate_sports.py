import os
import requests
import xml.etree.ElementTree as ET

from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import re
import html
import time
from concurrent.futures import ThreadPoolExecutor, as_completed


CHANNEL_FILE = "sports_channels.txt"
OUTPUT_FILE = "guides/sports.xml"


XTREAM_URL = os.environ["XTREAM_URL"].rstrip("/")
USERNAME = os.environ["XTREAM_USERNAME"]
PASSWORD = os.environ["XTREAM_PASSWORD"]


# --------------------------------------------------
# Normalize Xtream URL
# --------------------------------------------------

if XTREAM_URL.startswith("https://"):
    XTREAM_URL = XTREAM_URL.replace(
        "https://",
        "http://",
        1
    )


if ":80" not in XTREAM_URL and ":443" not in XTREAM_URL:
    XTREAM_URL += ":80"


os.makedirs(
    "guides",
    exist_ok=True
)


# --------------------------------------------------
# HTTP session
# --------------------------------------------------

session = requests.Session()


session.headers.update(
    {
        "User-Agent":
        "Mozilla/5.0"
    }
)


# --------------------------------------------------
# Text cleanup
# --------------------------------------------------

def clean_text(text):

    if not text:
        return ""


    text = html.unescape(
        str(text)
    )


    text = re.sub(
        r"<[^>]+>",
        "",
        text
    )


    text = text.replace(
        "\n",
        " "
    )


    text = text.replace(
        "\r",
        " "
    )


    text = re.sub(
        r"\s+",
        " ",
        text
    )


    return text.strip()


# --------------------------------------------------
# Convert 24-hour time to regular time
# --------------------------------------------------

def format_time(dt):

    return dt.strftime(
        "%-I:%M %p"
    )


# --------------------------------------------------
# Normalize matchup separator
# --------------------------------------------------

def normalize_matchup(text):

    if not text:
        return ""


    text = clean_text(
        text
    )


    text = re.sub(
        r"\s+[xX]\s+",
        " vs. ",
        text
    )


    text = re.sub(
        r"\s+@\s+",
        " vs. ",
        text
    )


    text = re.sub(
        r"\s+v\s+",
        " vs. ",
        text,
        flags=re.IGNORECASE
    )


    text = re.sub(
        r"\s+vs\s*\.?\s+",
        " vs. ",
        text,
        flags=re.IGNORECASE
    )


    text = re.sub(
        r"\s+",
        " ",
        text
    )


    return text.strip(
        " -|:;"
    )


# --------------------------------------------------
# Clean provider channel names
# --------------------------------------------------

def clean_channel_name(name):

    name = clean_text(
        name
    )


    # Convert embedded 24-hour times
    # such as 19:30 to 7:30 PM.
    def convert_time(match):

        hour = int(
            match.group(1)
        )


        minute = int(
            match.group(2)
        )


        suffix = (
            "AM"
            if hour < 12
            else "PM"
        )


        display_hour = hour % 12


        if display_hour == 0:
            display_hour = 12


        return (
            f"{display_hour}:"
            f"{minute:02d} "
            f"{suffix}"
        )


    name = re.sub(
        r"\b([01]?\d|2[0-3]):([0-5]\d)\b",
        convert_time,
        name
    )


    # Normalize X between teams
    name = re.sub(
        r"\s+[xX]\s+",
        " vs. ",
        name
    )


    # Normalize @ between teams
    name = re.sub(
        r"\s+@\s+",
        " vs. ",
        name
    )


    # Normalize existing vs variations
    name = re.sub(
        r"\s+vs\s*\.?\s+",
        " vs. ",
        name,
        flags=re.IGNORECASE
    )


    # Clean repeated separators
    name = re.sub(
        r"\s*\|\s*",
        " | ",
        name
    )


    name = re.sub(
        r"\s*;\s*",
        " ; ",
        name
    )


    name = re.sub(
        r"\s+",
        " ",
        name
    )


    return name.strip(
        " -|:;"
    )


# --------------------------------------------------
# Remove provider event metadata
# --------------------------------------------------

def remove_event_metadata(text):

    if not text:
        return ""


    text = clean_text(
        text
    )


    # Everything beginning with Start:
    # is event metadata and is removed
    # from the displayed event title.
    text = re.split(
        r"\bStart\s*:",
        text,
        maxsplit=1,
        flags=re.IGNORECASE
    )[0]


    # Also handle timestamp metadata if
    # the provider uses a different format.
    text = re.split(
        r"\bStop\s*:",
        text,
        maxsplit=1,
        flags=re.IGNORECASE
    )[0]


    text = re.sub(
        r"\s*\|\s*$",
        "",
        text
    )


    text = re.sub(
        r"\s*;\s*$",
        "",
        text
    )


    return normalize_matchup(
        text
    )


# --------------------------------------------------
# Extract provider start timestamp
# --------------------------------------------------

def extract_start_datetime(text):

    if not text:
        return None


    text = clean_text(
        text
    )


    patterns = [

        r"Start\s*:\s*"
        r"(\d{4}-\d{2}-\d{2})"
        r"\s+"
        r"(\d{2}:\d{2}(?::\d{2})?)",

        r"start\s*=\s*"
        r"(\d{4}-\d{2}-\d{2})"
        r"\s+"
        r"(\d{2}:\d{2}(?::\d{2})?)",

        r"(\d{4}-\d{2}-\d{2})"
        r"\s+"
        r"(\d{2}:\d{2}:\d{2})"

    ]


    for pattern in patterns:

        match = re.search(
            pattern,
            text,
            flags=re.IGNORECASE
        )


        if not match:
            continue


        date_part = match.group(
            1
        )


        time_part = match.group(
            2
        )


        if len(time_part) == 5:

            time_part += (
                ":00"
            )


        try:

            return datetime.strptime(
                f"{date_part} "
                f"{time_part}",
                "%Y-%m-%d %H:%M:%S"
            )


        except ValueError:

            continue


    return None


# --------------------------------------------------
# Get server timezone
# --------------------------------------------------

def get_server_timezone():

    url = (
        f"{XTREAM_URL}/player_api.php"
        f"?username={USERNAME}"
        f"&password={PASSWORD}"
    )


    response = session.get(
        url,
        timeout=60
    )


    response.raise_for_status()


    data = response.json()


    server_info = data.get(
        "server_info",
        {}
    )


    timezone_name = server_info.get(
        "timezone"
    )


    if not timezone_name:

        print(
            "Provider did not return a timezone."
        )


        print(
            "Using UTC."
        )


        return "UTC"


    print(
        f"Provider timezone: "
        f"{timezone_name}"
    )


    return timezone_name


# --------------------------------------------------
# Convert provider timestamp to Eastern Time
# --------------------------------------------------

def convert_to_eastern(
    naive_datetime,
    provider_timezone
):

    if not naive_datetime:

        return None


    try:

        source_zone = ZoneInfo(
            provider_timezone
        )


    except Exception:

        print(
            f"Invalid provider timezone: "
            f"{provider_timezone}"
        )


        print(
            "Falling back to UTC."
        )


        source_zone = timezone.utc


    eastern_zone = ZoneInfo(
        "America/New_York"
    )


    source_datetime = (
        naive_datetime
        .replace(
            tzinfo=source_zone
        )
    )


    return source_datetime.astimezone(
        eastern_zone
    )


# --------------------------------------------------
# Load requested channels
# --------------------------------------------------

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
    f"Requested channels: "
    f"{len(wanted)}"
)


# --------------------------------------------------
# Get provider timezone
# --------------------------------------------------

provider_timezone = (
    get_server_timezone()
)


# --------------------------------------------------
# Download provider channels
# --------------------------------------------------

print(
    "Downloading provider channels..."
)


url = (
    f"{XTREAM_URL}/player_api.php"
    f"?username={USERNAME}"
    f"&password={PASSWORD}"
    f"&action=get_live_streams"
)


streams = None


for attempt in range(
    1,
    6
):

    try:

        print(
            f"Downloading provider channels "
            f"(attempt {attempt}/5)..."
        )


        response = session.get(
            url,
            timeout=(30, 600)
        )


        response.raise_for_status()


        streams = response.json()


        break


    except Exception as e:

        print(
            "Download failed:"
        )


        print(
            e
        )


        if attempt < 5:

            time.sleep(
                10
            )


if streams is None:

    print(
        "Unable to download provider channels."
    )


    raise SystemExit(
        1
    )


print(
    f"Provider channels: "
    f"{len(streams)}"
)


provider = {}


for stream in streams:

    stream_id = str(
        stream.get(
            "stream_id"
        )
    )


    provider[stream_id] = stream


# --------------------------------------------------
# Create XMLTV root
# --------------------------------------------------

tv = ET.Element(
    "tv",
    {
        "generator-info-name":
        "Festy Sports Guide"
    }
)


# --------------------------------------------------
# Calculate guide period
# --------------------------------------------------

guide_start = datetime.now(
    timezone.utc
).astimezone(
    ZoneInfo(
        "America/New_York"
    )
).replace(
    hour=0,
    minute=0,
    second=0,
    microsecond=0
)


guide_end = (
    guide_start
    + timedelta(
        days=1
    )
)


# --------------------------------------------------
# Channel creation
# --------------------------------------------------

matched = 0


for channel_id, requested_name in wanted.items():

    if channel_id not in provider:

        continue


    matched += 1


    stream = provider[
        channel_id
    ]


    provider_name = clean_channel_name(
        stream.get(
            "name",
            requested_name
        )
    )


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


    display.text = provider_name
    # --------------------------------------------------
# EPG lookup
# --------------------------------------------------

def get_epg(stream_id):

    epg_url = (
        f"{XTREAM_URL}/player_api.php"
        f"?username={USERNAME}"
        f"&password={PASSWORD}"
        f"&action=get_short_epg"
        f"&stream_id={stream_id}"
        f"&limit=5"
    )


    try:

        response = session.get(
            epg_url,
            timeout=30
        )


        if response.status_code != 200:

            return None


        data = response.json()


        listings = data.get(
            "epg_listings",
            []
        )


        if listings:

            return listings[0]


    except Exception:

        return None


    return None


# --------------------------------------------------
# Build event information
# --------------------------------------------------

def build_event_info(
    stream,
    epg
):

    title_text = ""


    description_text = ""


    start_eastern = None


    # ----------------------------------------------
    # Use provider EPG when it has information
    # ----------------------------------------------

    if epg:

        title_text = clean_text(
            epg.get(
                "title",
                ""
            )
        )


        description_text = clean_text(
            epg.get(
                "description",
                ""
            )
        )


        # If the EPG title itself contains a
        # provider timestamp, extract it.
        start_datetime = (
            extract_start_datetime(
                title_text
            )
        )


        if start_datetime:

            start_eastern = (
                convert_to_eastern(
                    start_datetime,
                    provider_timezone
                )
            )


    # ----------------------------------------------
    # Otherwise use the provider channel name
    # ----------------------------------------------

    if not title_text:

        provider_name = clean_text(
            stream.get(
                "name",
                ""
            )
        )


        title_text = provider_name


        description_text = provider_name


    # ----------------------------------------------
    # Extract actual provider start time
    # ----------------------------------------------

    provider_name = clean_text(
        stream.get(
            "name",
            ""
        )
    )


    if not start_eastern:

        start_datetime = (
            extract_start_datetime(
                provider_name
            )
        )


        if start_datetime:

            start_eastern = (
                convert_to_eastern(
                    start_datetime,
                    provider_timezone
                )
            )


    # ----------------------------------------------
    # Clean event title
    # ----------------------------------------------

    cleaned_title = (
        remove_event_metadata(
            title_text
        )
    )


    # If the EPG title did not contain a
    # usable event title, try the provider name.
    if not cleaned_title:

        cleaned_title = (
            remove_event_metadata(
                provider_name
            )
        )


    # ----------------------------------------------
    # Add actual Eastern start time
    # ----------------------------------------------

    if start_eastern:

        eastern_time = format_time(
            start_eastern
        )


        cleaned_title = (
            f"{cleaned_title} "
            f"({eastern_time})"
        )


    # ----------------------------------------------
    # Clean description
    # ----------------------------------------------

    cleaned_description = (
        remove_event_metadata(
            description_text
        )
    )


    if not cleaned_description:

        cleaned_description = (
            cleaned_title
        )


    return (
        cleaned_title,
        cleaned_description,
        start_eastern
    )


# --------------------------------------------------
# Create all XMLTV channels
# --------------------------------------------------

print(
    "Creating XMLTV channels..."
)


for channel_id, requested_name in wanted.items():

    if channel_id not in provider:

        continue


    stream = provider[
        channel_id
    ]


    provider_name = clean_channel_name(
        stream.get(
            "name",
            requested_name
        )
    )


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


    display.text = provider_name


# --------------------------------------------------
# Create 2-hour programme blocks
# --------------------------------------------------

print(
    "Creating 2-hour programme blocks..."
)


for channel_id, requested_name in wanted.items():

    if channel_id not in provider:

        continue


    stream = provider[
        channel_id
    ]


    print(
        f"Processing {channel_id}"
    )


    epg = get_epg(
        channel_id
    )


    (
        title_text,
        description_text,
        event_time
    ) = build_event_info(
        stream,
        epg
    )


    current_start = guide_start


    while current_start < guide_end:


        current_stop = (
            current_start
            + timedelta(
                hours=2
            )
        )


        if current_stop > guide_end:

            current_stop = (
                guide_end
            )


        programme = ET.SubElement(
            tv,
            "programme",
            {
                "start":
                current_start.strftime(
                    "%Y%m%d%H%M%S %z"
                ),

                "stop":
                current_stop.strftime(
                    "%Y%m%d%H%M%S %z"
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


        desc.text = description_text


        current_start = (
            current_stop
        )


# --------------------------------------------------
# Save XMLTV file
# --------------------------------------------------

print(
    "Writing XMLTV file..."
)


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


print(
    ""
)


print(
    "Created:"
)


print(
    OUTPUT_FILE
)


print(
    f"Matched channels: "
    f"{matched}"
)


print(
    "Guide blocks: "
    "2 hours each"
)
