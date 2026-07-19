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
#
# Example:
#
# MLB 04 | Rays x Red Sox
# start:2026-07-19 18:35:00
# stop:2026-07-20 01:48:20
#
# becomes:
#
# Rays vs. Red Sox
#
# The provider time is NOT used.
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

    if "|" in text:

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

    text = normalize_matchup(
        text
    )

    parts = matchup_parts(
        text
    )

    if len(parts) != 2:

        debug_stats[
            "provider_event_failed"
        ] += 1

        return ""

    debug_stats[
        "provider_event_extracted"
    ] += 1

    return text


# --------------------------------------------------
# Get server timezone
#
# This is retained only for diagnostics.
#
# Provider event times are NOT used as
# event times or fallbacks.
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

        return "UTC"

    print(
        f"Provider timezone: {timezone_name}"
    )

    return timezone_name


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
    f"Requested channels: {len(wanted)}"
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
    f"Provider channels: {len(streams)}"
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
# Normalize team names
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
# Match team names
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
        or actual_team in wanted_team
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
# SportsDB team database
# --------------------------------------------------

SPORTSDB_LEAGUES = {

    "MLB": "MLB",
    "NBA": "NBA",
    "NFL": "NFL",
    "NHL": "NHL"

}


team_aliases = {}


def load_sportsdb_teams():

    print(
        "Loading official team names from TheSportsDB..."
    )

    for league_folder, league_name in SPORTSDB_LEAGUES.items():

        url = (
            "https://www.thesportsdb.com/"
            "api/v1/json/123/"
            "search_all_teams.php"
        )

        try:

            response = session.get(
                url,
                params={
                    "l": league_name
                },
                timeout=60
            )

            response.raise_for_status()

            data = response.json()

            teams = data.get(
                "teams",
                []
            ) or []

            print(
                f"{league_folder}: "
                f"{len(teams)} official teams"
            )

            for team in teams:

                official_name = clean_text(
                    team.get(
                        "strTeam",
                        ""
                    )
                )

                if not official_name:
                    continue

                aliases = [

                    official_name,

                    team.get(
                        "strTeamShort",
                        ""
                    ),

                    team.get(
                        "strAlternate",
                        ""
                    )

                ]

                for alias in aliases:

                    alias = clean_text(
                        alias
                    )

                    if not alias:
                        continue

                    normalized_alias = normalize_team_name(
                        alias
                    )

                    if normalized_alias:

                        team_aliases[
                            normalized_alias
                        ] = {

                            "name":
                            official_name,

                            "league":
                            league_folder

                        }

        except Exception as e:

            print(
                f"Unable to load "
                f"{league_folder} teams:"
            )

            print(
                e
            )


load_sportsdb_teams()


# --------------------------------------------------
# Convert provider team to official name
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

    exact = team_aliases.get(
        normalized_provider
    )

    if exact:

        if exact["name"] != provider_team:

            team_name_conversions += 1

        debug_stats[
            "canonical_team_matches"
        ] += 1

        return exact["name"]

    provider_words = set(
        normalized_provider.split()
    )

    best_match = None
    best_score = 0

    for normalized_alias, team_data in team_aliases.items():

        if (
            league_hint
            and
            team_data["league"] != league_hint
        ):

            continue

        alias_words = set(
            normalized_alias.split()
        )

        if not alias_words:
            continue

        shared = (
            provider_words
            &
            alias_words
        )

        if not shared:
            continue

        meaningful_provider_words = {

            word

            for word in provider_words

            if len(word) >= 4

        }

        meaningful_alias_words = {

            word

            for word in alias_words

            if len(word) >= 4

        }

        if (

            meaningful_provider_words

            and

            meaningful_provider_words.issubset(
                alias_words
            )

        ):

            score = (
                len(
                    meaningful_provider_words
                )
                * 10
            )

            if score > best_score:

                best_score = score

                best_match = team_data

            continue

        if (

            meaningful_alias_words

            and

            meaningful_alias_words.issubset(
                provider_words
            )

        ):

            score = (
                len(
                    meaningful_alias_words
                )
                * 10
            )

            if score > best_score:

                best_score = score

                best_match = team_data

    if best_match:

        team_name_conversions += 1

        debug_stats[
            "canonical_team_matches"
        ] += 1

        return best_match["name"]

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
# This is called ONLY after a public event
# has successfully matched.
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

        print(
            f"[LOGO FAIL] Unknown league: {league}"
        )

        logos_missing += 1

        return None

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

    if os.path.exists(
        direct_path
    ):

        logos_found += 1

        debug_stats[
            "logo_direct_order_found"
        ] += 1

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

    if os.path.exists(
        reverse_path
    ):

        logos_found += 1

        debug_stats[
            "logo_reverse_order_found"
        ] += 1

        return reverse_path

    print()

    print(
        "[LOGO FAIL] Not found:"
    )

    print(
        f"  {away} vs. {home}"
    )

    print(
        "  Tried:"
    )

    print(
        f"  {direct_path}"
    )

    print(
        f"  {reverse_path}"
    )

    print()

    logos_missing += 1

    debug_stats[
        "logo_not_found"
    ] += 1

    return None


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

        print()

        print(
            "[PUBLIC API ERROR]"
        )

        print(
            e
        )

        return []


# --------------------------------------------------
# Find public event
#
# IMPORTANT:
#
# 1. Provider channel is cleaned first.
# 2. Provider team names are canonicalized.
# 3. Public events are searched using those
#    cleaned/canonicalized teams.
# 4. Only a successful public match provides
#    the event time.
#
# The provider event time is NEVER used.
# --------------------------------------------------

def find_public_event(
    cleaned_matchup
):

    global public_api_matches

    parts = matchup_parts(
        cleaned_matchup
    )

    if len(parts) != 2:

        print()

        print(
            "[MATCH FAIL] Could not split cleaned matchup:"
        )

        print(
            f"  {cleaned_matchup}"
        )

        return None

    provider_first = parts[0]
    provider_second = parts[1]

    print()

    print(
        "[CLEANED MATCHUP]"
    )

    print(
        f"  {provider_first} vs. {provider_second}"
    )

    # Search a reasonable date window based on
    # today's date only.
    #
    # The provider's event timestamp is not used.
    today = datetime.now(
        ZoneInfo(
            "America/New_York"
        )
    ).date()

    search_dates = [

        today - timedelta(days=1),
        today,
        today + timedelta(days=1),
        today + timedelta(days=2)

    ]

    for date_value in search_dates:

        events = get_public_events(
            date_value
        )

        if not events:

            print(
                f"[LOOKUP] {date_value}: "
                f"no public events returned"
            )

            continue

        print(
            f"[LOOKUP] {date_value}: "
            f"{len(events)} public events"
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

            cleaned_first_canonical = canonicalize_team_name(
                provider_first,
                league_hint
            )

            cleaned_second_canonical = canonicalize_team_name(
                provider_second,
                league_hint
            )

            event_home_canonical = canonicalize_team_name(
                home_team,
                league_hint
            )

            event_away_canonical = canonicalize_team_name(
                away_team,
                league_hint
            )

            direct_match = (

                team_matches(
                    cleaned_first_canonical,
                    event_away_canonical
                )

                and

                team_matches(
                    cleaned_second_canonical,
                    event_home_canonical
                )

            )

            reverse_match = (

                team_matches(
                    cleaned_first_canonical,
                    event_home_canonical
                )

                and

                team_matches(
                    cleaned_second_canonical,
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
                "[MATCH SUCCESS]"
            )

            print(
                f"  Cleaned provider: "
                f"{cleaned_first_canonical} vs. "
                f"{cleaned_second_canonical}"
            )

            print(
                f"  SportsDB: "
                f"{away_team} vs. {home_team}"
            )

            print(
                f"  League: {event_league}"
            )

            print(
                f"  Verified time: "
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
        "[MATCH FAIL] No public event matched:"
    )

    print(
        f"  {provider_first} vs. {provider_second}"
    )

    return None


# --------------------------------------------------
# Build event information
#
# IMPORTANT:
#
# Provider name:
#   MLB 04 | Rays x Red Sox
#
# First becomes:
#   Rays vs. Red Sox
#
# Then becomes:
#   Tampa Bay Rays vs. Boston Red Sox
#
# ONLY THEN is the public schedule searched.
#
# No provider event time fallback exists.
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

    # ----------------------------------------------
    # STEP 1:
    # Clean provider channel name.
    #
    # Provider time is deliberately ignored.
    # ----------------------------------------------

    cleaned_matchup = extract_provider_matchup(
        provider_name
    )

    print(
        "Cleaned matchup:"
    )

    print(
        f"  {cleaned_matchup}"
    )

    if not cleaned_matchup:

        no_public_match += 1

        return (

            "Sports Event",
            "Sports event",
            None,
            None,
            False

        )

    # ----------------------------------------------
    # STEP 2:
    # Canonicalize team names before lookup.
    #
    # Example:
    #
    # Rays vs. Red Sox
    #
    # becomes:
    #
    # Tampa Bay Rays vs. Boston Red Sox
    # ----------------------------------------------

    canonical_matchup = canonicalize_matchup(
        cleaned_matchup
    )

    print(
        "Canonical matchup:"
    )

    print(
        f"  {canonical_matchup}"
    )

    # ----------------------------------------------
    # STEP 3:
    # Search public schedule using the cleaned
    # and canonicalized matchup.
    #
    # Provider start time is NOT passed in.
    # ----------------------------------------------

    public_event = find_public_event(
        canonical_matchup
    )

    if not public_event:

        no_public_match += 1

        print()

        print(
            "[NO PUBLIC MATCH]"
        )

        print(
            "  No event time will be used."
        )

        print(
            "  No logo lookup will be performed."
        )

        return (

            canonical_matchup,
            canonical_matchup,
            None,
            None,
            False

        )

    # ----------------------------------------------
    # STEP 4:
    # Public event matched.
    # Now use the public event's official names
    # and verified time.
    # ----------------------------------------------

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

        f"{away}"
        f" vs. "
        f"{home}"

    )

    title_text = (

        f"{matchup}"
        f" "
        f"({format_time(event_datetime)})"

    )

    date_text = event_datetime.strftime(
        "%m/%d/%Y"
    )

    day_text = event_datetime.strftime(
        "%A"
    )

    description_text = (

        f"{matchup}\n"
        f"{day_text} "
        f"{date_text} - "
        f"{format_time(event_datetime)}"

    )

    # ----------------------------------------------
    # STEP 5:
    # ONLY after public match succeeds:
    # look for logo.
    # ----------------------------------------------

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
# Guide period
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
# --------------------------------------------------

print()

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
        event_time,
        logo_path,
        has_real_epg

    ) = build_event_info(
        stream
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

        if logo_path:

            icon = ET.SubElement(

                programme,
                "icon"

            )

            icon.set(

                "src",
                logo_path

            )

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
    f"Matched channels: {matched}"
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
