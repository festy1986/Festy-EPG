import os
import re
import html
import time
import requests
import xml.etree.ElementTree as ET

from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo


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
canonical_team_matches = 0
canonical_team_failures = 0
provider_event_extracted = 0
provider_event_failed = 0
provider_matchup_parts_failed = 0


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
#
# Example:
#
# MLB 04 | Rays x Red Sox start:2026-07-19 18:35:00
#
# becomes:
#
# Rays vs. Red Sox
# --------------------------------------------------

def extract_provider_matchup(text):

    global provider_event_extracted
    global provider_event_failed


    if not text:

        provider_event_failed += 1

        return ""


    text = clean_text(
        text
    )


    if "|" not in text:

        provider_event_failed += 1

        return ""


    matchup_text = text.split(
        "|",
        1
    )[1]


    matchup_text = re.split(
        r"\bstart\s*:",
        matchup_text,
        maxsplit=1,
        flags=re.IGNORECASE
    )[0]


    matchup_text = re.split(
        r"\bstop\s*:",
        matchup_text,
        maxsplit=1,
        flags=re.IGNORECASE
    )[0]


    matchup_text = normalize_matchup(
        matchup_text
    )


    parts = matchup_parts(
        matchup_text
    )


    if len(parts) != 2:

        provider_event_failed += 1

        return ""


    provider_event_extracted += 1


    return matchup_text


# --------------------------------------------------
# Extract matchup teams
# --------------------------------------------------

def matchup_parts(text):

    global provider_matchup_parts_failed


    if not text:

        provider_matchup_parts_failed += 1

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

        provider_matchup_parts_failed += 1

        return []


    first = clean_text(
        match.group(1)
    )


    second = clean_text(
        match.group(2)
    )


    if not first or not second:

        provider_matchup_parts_failed += 1

        return []


    return [
        first,
        second
    ]


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


                    normalized_alias = normalize_team_name(
                        alias
                    )


                    if not normalized_alias:
                        continue


                    team_aliases[
                        normalized_alias
                    ] = {

                        "name": official_name,

                        "league": league_folder

                    }


        except Exception as e:

            print(
                f"Unable to load "
                f"{league_folder} teams:"
            )


            print(
                e
            )


# --------------------------------------------------
# Convert provider team name to official team name
# --------------------------------------------------

def canonicalize_team_name(

    provider_team,

    league_hint=None

):

    global team_name_conversions
    global canonical_team_matches
    global canonical_team_failures


    provider_team = clean_text(
        provider_team
    )


    if not provider_team:

        canonical_team_failures += 1

        return provider_team


    normalized_provider = normalize_team_name(
        provider_team
    )


    if not normalized_provider:

        canonical_team_failures += 1

        return provider_team


    # --------------------------------------------------
    # Exact alias match
    # --------------------------------------------------

    exact = team_aliases.get(
        normalized_provider
    )


    if exact:

        if exact["name"] != provider_team:

            team_name_conversions += 1


        canonical_team_matches += 1


        return exact["name"]


    # --------------------------------------------------
    # Partial matching
    # --------------------------------------------------

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


        # Provider words are contained in official name

        if (

            meaningful_provider_words

            and

            meaningful_provider_words.issubset(
                alias_words
            )

        ):

            score = len(
                meaningful_provider_words
            ) * 10


            if score > best_score:

                best_score = score

                best_match = team_data


            continue


        # Official name words are contained in provider name

        if (

            meaningful_alias_words

            and

            meaningful_alias_words.issubset(
                provider_words
            )

        ):

            score = len(
                meaningful_alias_words
            ) * 10


            if score > best_score:

                best_score = score

                best_match = team_data


    if best_match:

        team_name_conversions += 1

        canonical_team_matches += 1


        return best_match["name"]


    canonical_team_failures += 1


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
# Load official teams
# --------------------------------------------------

load_sportsdb_teams()


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
#
# IMPORTANT:
#
# The provider display-name is kept exactly as
# provided by the provider.
#
# The cleaned matchup is written into the
# programme title and description instead.
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


    print(
        "Raw provider name:"
    )


    print(
        f"  {provider_name}"
    )


    # --------------------------------------------------
    # STEP 1
    #
    # Extract the two teams from the provider name.
    # --------------------------------------------------

    provider_matchup = extract_provider_matchup(

        provider_name

    )


    print(
        "Extracted matchup:"
    )


    print(
        f"  {provider_matchup}"
    )


    # --------------------------------------------------
    # STEP 2
    #
    # Convert abbreviated names to official names.
    #
    # Example:
    #
    # Rays x Red Sox
    #
    # becomes:
    #
    # Tampa Bay Rays vs. Boston Red Sox
    # --------------------------------------------------

    cleaned_matchup = canonicalize_matchup(

        provider_matchup

    )


    print(
        "Cleaned matchup:"
    )


    print(
        f"  {cleaned_matchup}"
    )


    # --------------------------------------------------
    # STEP 3
    #
    # Build the title.
    # --------------------------------------------------

    if cleaned_matchup:

        title_text = cleaned_matchup


    else:

        title_text = "Sports Event"


    # --------------------------------------------------
    # STEP 4
    #
    # Build the description.
    #
    # Example:
    #
    # Tampa Bay Rays vs. Boston Red Sox
    # Sunday 07/19/2026
    # --------------------------------------------------

    if cleaned_matchup:

        description_text = (

            f"{cleaned_matchup}\n"

            f"{guide_start.strftime('%A')} "

            f"{guide_start.strftime('%m/%d/%Y')}"

        )


    else:

        description_text = (

            f"Sports Event\n"

            f"{guide_start.strftime('%A')} "

            f"{guide_start.strftime('%m/%d/%Y')}"

        )


    # --------------------------------------------------
    # STEP 5
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


print()
print(
    "Team name conversions: "
    f"{team_name_conversions}"
)


print(
    "Canonical team matches: "
    f"{canonical_team_matches}"
)


print(
    "Canonical team failures: "
    f"{canonical_team_failures}"
)


print(
    "Provider matchups extracted: "
    f"{provider_event_extracted}"
)


print(
    "Provider matchups failed: "
    f"{provider_event_failed}"
)


print(
    "Matchup parts failed: "
    f"{provider_matchup_parts_failed}"
)


print()
print(
    "Sports guide generation complete."
)
