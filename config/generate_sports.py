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
        "User-Agent": "Mozilla/5.0"
    }
)


# --------------------------------------------------
# Statistics
# --------------------------------------------------

team_name_conversions = 0

debug_stats = {

    "provider_event_extracted": 0,

    "provider_event_failed": 0,

    "provider_matchup_parts_failed": 0,

    "canonical_team_matches": 0,

    "canonical_team_failures": 0,

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
#
# Examples:
#
# Rays x Red Sox
# Rays @ Red Sox
# Rays v Red Sox
# Rays vs Red Sox
#
# becomes:
#
# Rays vs. Red Sox
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
# Extract the matchup from the provider channel name
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
# The provider timestamp is NOT used.
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
# Extract matchup teams
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
# SportsDB leagues
# --------------------------------------------------

SPORTSDB_LEAGUES = {

    "MLB": "MLB",

    "NBA": "NBA",

    "NFL": "NFL",

    "NHL": "NHL"

}


team_aliases = {}


# --------------------------------------------------
# Load official team names
# --------------------------------------------------

def load_sportsdb_teams():

    print()

    print(

        "Loading official team names from TheSportsDB..."

    )


    url = (

        "https://www.thesportsdb.com/"

        "api/v1/json/123/"

        "search_all_teams.php"

    )


    for league_folder, league_name in SPORTSDB_LEAGUES.items():

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


                    normalized_alias = (

                        normalize_team_name(

                            alias

                        )

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

            print()

            print(

                f"Unable to load "

                f"{league_folder} teams:"

            )


            print(

                e

            )


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


    normalized_provider = (

        normalize_team_name(

            provider_team

        )

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
# Canonicalize the entire matchup
#
# Example:
#
# Rays vs. Red Sox
#
# becomes:
#
# Tampa Bay Rays vs. Boston Red Sox
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


print()

print(

    f"Requested channels: "

    f"{len(wanted)}"

)


# --------------------------------------------------
# Download provider channels
# --------------------------------------------------

print()

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

        print()

        print(

            f"Downloading provider channels "

            f"(attempt {attempt}/5)..."

        )


        response = session.get(

            url,

            timeout=(

                30,

                600

            )

        )


        response.raise_for_status()


        streams = response.json()


        break


    except Exception as e:

        print()

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

    print()

    print(

        "Unable to download provider channels."

    )


    raise SystemExit(

        1

    )


print()

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
# Load official team names
# --------------------------------------------------

load_sportsdb_teams()


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
#
# 3 full days
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


    display.text = clean_text(

        provider_name

    )


# --------------------------------------------------
# Create 6-hour programme blocks
#
# 3 days
#
# 12 blocks per channel
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


    provider_name = clean_text(

        stream.get(

            "name",

            ""

        )

    )


    print()

    print(

        f"Processing {channel_id}"

    )


    print(

        "=================================================="

    )


    print(

        f"[CHANNEL {channel_id}]"

    )


    print()

    print(

        "Raw provider name:"

    )


    print(

        f"  {provider_name}"

    )


    # --------------------------------------------------
    # STEP 1
    #
    # Extract the teams from the provider channel name.
    #
    # No time lookup.
    # No logo lookup.
    # No provider-time fallback.
    # --------------------------------------------------

    provider_matchup = extract_provider_matchup(

        provider_name

    )


    print()

    print(

        "Extracted matchup:"

    )


    print(

        f"  {provider_matchup}"

    )


    # --------------------------------------------------
    # STEP 2
    #
    # Convert the extracted team names into official names.
    # --------------------------------------------------

    if provider_matchup:

        cleaned_matchup = canonicalize_matchup(

            provider_matchup

        )


    else:

        cleaned_matchup = ""


    print()

    print(

        "Cleaned matchup:"

    )


    print(

        f"  {cleaned_matchup}"

    )


    # --------------------------------------------------
    # STEP 3
    #
    # Create title and description.
    #
    # Example:
    #
    # Title:
    # Tampa Bay Rays vs. Boston Red Sox
    #
    # Description:
    # Tampa Bay Rays vs. Boston Red Sox
    # Sunday 07/19/2026
    # --------------------------------------------------

    if cleaned_matchup:

        title_text = (

            cleaned_matchup

        )


        description_text = (

            f"{cleaned_matchup}\n"

            f"{guide_start.strftime('%A')} "

            f"{guide_start.strftime('%m/%d/%Y')}"

        )


    else:

        title_text = (

            "Sports Event"

        )


        description_text = (

            "Sports Event\n"

            f"{guide_start.strftime('%A')} "

            f"{guide_start.strftime('%m/%d/%Y')}"

        )


    print()

    print(

        "Final title:"

    )


    print(

        f"  {title_text}"

    )


    print()

    print(

        "Final description:"

    )


    print(

        f"  {description_text}"

    )


    # --------------------------------------------------
    # STEP 4
    #
    # Create 6-hour blocks for 3 days.
    # --------------------------------------------------

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


print()

print(

    f"Matched channels: "

    f"{matched}"

)


print()

print(

    "Guide blocks: "

    "6 hours each"

)


print()

print(

    "Guide duration: "

    "3 days"

)


print()

print(

    "Team name conversions: "

    f"{team_name_conversions}"

)


print()

print(

    "Detailed cleanup diagnostics:"

)


for key, value in debug_stats.items():

    print(

        f"{key}: {value}"

    )
