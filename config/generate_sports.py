import os
import requests
import xml.etree.ElementTree as ET

from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import re
import html
import time


CHANNEL_FILE = "config/sports_channels.txt"
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
# Public API statistics
# --------------------------------------------------

public_api_lookups = 0
public_api_matches = 0
verified_public_times_used = 0
provider_fallbacks = 0
no_public_match = 0


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


    name = re.sub(
        r"\s+[xX]\s+",
        " vs. ",
        name
    )


    name = re.sub(
        r"\s+@\s+",
        " vs. ",
        name
    )


    name = re.sub(
        r"\s+vs\s*\.?\s+",
        " vs. ",
        name,
        flags=re.IGNORECASE
    )


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


    text = re.split(
        r"\bStart\s*:",
        text,
        maxsplit=1,
        flags=re.IGNORECASE
    )[0]


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
# Extract matchup parts
# --------------------------------------------------

def matchup_parts(text):

    text = remove_event_metadata(
        text
    )


    parts = re.split(
        r"\s+vs\.\s+",
        text,
        maxsplit=1,
        flags=re.IGNORECASE
    )


    if len(parts) != 2:

        return []


    return [

        parts[0].strip(),

        parts[1].strip()

    ]


# --------------------------------------------------
# Normalize team names for matching
# --------------------------------------------------

def normalize_team_name(text):

    text = clean_text(
        text
    ).lower()


    text = re.sub(
        r"[^a-z0-9 ]",
        " ",
        text
    )


    stop_words = {

        "live",
        "hd",
        "sd",
        "fhd",
        "4k",
        "channel",
        "tv",
        "network",
        "sports",
        "sport",
        "event",
        "game",
        "match",
        "today",
        "tomorrow"

    }


    words = [

        word

        for word in text.split()

        if word not in stop_words

    ]


    return " ".join(
        words
    )


# --------------------------------------------------
# Team name matching
# --------------------------------------------------

def team_matches(
    wanted_team,
    actual_team
):

    wanted_team = normalize_team_name(
        wanted_team
    )


    actual_team = normalize_team_name(
        actual_team
    )


    if not wanted_team or not actual_team:

        return False


    if (
        wanted_team in actual_team
        or actual_team in wanted_team
    ):

        return True


    wanted_words = set(
        wanted_team.split()
    )


    actual_words = set(
        actual_team.split()
    )


    return bool(
        wanted_words
        and actual_words
        and (
            wanted_words
            &
            actual_words
        )
    )


# --------------------------------------------------
# Public schedule lookup
# --------------------------------------------------

def get_public_events(
    date_value
):

    global public_api_lookups


    public_api_lookups += 1


    date_text = date_value.strftime(
        "%Y-%m-%d"
    )


    url = (
        "https://www.thesportsdb.com/"
        "api/v1/json/123/eventsday.php"
    )


    try:

        response = session.get(
            url,
            params={
                "d":
                date_text
            },
            timeout=30
        )


        if response.status_code != 200:

            return []


        data = response.json()


        return data.get(
            "events",
            []
        ) or []


    except Exception as e:

        print(
            "Public schedule lookup failed:"
        )


        print(
            e
        )


        return []


# --------------------------------------------------
# Find verified public event
# --------------------------------------------------

def find_public_event(
    provider_matchup,
    preferred_date
):

    global public_api_matches


    parts = matchup_parts(
        provider_matchup
    )


    if len(parts) != 2:

        return None


    search_dates = [

        preferred_date,

        preferred_date
        - timedelta(
            days=1
        ),

        preferred_date
        + timedelta(
            days=1
        ),

        preferred_date
        + timedelta(
            days=2
        )

    ]


    for date_value in search_dates:

        events = get_public_events(
            date_value
        )


        for event in events:

            home_team = clean_text(
                event.get(
                    "strHomeTeam",
                    ""
                )
            )


            away_team = clean_text(
                event.get(
                    "strAwayTeam",
                    ""
                )
            )


            if not home_team or not away_team:

                continue


            direct_match = (

                team_matches(
                    parts[0],
                    home_team
                )

                and

                team_matches(
                    parts[1],
                    away_team
                )

            )


            reverse_match = (

                team_matches(
                    parts[0],
                    away_team
                )

                and

                team_matches(
                    parts[1],
                    home_team
                )

            )


            if not direct_match and not reverse_match:

                continue


            event_date = (
                event.get(
                    "dateEvent"
                )
            )


            event_time = (
                event.get(
                    "strTime"
                )
            )


            if not event_date or not event_time:

                continue


            try:

                event_datetime = datetime.strptime(
                    f"{event_date} "
                    f"{event_time}",
                    "%Y-%m-%d %H:%M:%S"
                )


            except ValueError:

                continue


            event_datetime = (
                event_datetime.replace(
                    tzinfo=timezone.utc
                ).astimezone(
                    ZoneInfo(
                        "America/New_York"
                    )
                )
            )


            public_api_matches += 1


            return {

                "away":
                away_team,

                "home":
                home_team,

                "datetime":
                event_datetime

            }


    return None


# --------------------------------------------------
# Day label
# --------------------------------------------------

def get_day_label(
    event_datetime
):

    eastern_now = datetime.now(
        ZoneInfo(
            "America/New_York"
        )
    )


    event_date = (
        event_datetime.date()
    )


    today = (
        eastern_now.date()
    )


    tomorrow = (
        today
        + timedelta(
            days=1
        )
    )


    if event_date == today:

        return "Today"


    if event_date == tomorrow:

        return "Tomorrow"


    return event_datetime.strftime(
        "%A"
    )


# --------------------------------------------------
# Build event information
# --------------------------------------------------

def build_event_info(
    stream,
    epg
):

    global verified_public_times_used
    global provider_fallbacks
    global no_public_match


    provider_name = clean_text(
        stream.get(
            "name",
            ""
        )
    )


    provider_event = remove_event_metadata(
        provider_name
    )


    provider_start = (
        extract_start_datetime(
            provider_name
        )
    )


    provider_start_eastern = None


    if provider_start:

        provider_start_eastern = (
            convert_to_eastern(
                provider_start,
                provider_timezone
            )
        )


    # --------------------------------------------------
    # Skip real provider EPG information
    # --------------------------------------------------

    if epg:

        epg_title = clean_text(
            epg.get(
                "title",
                ""
            )
        )


        epg_description = clean_text(
            epg.get(
                "description",
                ""
            )
        )


        if epg_title or epg_description:

            return (

                epg_title
                or provider_name,

                epg_description
                or epg_title
                or provider_name,

                provider_start_eastern,

                True

            )


    # --------------------------------------------------
    # Use channel name as event source
    # --------------------------------------------------

    preferred_date = (

        provider_start_eastern.date()

        if provider_start_eastern

        else datetime.now(
            ZoneInfo(
                "America/New_York"
            )
        ).date()

    )


    public_event = find_public_event(
        provider_event,
        preferred_date
    )


    if public_event:

        verified_public_times_used += 1


        away = public_event[
            "away"
        ]


        home = public_event[
            "home"
        ]


        event_datetime = public_event[
            "datetime"
        ]


        matchup = (

            f"{away} vs. {home}"

        )


        title_text = (

            f"{matchup} "

            f"({format_time(event_datetime)})"

        )


        date_text = (
            event_datetime.strftime(
                "%m/%d/%Y"
            )
        )


        day_text = (
            event_datetime.strftime(
                "%A"
            )
        )


        description_text = (

            f"{matchup}\n"

            f"{day_text} "

            f"{date_text} - "

            f"{format_time(event_datetime)}"

        )


        return (

            title_text,

            description_text,

            event_datetime,

            False

        )


    # --------------------------------------------------
    # Fallback when public schedule does not match
    # --------------------------------------------------

    no_public_match += 1


    if provider_start_eastern:

        provider_fallbacks += 1


    cleaned_title = (

        provider_event

    )


    if provider_start_eastern:

        cleaned_title = (

            f"{cleaned_title} "

            f"({format_time(
                provider_start_eastern
            )})"

        )


    if provider_start_eastern:

        cleaned_description = (

            f"{provider_event}\n"

            f"{provider_start_eastern.strftime('%A')} "

            f"{provider_start_eastern.strftime('%m/%d/%Y')} - "

            f"{format_time(provider_start_eastern)}"

        )


    else:

        cleaned_description = (

            provider_event

        )


    return (

        cleaned_title,

        cleaned_description,

        provider_start_eastern,

        False

    )


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
        days=3
    )
)


# --------------------------------------------------
# Create XMLTV channels
# --------------------------------------------------

print(
    "Creating XMLTV channels..."
)


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
# Create 6-hour programme blocks
# --------------------------------------------------

print(
    "Creating 6-hour programme blocks..."
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

        event_time,

        has_real_epg

    ) = build_event_info(
        stream,
        epg
    )


    current_start = guide_start


    while current_start < guide_end:

        current_stop = (

            current_start

            + timedelta(
                hours=6
            )

        )


        if current_stop > guide_end:

            current_stop = guide_end


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
    "6 hours each"
)


print(
    "Guide duration: "
    "3 days"
)


print(
    ""
)


print(
    "Public API statistics:"
)


print(
    f"Schedule API lookups: "
    f"{public_api_lookups}"
)


print(
    f"Verified public event matches: "
    f"{public_api_matches}"
)


print(
    f"Verified public times used: "
    f"{verified_public_times_used}"
)


print(
    f"Provider time fallbacks: "
    f"{provider_fallbacks}"
)


print(
    f"No public schedule match: "
    f"{no_public_match}"
)
