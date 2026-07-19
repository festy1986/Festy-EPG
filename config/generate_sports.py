import os
import re
import html
import time
import requests
import xml.etree.ElementTree as ET

from datetime import datetime, timedelta, timezone


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

    "provider_matchups_extracted": 0,

    "provider_matchups_failed": 0,

    "canonical_team_matches": 0,

    "canonical_team_failures": 0,

}


# --------------------------------------------------
# Clean text
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
# Normalize team name for matching
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


    text = re.sub(

        r"\s+",

        " ",

        text

    )


    return text.strip()


# --------------------------------------------------
# Extract the matchup from the provider channel name
#
# Example:
#
# MLB 04 | Rays x Red Sox start:2026-07-19 18:35:00 stop:2026-07-20 01:48:20
#
# becomes:
#
# Rays vs. Red Sox
#
# The start/stop data is NOT included.
# --------------------------------------------------

def extract_provider_matchup(text):

    if not text:

        debug_stats[

            "provider_matchups_failed"

        ] += 1


        return ""


    text = clean_text(

        text

    )


    if "|" not in text:

        debug_stats[

            "provider_matchups_failed"

        ] += 1


        return ""


    matchup = text.split(

        "|",

        1

    )[1]


    matchup = clean_text(

        matchup

    )


    matchup = re.split(

        r"\bstart\s*:",

        matchup,

        maxsplit=1,

        flags=re.IGNORECASE

    )[0]


    matchup = re.split(

        r"\bstop\s*:",

        matchup,

        maxsplit=1,

        flags=re.IGNORECASE

    )[0]


    matchup = clean_text(

        matchup

    )


    matchup = re.sub(

        r"\s+[xX]\s+",

        " vs. ",

        matchup

    )


    matchup = re.sub(

        r"\s+@\s+",

        " vs. ",

        matchup

    )


    matchup = re.sub(

        r"\s+v\.?\s+",

        " vs. ",

        matchup,

        flags=re.IGNORECASE

    )


    matchup = re.sub(

        r"\s+vs\.?\s+",

        " vs. ",

        matchup,

        flags=re.IGNORECASE

    )


    matchup = matchup.strip(

        " -|:;"

    )


    parts = matchup_parts(

        matchup

    )


    if len(parts) != 2:

        debug_stats[

            "provider_matchups_failed"

        ] += 1


        return ""


    debug_stats[

        "provider_matchups_extracted"

    ] += 1


    return (

        f"{parts[0]}"

        f" vs. "

        f"{parts[1]}"

    )


# --------------------------------------------------
# Split matchup into two teams
# --------------------------------------------------

def matchup_parts(text):

    if not text:

        return []


    text = clean_text(

        text

    )


    match = re.match(

        r"^(.+?)\s+vs\.\s+(.+?)$",

        text,

        flags=re.IGNORECASE

    )


    if not match:

        return []


    first = clean_text(

        match.group(1)

    )


    second = clean_text(

        match.group(2)

    )


    if not first or not second:

        return []


    return [

        first,

        second

    ]


# --------------------------------------------------
# SportsDB official team database
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

        "Loading official team names..."

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

                f"{len(teams)} teams"

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


load_sportsdb_teams()


# --------------------------------------------------
# Convert provider team name to official team name
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


        shared_words = (

            provider_words

            &

            alias_words

        )


        if not shared_words:

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


        elif (

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
# Convert complete matchup to official team names
# --------------------------------------------------

def canonicalize_matchup(matchup):

    parts = matchup_parts(

        matchup

    )


    if len(parts) != 2:

        return matchup


    first = canonicalize_team_name(

        parts[0]

    )


    second = canonicalize_team_name(

        parts[1]

    )


    return (

        f"{first}"

        f" vs. "

        f"{second}"

    )


# --------------------------------------------------
# Build cleaned title and description
#
# Example:
#
# Provider:
#
# MLB 04 | Rays x Red Sox start:2026-07-19 18:35:00 stop:2026-07-20 01:48:20
#
# Title:
#
# Tampa Bay Rays vs. Boston Red Sox
#
# Description:
#
# Tampa Bay Rays vs. Boston Red Sox
# Sunday 07/19/2026
# --------------------------------------------------

def build_event_info(

    stream,

    guide_date

):

    provider_name = clean_text(

        stream.get(

            "name",

            ""

        )

    )


    print()

    print(

        "=================================================="

    )


    print(

        f"Raw provider name:"

    )


    print(

        f"  {provider_name}"

    )


    extracted_matchup = (

        extract_provider_matchup(

            provider_name

        )

    )


    print()

    print(

        "Extracted matchup:"

    )


    print(

        f"  {extracted_matchup}"

    )


    if not extracted_matchup:

        return (

            "Sports Event",

            "Sports Event",

        )


    cleaned_matchup = (

        canonicalize_matchup(

            extracted_matchup

        )

    )


    print()

    print(

        "Cleaned matchup:"

    )


    print(

        f"  {cleaned_matchup}"

    )


    title_text = (

        cleaned_matchup

    )


    description_text = (

        f"{cleaned_matchup}\n"

        f"{guide_date.strftime('%A')} "

        f"{guide_date.strftime('%m/%d/%Y')}"

    )


    return (

        title_text,

        description_text

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

    .astimezone()

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


guide_date = guide_start.date()


# --------------------------------------------------
# Create channels
#
# IMPORTANT:
#
# The original provider channel name is preserved.
#
# The cleaned matchup is written into the
# programme title and description.
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
# for 3 days
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

        description_text

    ) = build_event_info(

        stream,

        guide_date

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
# Write XMLTV file
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


print(

    "Guide blocks: 6 hours each"

)


print(

    "Guide duration: 3 days"

)


print()

print(

    "Team name conversions: "

    f"{team_name_conversions}"

)


print()

print(

    "Detailed diagnostics:"

)


for key, value in debug_stats.items():

    print(

        f"{key}: {value}"

    )
