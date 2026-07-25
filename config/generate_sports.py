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
SUPPORTED_MAJOR_LEAGUES = ("MLB", "NBA", "NFL", "NHL")

GITHUB_RAW_ROOT = (
    "https://raw.githubusercontent.com/"
    "festy1986/festy-epg/main/"
)


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

    "dynamic_major_channels_added": 0,

    "single_team_logo_found": 0,

    "single_team_logo_missing": 0,

    "provider_name_fallback_used": 0,

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
# Clean provider channel/event text for fallback use.
#
# This does not replace the existing matchup parser.
# It is used only when a normal A-vs-B matchup cannot
# be extracted, such as boxing, PPV, or named events.
# --------------------------------------------------

def extract_provider_event_text(text):

    if not text:

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
        r"\bstart\s*[:=]",
        text,
        maxsplit=1,
        flags=re.IGNORECASE
    )[0]


    text = re.split(
        r"\bstop\s*[:=]",
        text,
        maxsplit=1,
        flags=re.IGNORECASE
    )[0]


    text = re.sub(
        r"^(?:MLB|NBA|NFL|NHL)\s*[-:]?\s*",
        "",
        text,
        flags=re.IGNORECASE
    )


    text = re.sub(
        r"^(?:PPV\s+)?EVENT\s*\d*\s*[:|-]?\s*",
        "",
        text,
        flags=re.IGNORECASE
    )


    text = normalize_matchup(
        text
    )


    return clean_text(
        text
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


    # Remove provider scheduling metadata first.
    text = re.split(
        r"\bstart\s*[:=]",
        text,
        maxsplit=1,
        flags=re.IGNORECASE
    )[0]

    text = re.split(
        r"\bstop\s*[:=]",
        text,
        maxsplit=1,
        flags=re.IGNORECASE
    )[0]


    # Existing pipe-based names remain supported.
    if "|" in text:

        text = text.split(
            "|",
            1
        )[1]

    else:

        # Also support current provider names such as:
        # NBA 02: Knicks (NYK) x Timberwolves (MIN)
        # MLB 04 - Blue Jays x Red Sox
        text = re.sub(
            r"^(?:US\s*:\s*)?"
            r"(?:MLB|NBA|NFL|NHL)"
            r"(?:\s+(?:CHANNEL\s*)?\d+)?"
            r"\s*[-:|]\s*",
            "",
            text,
            flags=re.IGNORECASE
        )


    # Remove provider abbreviations such as (NYK), (MIN), etc.
    # The canonical team alias lookup supplies the full official names.
    text = re.sub(
        r"\s*\([A-Za-z0-9]{2,5}\)\s*",
        " ",
        text
    )


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
# Used only to determine the date ESPN should search.
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
# Download provider live categories.
#
# The original sports_channels.txt entries are kept.
# This only adds current MLB/NBA/NFL/NHL streams found
# by live category/group name or current channel name.
# --------------------------------------------------

category_names = {}


categories_url = (

    f"{XTREAM_URL}/player_api.php"

    f"?username={USERNAME}"

    f"&password={PASSWORD}"

    f"&action=get_live_categories"

)


try:

    categories_response = session.get(
        categories_url,
        timeout=(30, 120)
    )


    categories_response.raise_for_status()


    categories = categories_response.json()


    for category in categories:

        category_id = str(
            category.get(
                "category_id",
                ""
            )
        )


        category_name = clean_text(
            category.get(
                "category_name",
                ""
            )
        )


        if category_id:

            category_names[
                category_id
            ] = category_name


    print(
        f"Provider live categories: "
        f"{len(category_names)}"
    )


except Exception as e:

    print(
        "Unable to download provider live categories."
    )


    print(
        e
    )


# --------------------------------------------------
# Dynamically add all current major-league streams.
#
# XMLTV IDs remain the current provider stream IDs,
# preserving TiviMate matching.
# --------------------------------------------------

dynamic_major_channels_added = 0


for stream in streams:

    stream_id = str(
        stream.get(
            "stream_id",
            ""
        )
    )


    stream_name = clean_text(
        stream.get(
            "name",
            ""
        )
    )


    category_id = str(
        stream.get(
            "category_id",
            ""
        )
    )


    category_name = category_names.get(
        category_id,
        ""
    )


    detection_text = (

        f"{category_name} "

        f"{stream_name}"

    )


    if not re.search(
        r"\b(?:MLB|NBA|NFL|NHL)\b",
        detection_text,
        flags=re.IGNORECASE
    ):

        continue


    if stream_id not in wanted:

        wanted[
            stream_id
        ] = stream_name


        dynamic_major_channels_added += 1


debug_stats[
    "dynamic_major_channels_added"
] = dynamic_major_channels_added


print(
    f"Dynamic major-league channels added: "
    f"{dynamic_major_channels_added}"
)


print(
    f"Total sports channels selected: "
    f"{len(wanted)}"
)


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
# ESPN league configuration
# --------------------------------------------------

ESPN_LEAGUES = {

    "MLB": (

        "baseball",

        "mlb"

    ),

    "NBA": (

        "basketball",

        "nba"

    ),

    "NFL": (

        "football",

        "nfl"

    ),

    "NHL": (

        "hockey",

        "nhl"

    )

}


# --------------------------------------------------
# Parse ESPN event datetime
# --------------------------------------------------

def parse_espn_datetime(
    event
):

    event_date = event.get(
        "date"
    )


    if not event_date:

        debug_stats[
            "public_events_date_time_failed"
        ] += 1


        return None


    try:

        event_datetime = datetime.fromisoformat(

            event_date.replace(
                "Z",
                "+00:00"
            )

        )


    except ValueError:

        debug_stats[
            "public_events_date_time_failed"
        ] += 1


        return None


    return event_datetime.astimezone(

        ZoneInfo(
            "America/New_York"
        )

    )


# --------------------------------------------------
# ESPN scoreboard lookup
#
# ESPN IS USED ONLY TO:
#
# - Find the matching game
# - Return the game's verified start time
#
# It does NOT provide:
#
# - Displayed team names
# - Title cleanup
# - Description cleanup
# - Logo information
# --------------------------------------------------

def get_public_events(
    date_value,
    league_hint
):

    global public_api_lookups


    if league_hint not in ESPN_LEAGUES:

        return []


    sport, league = ESPN_LEAGUES[
        league_hint
    ]


    public_api_lookups += 1


    date_text = date_value.strftime(
        "%Y%m%d"
    )


    url = (

        "https://site.api.espn.com/apis/site/v2/sports/"

        f"{sport}/"

        f"{league}/"

        "scoreboard"

    )


    try:

        response = session.get(

            url,

            params={

                "dates": date_text

            },

            timeout=30

        )


        if response.status_code != 200:

            debug_stats[
                "public_events_empty"
            ] += 1


            print(

                f"[ESPN] HTTP "

                f"{response.status_code}"

            )


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
            "[ESPN API ERROR]"
        )


        print(
            e
        )


        return []


# --------------------------------------------------
# Find ESPN event
#
# The cleaned canonical matchup is used to find
# the game.
#
# ESPN's team names are ONLY used internally
# to verify that the correct event was found.
#
# They are NEVER written into the title or description.
# --------------------------------------------------

def find_public_event(

    canonical_matchup,

    preferred_date,

    league_hint

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
        "[ESPN LOOKUP]"
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

            date_value,

            league_hint

        )


        if not events:

            print(

                f"[ESPN] {date_value}: "

                f"no events returned"

            )


            continue


        print(

            f"[ESPN] {date_value}: "

            f"{len(events)} events"

        )


        for event in events:

            competitions = event.get(

                "competitions",

                []

            )


            if not competitions:

                continue


            competition = competitions[0]


            competitors = competition.get(

                "competitors",

                []

            )


            if len(competitors) < 2:

                continue


            event_teams = []


            for competitor in competitors:

                team = competitor.get(

                    "team",

                    {}

                )


                display_name = clean_text(

                    team.get(

                        "displayName",

                        ""

                    )

                )


                short_name = clean_text(

                    team.get(

                        "shortDisplayName",

                        ""

                    )

                )


                location = clean_text(

                    team.get(

                        "location",

                        ""

                    )

                )


                nickname = clean_text(

                    team.get(

                        "name",

                        ""

                    )

                )


                event_teams.append({

                    "display_name":

                    display_name,

                    "short_name":

                    short_name,

                    "location":

                    location,

                    "nickname":

                    nickname

                })


            if len(event_teams) < 2:

                continue


            event_team_names = []


            for team in event_teams:

                candidates = [

                    team["display_name"],

                    team["short_name"],

                    team["location"],

                    team["nickname"]

                ]


                event_team_names.append(

                    [

                        canonicalize_team_name(

                            candidate,

                            league_hint

                        )

                        for candidate in candidates

                        if candidate

                    ]

                )


            wanted_first_match = any(

                team_matches(

                    wanted_first,

                    candidate

                )

                for candidate in event_team_names[0]

            ) or any(

                team_matches(

                    wanted_first,

                    candidate

                )

                for candidate in event_team_names[1]

            )


            wanted_second_match = any(

                team_matches(

                    wanted_second,

                    candidate

                )

                for candidate in event_team_names[0]

            ) or any(

                team_matches(

                    wanted_second,

                    candidate

                )

                for candidate in event_team_names[1]

            )


            if not (

                wanted_first_match

                and

                wanted_second_match

            ):

                debug_stats[

                    "public_events_team_match_failed"

                ] += 1


                continue


            event_datetime = parse_espn_datetime(

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
                "[ESPN MATCH SUCCESS]"
            )


            print(
                f"  Clean matchup: "
                f"{canonical_matchup}"
            )


            print(
                "  ESPN event teams:"
            )


            for team in event_teams:

                print(

                    f"    {team['display_name']}"

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
        "[ESPN MATCH FAIL]"
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
# Find matchup logo by searching entire
# sports-logos directory.
#
# Independent of ESPN.
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
# Detect whether the current channel/event name is
# simply one known MLB/NBA/NFL/NHL team.
# --------------------------------------------------

def detect_single_team(
    provider_name,
    league_hint=None
):

    if not provider_name:

        return None


    # A matchup channel must be handled by the matchup-logo path,
    # never mistaken for one single team.
    if matchup_parts(
        normalize_matchup(
            re.sub(
                r"\s*\([A-Za-z0-9]{2,5}\)\s*",
                " ",
                clean_text(provider_name)
            )
        )
    ):

        return None


    candidate = clean_text(
        provider_name
    )


    # Remove provider prefixes, league labels, channel numbers,
    # and quality/feed markers without changing the display-name.
    candidate = re.sub(
        r"^(?:US|CA|UK)\s*:\s*",
        "",
        candidate,
        flags=re.IGNORECASE
    )

    candidate = re.sub(
        r"^(?:MLB|NBA|NFL|NHL)\s*:\s*",
        "",
        candidate,
        flags=re.IGNORECASE
    )

    candidate = re.sub(
        r"^(?:MLB|NBA|NFL|NHL)"
        r"(?:\s+(?:CHANNEL\s*)?\d+)?"
        r"\s*[-:|]?\s*",
        "",
        candidate,
        flags=re.IGNORECASE
    )

    candidate = re.sub(
        r"\b(?:RAW|HD|FHD|UHD|SD|4K|8K)\b",
        " ",
        candidate,
        flags=re.IGNORECASE
    )

    candidate = re.sub(
        r"[ᴿᴬᵂᴴᴰ⁴ᴷ⁸ᴷ]+",
        " ",
        candidate
    )

    candidate = clean_text(
        candidate
    )


    candidate_normalized = normalize_team_name(
        candidate
    )


    leagues = (

        [league_hint]

        if league_hint in team_aliases

        else list(
            SUPPORTED_MAJOR_LEAGUES
        )

    )


    for league in leagues:

        # First try an exact cleaned-name match.
        official_name = team_aliases[
            league
        ].get(
            candidate_normalized
        )


        if official_name:

            return (
                league,
                official_name
            )


        # Then search every known alias inside the current live-stream
        # name. This covers all provider groups and quality variants
        # while still using the current stream ID and current name.
        best_match = None
        best_length = 0

        for normalized_alias, official_name in team_aliases[
            league
        ].items():

            if not normalized_alias:

                continue

            if re.search(
                rf"(?:^|\s){re.escape(normalized_alias)}(?:$|\s)",
                candidate_normalized
            ):

                alias_length = len(
                    normalized_alias
                )

                if alias_length > best_length:

                    best_length = alias_length
                    best_match = official_name


        if best_match:

            return (
                league,
                best_match
            )


    return None


# --------------------------------------------------
# Find an existing single-team logo.
#
# Existing matchup-logo logic is left unchanged.
# This is used only when the entire channel/event name
# is detected as one known major-league team.
# --------------------------------------------------

def find_single_team_logo(
    official_team,
    league_hint
):

    global logos_found

    global logos_missing


    wanted_team = normalize_team_name(
        official_team
    )


    if not wanted_team:

        return None


    league_root = os.path.join(
        SPORTS_LOGO_ROOT,
        league_hint
    )


    if not os.path.isdir(
        league_root
    ):

        debug_stats[
            "single_team_logo_missing"
        ] += 1


        logos_missing += 1


        return None


    for root, directories, files in os.walk(
        league_root
    ):

        for filename in files:

            if not filename.lower().endswith(
                ".png"
            ):

                continue


            file_stem = os.path.splitext(
                filename
            )[0]


            if "_vs_" in file_stem.lower():

                continue


            file_team = normalize_team_name(
                file_stem.replace(
                    "_",
                    " "
                )
            )


            if file_team != wanted_team:

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


            debug_stats[
                "single_team_logo_found"
            ] += 1


            print()


            print(
                "[SINGLE TEAM LOGO FOUND]"
            )


            print(
                f"  Team: {official_team}"
            )


            print(
                f"  {relative_path}"
            )


            return logo_url


    debug_stats[
        "single_team_logo_missing"
    ] += 1


    logos_missing += 1


    return None



# --------------------------------------------------
# Build event information
#
# Order:
#
# 1. Read provider matchup
# 2. Clean team names using sports_teams.txt
# 3. Build title/description from those names
# 4. ESPN searches for the game time only
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
    # Extract provider matchup.
    # --------------------------------------------------

    provider_event = extract_provider_matchup(

        provider_name

    )


    provider_fallback_event = extract_provider_event_text(

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


    single_team = detect_single_team(

        provider_name,

        league_hint

    )


    # --------------------------------------------------
    # STEP 3:
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
    # Determine preferred date.
    #
    # Provider timestamp is used only to know which
    # date ESPN should search.
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
    # Build clean title and description BEFORE ESPN.
    # --------------------------------------------------

    if canonical_matchup:

        title_text = canonical_matchup


        description_text = (

            f"{canonical_matchup}\n"

            f"{preferred_date.strftime('%A')} "

            f"{preferred_date.strftime('%m/%d/%Y')}"

        )


    else:

        fallback_title = (

            provider_fallback_event

            or provider_name

            or "Sports Event"

        )


        if fallback_title != "Sports Event":

            debug_stats[
                "provider_name_fallback_used"
            ] += 1


        title_text = fallback_title


        description_text = (

            f"{fallback_title}\n"

            f"{preferred_date.strftime('%A')} "

            f"{preferred_date.strftime('%m/%d/%Y')}"

        )


    # --------------------------------------------------
    # STEP 6:
    # Find logo independently.
    #
    # This happens regardless of whether ESPN
    # finds the game.
    # --------------------------------------------------

    logo_url = None


    if canonical_matchup and league_hint:

        logo_url = find_matchup_logo(

            canonical_matchup,

            league_hint

        )


    elif single_team:

        single_team_league = single_team[
            0
        ]


        single_team_name = single_team[
            1
        ]


        logo_url = find_single_team_logo(

            single_team_name,

            single_team_league

        )


    # --------------------------------------------------
    # STEP 7:
    # ESPN is used ONLY to find the verified
    # game time.
    # --------------------------------------------------

    public_event = None


    if canonical_matchup and league_hint:

        public_event = find_public_event(

            canonical_matchup,

            preferred_date,

            league_hint

        )


    # --------------------------------------------------
    # STEP 8:
    # If ESPN found the game, add verified
    # Eastern time to BOTH title and description.
    #
    # Team names remain from sports_teams.txt.
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
    # ESPN failed.
    #
    # Keep clean title and description.
    #
    # Logo remains valid if found.
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
    # Add matchup or single-team logo to CHANNEL.
    #
    # Independent of ESPN success/failure.
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
    "ESPN statistics:"
)


print(

    f"Scoreboard API lookups: "

    f"{public_api_lookups}"

)


print(

    f"Verified ESPN event matches: "

    f"{public_api_matches}"

)


print(

    f"Verified ESPN times used: "

    f"{verified_public_times_used}"

)


print(

    f"No ESPN schedule match: "

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
