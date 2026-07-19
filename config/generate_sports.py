import os
import requests
import xml.etree.ElementTree as ET

from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import re
import html
import time
from urllib.parse import quote


CHANNEL_FILE = "config/sports_channels.txt"
TEAM_FILE = "config/sports_teams.txt"
OUTPUT_FILE = "guides/sports.xml"
SPORTS_LOGO_ROOT = "sports-logos"

GITHUB_RAW_ROOT = (
    "https://raw.githubusercontent.com/"
    "festy1986/festy-epg/main/"
)


XTREAM_URL = os.environ["XTREAM_URL"].rstrip("/")
USERNAME = os.environ["XTREAM_USERNAME"]
PASSWORD = os.environ["XTREAM_PASSWORD"]

SPORTSDB_TOKEN = os.environ.get(
    "SPORTSDB_TOKEN",
    "123"
)


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
        "User-Agent": "Mozilla/5.0"
    }
)


# --------------------------------------------------
# Statistics
# --------------------------------------------------

public_api_lookups = 0

public_api_matches = 0

verified_public_times_used = 0

no_public_match = 0

logos_found = 0

logos_missing = 0

team_name_conversions = 0


# --------------------------------------------------
# Detailed diagnostics
# --------------------------------------------------

debug_stats = {

    "provider_event_extracted": 0,

    "provider_event_failed": 0,

    "provider_matchup_parts_failed": 0,

    "canonical_team_matches": 0,

    "canonical_team_failures": 0,

    "public_events_downloaded": 0,

    "public_events_empty": 0,

    "public_events_team_match_failed": 0,

    "public_events_date_time_failed": 0,

    "public_events_success": 0,

    "logo_direct_order_found": 0,

    "logo_reverse_order_found": 0,

    "logo_not_found": 0,

}


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
        r"\s+v\.?\s+",
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
# Extract matchup from provider channel name
# --------------------------------------------------

def extract_provider_matchup(text):

    if not text:

        debug_stats[
            "provider_event_failed"
        ] += 1


        return ""


    text = clean_text(
        text
    )


    if "|" not in text:

        debug_stats[
            "provider_event_failed"
        ] += 1


        return ""


    text = text.split(
        "|",
        1
    )[1]


    text = re.split(
        r"\bstart\s*:",
        text,
        maxsplit=1,
        flags=re.IGNORECASE
    )[0]


    text = re.split(
        r"\bstop\s*:",
        text,
        maxsplit=1,
        flags=re.IGNORECASE
    )[0]


    text = clean_text(
        text
    )


    matchup = normalize_matchup(
        text
    )


    parts = matchup_parts(
        matchup
    )


    if len(parts) != 2:

        debug_stats[
            "provider_event_failed"
        ] += 1


        return ""


    debug_stats[
        "provider_event_extracted"
    ] += 1


    return matchup


# --------------------------------------------------
# Extract provider start timestamp
#
# This is used only to determine the date that
# SportsDB should search.
#
# It is NOT used as the final displayed game time.
# --------------------------------------------------

def extract_start_datetime(text):

    if not text:

        return None


    text = clean_text(
        text
    )


    patterns = [

        r"start\s*:\s*"
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

            time_part += ":00"


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
# Get provider timezone
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
# Convert provider time to Eastern Time
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


    source_datetime = naive_datetime.replace(
        tzinfo=source_zone
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
# Load provider timezone
# --------------------------------------------------

provider_timezone = get_server_timezone()


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
# Load canonical team names and aliases
# --------------------------------------------------

team_aliases = {

    "MLB": {},

    "NBA": {},

    "NFL": {},

    "NHL": {}

}


def normalize_team_name(text):

    if not text:

        return ""


    text = clean_text(
        text
    ).lower()


    text = text.replace(
        "&",
        " and "
    )


    text = re.sub(
        r"[^a-z0-9]+",
        " ",
        text
    )


    text = re.sub(
        r"\s+",
        " ",
        text
    )


    return text.strip()


def load_canonical_teams():

    print(
        "Loading canonical team names..."
    )


    current_league = None


    with open(
        TEAM_FILE,
        "r",
        encoding="utf-8"
    ) as f:

        for line_number, raw_line in enumerate(
            f,
            start=1
        ):

            line = raw_line.strip()


            if not line:

                continue


            if line.startswith(
                "#"
            ):

                continue


            if (

                line.startswith("[")

                and

                line.endswith("]")

            ):

                league = line[
                    1:-1
                ].strip().upper()


                if league not in team_aliases:

                    print(
                        f"Unknown league "
                        f"at line "
                        f"{line_number}: "
                        f"{league}"
                    )


                    current_league = None


                else:

                    current_league = league


                continue


            if not current_league:

                continue


            if "=" not in line:

                print(
                    f"Invalid team line "
                    f"{line_number}: "
                    f"{line}"
                )


                continue


            official_name, aliases_text = line.split(
                "=",
                1
            )


            official_name = clean_text(
                official_name
            )


            aliases = [

                clean_text(alias)

                for alias in aliases_text.split(",")

            ]


            aliases.append(
                official_name
            )


            official_normalized = normalize_team_name(
                official_name
            )


            if not official_normalized:

                continue


            for alias in aliases:

                normalized_alias = normalize_team_name(
                    alias
                )


                if not normalized_alias:

                    continue


                team_aliases[
                    current_league
                ][
                    normalized_alias
                ] = official_name


    for league, aliases in team_aliases.items():

        print(
            f"{league}: "
            f"{len(aliases)} "
            f"team aliases loaded"
        )


load_canonical_teams()


# --------------------------------------------------
# Extract matchup parts
# --------------------------------------------------

def matchup_parts(text):

    if not text:

        return []


    text = clean_text(
        text
    )


    match = re.search(

        r"(.+?)\s+"

        r"(?:vs\.?|v\.?|x|@)"

        r"\s+"

        r"(.+)",

        text,

        flags=re.IGNORECASE

    )


    if not match:

        debug_stats[
            "provider_matchup_parts_failed"
        ] += 1


        return []


    first = clean_text(
        match.group(1)
    )


    second = clean_text(
        match.group(2)
    )


    if not first or not second:

        debug_stats[
            "provider_matchup_parts_failed"
        ] += 1


        return []


    return [

        first,

        second

    ]


# --------------------------------------------------
# Determine league from provider channel name
# --------------------------------------------------

def detect_league(text):

    if not text:

        return None


    text = clean_text(
        text
    )


    match = re.search(

        r"\b(MLB|NBA|NFL|NHL)\b",

        text,

        flags=re.IGNORECASE

    )


    if not match:

        return None


    return match.group(
        1
    ).upper()


# --------------------------------------------------
# Convert provider team name to official name
#
# This is the source of the displayed team names.
#
# SportsDB does NOT perform this conversion.
# --------------------------------------------------

def canonicalize_team_name(
    provider_team,
    league_hint=None
):

    global team_name_conversions


    provider_team = clean_text(
        provider_team
    )


    if not provider_team:

        debug_stats[
            "canonical_team_failures"
        ] += 1


        return provider_team


    normalized_provider = normalize_team_name(
        provider_team
    )


    if not normalized_provider:

        debug_stats[
            "canonical_team_failures"
        ] += 1


        return provider_team


    if league_hint in team_aliases:

        exact = team_aliases[
            league_hint
        ].get(
            normalized_provider
        )


        if exact:

            if exact != provider_team:

                team_name_conversions += 1


            debug_stats[
                "canonical_team_matches"
            ] += 1


            return exact


    if league_hint in team_aliases:

        provider_words = set(
            normalized_provider.split()
        )


        best_match = None

        best_score = 0


        for normalized_alias, official_name in team_aliases[
            league_hint
        ].items():

            alias_words = set(
                normalized_alias.split()
            )


            if not alias_words:

                continue


            if normalized_provider in normalized_alias:

                score = len(
                    normalized_provider
                )


                if score > best_score:

                    best_score = score

                    best_match = official_name


            elif normalized_alias in normalized_provider:

                score = len(
                    normalized_alias
                )


                if score > best_score:

                    best_score = score

                    best_match = official_name


            else:

                shared_words = (

                    provider_words

                    &

                    alias_words

                )


                if shared_words:

                    score = len(
                        shared_words
                    )


                    if score > best_score:

                        best_score = score

                        best_match = official_name


        if best_match:

            team_name_conversions += 1


            debug_stats[
                "canonical_team_matches"
            ] += 1


            return best_match


    debug_stats[
        "canonical_team_failures"
    ] += 1


    return provider_team


# --------------------------------------------------
# Canonicalize entire matchup
# --------------------------------------------------

def canonicalize_matchup(
    matchup,
    league_hint=None
):

    parts = matchup_parts(
        matchup
    )


    if len(parts) != 2:

        return normalize_matchup(
            matchup
        )


    first = canonicalize_team_name(
        parts[0],
        league_hint
    )


    second = canonicalize_team_name(
        parts[1],
        league_hint
    )


    return (

        f"{first}"

        f" vs. "

        f"{second}"

    )


# --------------------------------------------------
# SportsDB event date/time parsing
# --------------------------------------------------

def parse_sportsdb_datetime(
    event
):

    event_date = event.get(
        "dateEvent"
    )


    event_time = event.get(
        "strTime"
    )


    if not event_date or not event_time:

        debug_stats[
            "public_events_date_time_failed"
        ] += 1


        return None


    try:

        event_datetime = datetime.strptime(

            f"{event_date} "

            f"{event_time}",

            "%Y-%m-%d %H:%M:%S"

        )


    except ValueError:

        debug_stats[
            "public_events_date_time_failed"
        ] += 1


        return None


    return (

        event_datetime

        .replace(
            tzinfo=timezone.utc
        )

        .astimezone(
            ZoneInfo(
                "America/New_York"
            )
        )

    )


# --------------------------------------------------
# SportsDB public schedule lookup
#
# SPORTSDB IS USED ONLY TO:
#
# - Find the matching game
# - Return the game's verified time
#
# It does NOT provide:
#
# - Displayed team names
# - Title cleanup
# - Description cleanup
# - Logo information
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

        f"api/v1/json/{SPORTSDB_TOKEN}/eventsday.php"

    )


    try:

        response = session.get(

            url,

            params={

                "d": date_text

            },

            timeout=30

        )


        if response.status_code != 200:

            debug_stats[
                "public_events_empty"
            ] += 1


            return []


        data = response.json()


        events = data.get(

            "events",

            []

        ) or []


        if events:

            debug_stats[
                "public_events_downloaded"
            ] += len(events)


        else:

            debug_stats[
                "public_events_empty"
            ] += 1


        return events


    except Exception as e:

        print(
            "[SPORTSDB API ERROR]"
        )


        print(
            e
        )


        return []


# --------------------------------------------------
# Find SportsDB event
#
# The cleaned canonical matchup is used to find
# the game.
#
# SportsDB's team names are ONLY used internally
# to verify that the correct event was found.
#
# They are NEVER written into the title or description.
# --------------------------------------------------

def find_public_event(

    canonical_matchup,

    preferred_date

):

    global public_api_matches


    parts = matchup_parts(
        canonical_matchup
    )


    if len(parts) != 2:

        return None


    wanted_first = parts[0]

    wanted_second = parts[1]


    print()

    print(
        "[SPORTSDB LOOKUP]"
    )


    print(
        "Searching for:"
    )


    print(
        f"  {canonical_matchup}"
    )


    search_dates = [

        preferred_date,

        preferred_date - timedelta(
            days=1
        ),

        preferred_date + timedelta(
            days=1
        ),

        preferred_date + timedelta(
            days=2
        )

    ]


    for date_value in search_dates:

        events = get_public_events(
            date_value
        )


        if not events:

            print(

                f"[SPORTSDB] {date_value}: "

                f"no events returned"

            )


            continue


        print(

            f"[SPORTSDB] {date_value}: "

            f"{len(events)} events"

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


            event_league = clean_text(

                event.get(

                    "strLeague",

                    ""

                )

            )


            league_map = {

                "Major League Baseball": "MLB",

                "National Basketball Association": "NBA",

                "National Football League": "NFL",

                "National Hockey League": "NHL"

            }


            league_hint = league_map.get(

                event_league

            )


            # --------------------------------------------------
            # SportsDB names are only normalized internally
            # for matching.
            #
            # They are NOT used for display.
            # --------------------------------------------------

            wanted_first_canonical = (

                canonicalize_team_name(

                    wanted_first,

                    league_hint

                )

            )


            wanted_second_canonical = (

                canonicalize_team_name(

                    wanted_second,

                    league_hint

                )

            )


            event_home_canonical = (

                canonicalize_team_name(

                    home_team,

                    league_hint

                )

            )


            event_away_canonical = (

                canonicalize_team_name(

                    away_team,

                    league_hint

                )

            )


            direct_match = (

                team_matches(

                    wanted_first_canonical,

                    event_away_canonical

                )

                and

                team_matches(

                    wanted_second_canonical,

                    event_home_canonical

                )

            )


            reverse_match = (

                team_matches(

                    wanted_first_canonical,

                    event_home_canonical

                )

                and

                team_matches(

                    wanted_second_canonical,

                    event_away_canonical

                )

            )


            if not direct_match and not reverse_match:

                debug_stats[

                    "public_events_team_match_failed"

                ] += 1


                continue


            event_datetime = parse_sportsdb_datetime(

                event

            )


            if not event_datetime:

                continue


            public_api_matches += 1


            debug_stats[

                "public_events_success"

            ] += 1


            print()

            print(
                "[SPORTSDB MATCH SUCCESS]"
            )


            print(
                f"  Clean matchup: "
                f"{canonical_matchup}"
            )


            print(
                f"  SportsDB event: "
                f"{away_team} vs "
                f"{home_team}"
            )


            print(
                f"  Verified Eastern time: "
                f"{event_datetime}"
            )


            return {

                "datetime": event_datetime

            }


    print()

    print(
        "[SPORTSDB MATCH FAIL]"
    )


    print(
        f"  No event/time found for: "
        f"{canonical_matchup}"
    )


    return None


# --------------------------------------------------
# Team matching
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


    if wanted_team == actual_team:

        return True


    if (

        wanted_team in actual_team

        or

        actual_team in wanted_team

    ):

        return True


    wanted_words = set(

        wanted_team.split()

    )


    actual_words = set(

        actual_team.split()

    )


    if wanted_words.issubset(

        actual_words

    ):

        return True


    meaningful_words = {

        word

        for word in wanted_words

        if len(word) >= 4

    }


    shared_words = (

        wanted_words

        &

        actual_words

    )


    return bool(

        meaningful_words

        and

        meaningful_words.issubset(

            shared_words

        )

    )


# --------------------------------------------------
# Create safe logo filename
# --------------------------------------------------

def clean_logo_filename(text):

    text = clean_text(
        text
    )


    text = re.sub(
        r"[^A-Za-z0-9]+",
        "_",
        text
    )


    text = re.sub(
        r"_+",
        "_",
        text
    )


    return text.strip(
        "_"
    )


# --------------------------------------------------
# Create normalized logo key
#
# This makes logo matching order-independent.
#
# Example:
#
# Tampa Bay Rays vs. Boston Red Sox
#
# matches:
#
# Tampa_Bay_Rays_vs_Boston_Red_Sox.png
#
# and:
#
# Boston_Red_Sox_vs_Tampa_Bay_Rays.png
# --------------------------------------------------

def matchup_logo_key(
    first_team,
    second_team
):

    first = normalize_team_name(
        first_team
    )


    second = normalize_team_name(
        second_team
    )


    if not first or not second:

        return None


    return frozenset({

        first,

        second

    })


# --------------------------------------------------
# Find matchup logo by searching the ENTIRE
# sports-logos directory.
#
# This does NOT depend on SportsDB.
# --------------------------------------------------

def find_matchup_logo(

    canonical_matchup,

    league_hint

):

    global logos_found

    global logos_missing


    parts = matchup_parts(

        canonical_matchup

    )


    if len(parts) != 2:

        logos_missing += 1


        debug_stats[

            "logo_not_found"

        ] += 1


        return None


    first_team = canonicalize_team_name(

        parts[0],

        league_hint

    )


    second_team = canonicalize_team_name(

        parts[1],

        league_hint

    )


    wanted_key = matchup_logo_key(

        first_team,

        second_team

    )


    if not wanted_key:

        logos_missing += 1


        debug_stats[

            "logo_not_found"

        ] += 1


        return None


    print()

    print(
        "[LOGO SEARCH]"
    )


    print(
        f"  Searching entire: "
        f"{SPORTS_LOGO_ROOT}/"
    )


    print(
        f"  Teams: "
        f"{first_team} vs. {second_team}"
    )


    if not os.path.isdir(

        SPORTS_LOGO_ROOT

    ):

        logos_missing += 1


        debug_stats[

            "logo_not_found"

        ] += 1


        print(
            "  Logo directory does not exist."
        )


        return None


    for root, directories, files in os.walk(

        SPORTS_LOGO_ROOT

    ):

        for filename in files:

            if not filename.lower().endswith(

                ".png"

            ):

                continue


            file_stem = os.path.splitext(

                filename

            )[0]


            if "_vs_" not in file_stem:

                continue


            file_parts = file_stem.split(

                "_vs_",

                1

            )


            if len(file_parts) != 2:

                continue


            logo_first = file_parts[0]

            logo_second = file_parts[1]


            logo_first_normalized = normalize_team_name(

                logo_first.replace(

                    "_",

                    " "

                )

            )


            logo_second_normalized = normalize_team_name(

                logo_second.replace(

                    "_",

                    " "

                )

            )


            logo_key = matchup_logo_key(

                logo_first_normalized,

                logo_second_normalized

            )


            if logo_key != wanted_key:

                continue


            relative_path = os.path.relpath(

                os.path.join(

                    root,

                    filename

                ),

                "."

            )


            relative_path = relative_path.replace(

                os.sep,

                "/"

            )


            encoded_path = "/".join(

                quote(

                    part,

                    safe=""

                )

                for part in relative_path.split(

                    "/"

                )

            )


            logo_url = (

                GITHUB_RAW_ROOT

                + encoded_path

            )


            logos_found += 1


            if (

                logo_first_normalized

                ==

                normalize_team_name(

                    first_team

                )

            ):

                debug_stats[

                    "logo_direct_order_found"

                ] += 1


            else:

                debug_stats[

                    "logo_reverse_order_found"

                ] += 1


            print(
                "  Logo found:"
            )


            print(
                f"  {relative_path}"
            )


            print(
                f"  {logo_url}"
            )


            return logo_url


    logos_missing += 1


    debug_stats[

        "logo_not_found"

    ] += 1


    print(
        "  No matching logo found."
    )


    return None


# --------------------------------------------------
# Build event information
#
# Order:
#
# 1. Read provider matchup
# 2. Clean team names using sports_teams.txt
# 3. Build title/description from those names
# 4. SportsDB searches for the game time only
# 5. Logo search runs independently
# --------------------------------------------------

def build_event_info(

    stream

):

    global verified_public_times_used

    global no_public_match


    provider_name = clean_text(

        stream.get(

            "name",

            ""

        )

    )


    stream_id = str(

        stream.get(

            "stream_id",

            ""

        )

    )


    print()

    print(
        "=================================================="
    )


    print(

        f"[CHANNEL {stream_id}]"

    )


    print(
        "Raw provider name:"
    )


    print(
        f"  {provider_name}"
    )


    # --------------------------------------------------
    # STEP 1:
    #
    # Extract provider matchup.
    # --------------------------------------------------

    provider_event = extract_provider_matchup(

        provider_name

    )


    print(
        "Extracted matchup:"
    )


    print(
        f"  {provider_event}"
    )


    # --------------------------------------------------
    # STEP 2:
    #
    # Detect league.
    # --------------------------------------------------

    league_hint = detect_league(

        provider_name

    )


    print(
        "Detected league:"
    )


    print(
        f"  {league_hint}"
    )


    # --------------------------------------------------
    # STEP 3:
    #
    # Clean team names using sports_teams.txt.
    #
    # This controls the displayed matchup.
    # --------------------------------------------------

    canonical_matchup = canonicalize_matchup(

        provider_event,

        league_hint

    )


    print(
        "Clean canonical matchup:"
    )


    print(
        f"  {canonical_matchup}"
    )


    # --------------------------------------------------
    # STEP 4:
    #
    # Determine preferred date.
    #
    # Provider timestamp is used only to know which
    # date to search.
    # --------------------------------------------------

    provider_start = extract_start_datetime(

        provider_name

    )


    provider_start_eastern = None


    if provider_start:

        provider_start_eastern = (

            convert_to_eastern(

                provider_start,

                provider_timezone

            )

        )


    preferred_date = (

        provider_start_eastern.date()

        if provider_start_eastern

        else datetime.now(

            ZoneInfo(

                "America/New_York"

            )

        ).date()

    )


    # --------------------------------------------------
    # STEP 5:
    #
    # Build the clean title and description BEFORE
    # SportsDB.
    #
    # These names come from sports_teams.txt.
    # --------------------------------------------------

    if canonical_matchup:

        title_text = canonical_matchup


        description_text = (

            f"{canonical_matchup}\n"

            f"{preferred_date.strftime('%A')} "

            f"{preferred_date.strftime('%m/%d/%Y')}"

        )


    else:

        title_text = "Sports Event"


        description_text = (

            f"Sports event\n"

            f"{preferred_date.strftime('%A')} "

            f"{preferred_date.strftime('%m/%d/%Y')}"

        )


    # --------------------------------------------------
    # STEP 6:
    #
    # Find the logo independently.
    #
    # This happens regardless of whether SportsDB
    # finds the game.
    # --------------------------------------------------

    logo_url = None


    if canonical_matchup and league_hint:

        logo_url = find_matchup_logo(

            canonical_matchup,

            league_hint

        )


    # --------------------------------------------------
    # STEP 7:
    #
    # SportsDB is used ONLY to find the verified
    # game time.
    # --------------------------------------------------

    public_event = None


    if canonical_matchup:

        public_event = find_public_event(

            canonical_matchup,

            preferred_date

        )


    # --------------------------------------------------
    # STEP 8:
    #
    # If SportsDB found the game, add its verified
    # Eastern time to BOTH the title and description.
    #
    # Team names remain the names from sports_teams.txt.
    # --------------------------------------------------

    if public_event:

        verified_public_times_used += 1


        event_datetime = public_event[

            "datetime"

        ]


        event_time_text = (

            event_datetime.strftime(

                "%-I:%M %p"

            )

        )


        title_text = (

            f"{canonical_matchup}"

            f" - "

            f"{event_time_text}"

        )


        description_text = (

            f"{canonical_matchup}\n"

            f"{event_datetime.strftime('%A')} "

            f"{event_datetime.strftime('%m/%d/%Y')}\n"

            f"{event_time_text}"

        )


        print()

        print(
            "[FINAL EVENT DATA]"
        )


        print(
            f"  Title: "
            f"{title_text}"
        )


        print(
            f"  Description: "
            f"{description_text}"
        )


        print(
            f"  Logo: "
            f"{logo_url}"
        )


        return (

            title_text,

            description_text,

            logo_url,

            True

        )


    # --------------------------------------------------
    # SportsDB failed.
    #
    # Keep the clean title and description.
    #
    # The logo remains valid if it was found.
    # --------------------------------------------------

    no_public_match += 1


    print()

    print(
        "[FINAL EVENT DATA]"
    )


    print(
        f"  Title: "
        f"{title_text}"
    )


    print(
        f"  Description: "
        f"{description_text}"
    )


    print(
        f"  Logo: "
        f"{logo_url}"
    )


    return (

        title_text,

        description_text,

        logo_url,

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

guide_start = (

    datetime.now(

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

print()

print(
    "Creating XMLTV channels..."
)


matched = 0


channel_elements = {}


for channel_id, requested_name in wanted.items():

    if channel_id not in provider:

        continue


    matched += 1


    stream = provider[

        channel_id

    ]


    provider_name = stream.get(

        "name",

        requested_name

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


    channel_elements[

        channel_id

    ] = channel


# --------------------------------------------------
# Create 6-hour programme blocks
# --------------------------------------------------

print()

print(
    "Creating 6-hour programme blocks..."
)


for channel_id, requested_name in wanted.items():

    if channel_id not in provider:

        continue


    stream = provider[

        channel_id

    ]


    print()

    print(

        f"Processing {channel_id}"

    )


    (

        title_text,

        description_text,

        logo_url,

        has_real_epg

    ) = build_event_info(

        stream

    )


    # --------------------------------------------------
    # Add the matchup logo to the CHANNEL.
    #
    # This is independent of SportsDB success/failure.
    # --------------------------------------------------

    if logo_url:

        channel = channel_elements[

            channel_id

        ]


        icon = ET.SubElement(

            channel,

            "icon"

        )


        icon.set(

            "src",

            logo_url

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


        current_start = current_stop


# --------------------------------------------------
# Save XMLTV file
# --------------------------------------------------

print()

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


# --------------------------------------------------
# Final statistics
# --------------------------------------------------

print()

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
    "Guide blocks: 6 hours each"
)


print(
    "Guide duration: 3 days"
)


print()

print(
    "SportsDB statistics:"
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

    f"No public schedule match: "

    f"{no_public_match}"

)


print()

print(
    "Team name conversions:"
)


print(

    f"{team_name_conversions}"

)


print()

print(
    "Matchup logos found:"
)


print(

    f"{logos_found}"

)


print(

    "Matchup logos missing: "

    f"{logos_missing}"

)


print()

print(
    "Detailed matching diagnostics:"
)


for key, value in debug_stats.items():

    print(

        f"{key}: {value}"

    )
