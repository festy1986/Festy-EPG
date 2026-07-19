import os
import requests
import xml.etree.ElementTree as ET

from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import re
import html
import time


CHANNEL_FILE = "config/sports_channels.txt"
TEAM_FILE = "config/sports_teams.txt"
OUTPUT_FILE = "guides/sports.xml"
SPORTS_LOGO_ROOT = "sports-logos"


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
# Convert time to regular format
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
# Determine league
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
# Normalize a matchup for SportsDB comparison
#
# This deliberately removes:
#
# - vs.
# - vs
# - punctuation
# - capitalization differences
#
# Therefore:
#
# Tampa Bay Rays vs. Boston Red Sox
#
# matches:
#
# Boston Red Sox vs Tampa Bay Rays
# --------------------------------------------------

def normalize_matchup_for_comparison(text):

    parts = matchup_parts(
        text
    )


    if len(parts) != 2:

        return []


    return [

        normalize_team_name(
            parts[0]
        ),

        normalize_team_name(
            parts[1]
        )

    ]


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
# SportsDB public schedule lookup
#
# IMPORTANT:
#
# This is performed AFTER:
#
# 1. The provider event is read.
# 2. sports_teams.txt is loaded.
# 3. The provider team names are converted
#    into clean official team names.
# 4. The clean title and description are created.
#
# The clean matchup is then used to find
# the actual SportsDB event and its time.
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


    print()

    print(
        f"[SPORTSDB] Requesting events for "
        f"{date_text}"
    )


    try:

        response = session.get(

            url,

            params={

                "d": date_text

            },

            timeout=30

        )


        print(

            f"[SPORTSDB] HTTP status: "

            f"{response.status_code}"

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


            print(

                f"[SPORTSDB] Events returned: "

                f"{len(events)}"

            )


        else:

            debug_stats[
                "public_events_empty"
            ] += 1


            print(

                "[SPORTSDB] No events returned"

            )


        return events


    except Exception as e:

        print(
            "[SPORTSDB ERROR]"
        )


        print(
            e
        )


        return []


# --------------------------------------------------
# Find verified public event
#
# The input is the CLEAN matchup.
#
# Example:
#
# Tampa Bay Rays vs. Boston Red Sox
#
# SportsDB may return:
#
# Boston Red Sox vs Tampa Bay Rays
#
# Both orders are accepted.
# --------------------------------------------------

def find_public_event(

    clean_matchup,

    preferred_date

):

    global public_api_matches


    parts = matchup_parts(

        clean_matchup

    )


    if len(parts) != 2:

        return None


    clean_first = parts[0]

    clean_second = parts[1]


    print()

    print(
        "[SPORTSDB LOOKUP]"
    )


    print(

        f"Clean matchup being searched: "

        f"{clean_first}"

        f" vs. "

        f"{clean_second}"

    )


    print(

        f"Preferred date: "

        f"{preferred_date}"

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

                f"[SPORTSDB] "

                f"{date_value}: "

                f"no events"

            )


            continue


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


            # --------------------------------------------------
            # Diagnostic output for possible team matches
            # --------------------------------------------------

            if (

                "ray" in home_team.lower()

                or

                "ray" in away_team.lower()

                or

                "red sox" in home_team.lower()

                or

                "red sox" in away_team.lower()

            ):

                print()

                print(

                    "[SPORTSDB POSSIBLE TEAM EVENT]"

                )


                print(

                    f"  Home: "

                    f"{home_team}"

                )


                print(

                    f"  Away: "

                    f"{away_team}"

                )


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
            # IMPORTANT:
            #
            # The clean guide names are canonicalized again
            # using sports_teams.txt.
            #
            # SportsDB names are also canonicalized using
            # the same file.
            # --------------------------------------------------

            clean_first_canonical = (

                canonicalize_team_name(

                    clean_first,

                    league_hint

                )

            )


            clean_second_canonical = (

                canonicalize_team_name(

                    clean_second,

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


            # --------------------------------------------------
            # Direct order:
            #
            # Clean first = SportsDB away
            # Clean second = SportsDB home
            # --------------------------------------------------

            direct_match = (

                team_matches(

                    clean_first_canonical,

                    event_away_canonical

                )

                and

                team_matches(

                    clean_second_canonical,

                    event_home_canonical

                )

            )


            # --------------------------------------------------
            # Reverse order:
            #
            # Clean first = SportsDB home
            # Clean second = SportsDB away
            # --------------------------------------------------

            reverse_match = (

                team_matches(

                    clean_first_canonical,

                    event_home_canonical

                )

                and

                team_matches(

                    clean_second_canonical,

                    event_away_canonical

                )

            )


            if not direct_match and not reverse_match:

                debug_stats[

                    "public_events_team_match_failed"

                ] += 1


                continue


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


                continue


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


                continue


            # SportsDB event time is UTC.

            event_datetime = (

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


            public_api_matches += 1


            debug_stats[

                "public_events_success"

            ] += 1


            print()

            print(

                "[SPORTSDB MATCH SUCCESS]"

            )


            print(

                f"  Clean title: "

                f"{clean_matchup}"

            )


            print(

                f"  SportsDB: "

                f"{away_team}"

                f" vs "

                f"{home_team}"

            )


            print(

                f"  League: "

                f"{event_league}"

            )


            print(

                f"  Verified Eastern time: "

                f"{event_datetime}"

            )


            return {

                "away": away_team,

                "home": home_team,

                "league": event_league,

                "datetime": event_datetime

            }


    print()

    print(

        "[SPORTSDB MATCH FAIL]"

    )


    print(

        f"No SportsDB event matched: "

        f"{clean_matchup}"

    )


    return None


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
# Find matchup logo
#
# This is performed AFTER SportsDB has identified
# the actual game.
#
# The existing logo structure is:
#
# sports-logos/
#   MLB/
#     Tampa_Bay_Rays/
#       Tampa_Bay_Rays_vs_Boston_Red_Sox.png
#
# Both direct and reverse order are checked.
# --------------------------------------------------

def find_matchup_logo(

    public_event

):

    global logos_found

    global logos_missing


    if not public_event:

        logos_missing += 1


        return None


    league = clean_text(

        public_event.get(

            "league",

            ""

        )

    )


    away = clean_text(

        public_event.get(

            "away",

            ""

        )

    )


    home = clean_text(

        public_event.get(

            "home",

            ""

        )

    )


    league_map = {

        "Major League Baseball": "MLB",

        "National Basketball Association": "NBA",

        "National Football League": "NFL",

        "National Hockey League": "NHL",

        "MLB": "MLB",

        "NBA": "NBA",

        "NFL": "NFL",

        "NHL": "NHL"

    }


    league_folder = league_map.get(

        league

    )


    if not league_folder:

        logos_missing += 1


        return None


    away = canonicalize_team_name(

        away,

        league_folder

    )


    home = canonicalize_team_name(

        home,

        league_folder

    )


    away_folder = clean_logo_filename(

        away

    )


    home_folder = clean_logo_filename(

        home

    )


    direct_filename = (

        f"{away_folder}"

        f"_vs_"

        f"{home_folder}"

        f".png"

    )


    direct_path = os.path.join(

        SPORTS_LOGO_ROOT,

        league_folder,

        away_folder,

        direct_filename

    )


    print()

    print(

        "[LOGO LOOKUP]"

    )


    print(

        f"  League: "

        f"{league_folder}"

    )


    print(

        f"  Away: "

        f"{away}"

    )


    print(

        f"  Home: "

        f"{home}"

    )


    print(

        f"  Checking: "

        f"{direct_path}"

    )


    if os.path.exists(

        direct_path

    ):

        logos_found += 1


        debug_stats[

            "logo_direct_order_found"

        ] += 1


        print(

            "[LOGO MATCH] "

            f"{direct_path}"

        )


        return direct_path


    reverse_filename = (

        f"{home_folder}"

        f"_vs_"

        f"{away_folder}"

        f".png"

    )


    reverse_path = os.path.join(

        SPORTS_LOGO_ROOT,

        league_folder,

        home_folder,

        reverse_filename

    )


    print(

        f"  Checking reverse: "

        f"{reverse_path}"

    )


    if os.path.exists(

        reverse_path

    ):

        logos_found += 1


        debug_stats[

            "logo_reverse_order_found"

        ] += 1


        print(

            "[LOGO MATCH] "

            f"{reverse_path}"

        )


        return reverse_path


    logos_missing += 1


    debug_stats[

        "logo_not_found"

    ] += 1


    print(

        "[LOGO NOT FOUND]"

    )


    return None


# --------------------------------------------------
# Build event information
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
    # STEP 1
    #
    # Extract the raw provider matchup.
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
    # STEP 2
    #
    # Determine league.
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
    # STEP 3
    #
    # Convert provider team names using
    # config/sports_teams.txt.
    #
    # THIS HAPPENS BEFORE SPORTSDB.
    # --------------------------------------------------

    canonical_matchup = canonicalize_matchup(

        provider_event,

        league_hint

    )


    print(

        "Canonical matchup:"

    )


    print(

        f"  {canonical_matchup}"

    )


    # --------------------------------------------------
    # STEP 4
    #
    # Extract the provider date.
    #
    # This is used to determine which date to
    # search on SportsDB.
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
    # STEP 5
    #
    # Create the clean title and description.
    #
    # SportsDB has NOT been called yet.
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


    print()

    print(

        "[CLEAN EVENT READY FOR SPORTSDB]"

    )


    print(

        f"  Title: "

        f"{title_text}"

    )


    print(

        f"  Description: "

        f"{description_text}"

    )


    # --------------------------------------------------
    # STEP 6
    #
    # NOW SportsDB uses the CLEAN matchup.
    #
    # It does not use the provider channel name.
    # --------------------------------------------------

    public_event = None


    if canonical_matchup:

        public_event = find_public_event(

            canonical_matchup,

            preferred_date

        )


    # --------------------------------------------------
    # STEP 7
    #
    # SportsDB matched the actual game.
    #
    # Update the title/description with the verified
    # actual event date and time.
    # --------------------------------------------------

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


        event_league = public_event.get(

            "league",

            ""

        )


        league_map = {

            "Major League Baseball": "MLB",

            "National Basketball Association": "NBA",

            "National Football League": "NFL",

            "National Hockey League": "NHL"

        }


        event_league_code = league_map.get(

            event_league

        )


        away = canonicalize_team_name(

            away,

            event_league_code

        )


        home = canonicalize_team_name(

            home,

            event_league_code

        )


        matchup = (

            f"{away}"

            f" vs. "

            f"{home}"

        )


        title_text = matchup


        description_text = (

            f"{matchup}\n"

            f"{event_datetime.strftime('%A')} "

            f"{event_datetime.strftime('%m/%d/%Y')}\n"

            f"{format_time(event_datetime)} "

            f"ET"

        )


        # --------------------------------------------------
        # STEP 8
        #
        # AFTER SportsDB finds the actual game,
        # find the matching matchup logo.
        # --------------------------------------------------

        logo_path = find_matchup_logo(

            public_event

        )


        return (

            title_text,

            description_text,

            event_datetime,

            logo_path,

            True

        )


    no_public_match += 1


    # --------------------------------------------------
    # No SportsDB match.
    #
    # Keep the clean canonical title and description.
    # --------------------------------------------------

    return (

        title_text,

        description_text,

        None,

        None,

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

    )

    .astimezone(

        ZoneInfo(

            "America/New_York"

        )

    )

    .replace(

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
#
# Channel logos are added AFTER the event is
# processed and SportsDB has identified the game.
# --------------------------------------------------

print()

print(

    "Creating XMLTV channels..."

)


matched = 0


channel_logos = {}


# --------------------------------------------------
# First process each channel's event.
#
# This allows the SportsDB matchup and logo to be
# determined before the channel XML is written.
# --------------------------------------------------

event_information = {}


for channel_id, requested_name in wanted.items():

    if channel_id not in provider:

        continue


    matched += 1


    stream = provider[

        channel_id

    ]


    print()

    print(

        f"Processing event for channel "

        f"{channel_id}"

    )


    event_information[channel_id] = build_event_info(

        stream

    )


    (

        title_text,

        description_text,

        event_time,

        logo_path,

        has_real_epg

    ) = event_information[channel_id]


    if logo_path:

        channel_logos[channel_id] = logo_path


# --------------------------------------------------
# Now create XMLTV channels.
#
# The matchup logo is placed on the channel itself.
# --------------------------------------------------

for channel_id, requested_name in wanted.items():

    if channel_id not in provider:

        continue


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


    # --------------------------------------------------
    # Add the detected matchup logo to the channel.
    # --------------------------------------------------

    logo_path = channel_logos.get(

        channel_id

    )


    if logo_path:

        icon = ET.SubElement(

            channel,

            "icon"

        )


        icon.set(

            "src",

            logo_path

        )


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


    (

        title_text,

        description_text,

        event_time,

        logo_path,

        has_real_epg

    ) = event_information[channel_id]


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

    f"No public schedule match: "

    f"{no_public_match}"

)


print(

    f"Team name conversions: "

    f"{team_name_conversions}"

)


print(

    f"Matchup logos found: "

    f"{logos_found}"

)


print(

    f"Matchup logos missing: "

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
