import os
import re
import shutil
import unicodedata
import json
import time

from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from collections import deque

import requests
from PIL import Image


# ============================================================
# CONFIG
# ============================================================

# ============================================================
# SPORTS-LOGOS
#
# The EXISTING sports-logos directory is used ONLY to discover:
#
#   - leagues
#   - team folder names
#
# The existing PNG artwork is NEVER used as the logo source.
#
# New logo artwork is downloaded from ESPN.
#
# A completely separate build is created and verified before
# sports-logos is replaced.
# ============================================================

ROOT = Path("sports-logos")

BUILD_ROOT = Path("_sports_logos_rebuild")

BACKUP_ROOT = Path("_sports_logos_old")

# Temporary directory containing the logos downloaded from ESPN.
DOWNLOAD_ROOT = Path("_sports_logo_downloads")

LEAGUES = {
    "MLB",
    "NBA",
    "NFL",
    "NHL",
}

BUILD_WORKERS = 8

DOWNLOAD_WORKERS = 8


# ============================================================
# ESPN SOURCES
# ============================================================

ESPN_API_BASE = (
    "https://site.api.espn.com/apis/site/v2/sports"
)

ESPN_LEAGUES = {
    "MLB": "baseball/mlb",
    "NBA": "basketball/nba",
    "NFL": "football/nfl",
    "NHL": "hockey/nhl",
}


# ============================================================
# HTTP SETTINGS
# ============================================================

REQUEST_TIMEOUT = 30

MAX_RETRIES = 4

RETRY_DELAY = 2

USER_AGENT = (
    "Mozilla/5.0 "
    "(Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 "
    "(KHTML, like Gecko) "
    "Chrome/151.0 Safari/537.36"
)

SESSION_HEADERS = {
    "User-Agent": USER_AGENT,
    "Accept": "*/*",
}


# ============================================================
# SOLO LOGO SETTINGS
# ============================================================

SOLO_SIZE = (1024, 1024)

# Artwork is allowed to occupy 90% of the canvas.
SOLO_LOGO_SCALE = 0.90


# ============================================================
# MATCHUP SETTINGS
# ============================================================

MATCHUP_SIZE = (1024, 512)

MATCHUP_LOGO_WIDTH_SCALE = 0.88

MATCHUP_LOGO_HEIGHT_SCALE = 0.88


# ============================================================
# BACKGROUND CLEANUP
# ============================================================

WHITE_THRESHOLD = 245

ALPHA_THRESHOLD = 8


# ============================================================
# NAME NORMALIZATION
# ============================================================

def clean_name(value):

    value = os.path.splitext(value)[0]

    value = value.replace("_", " ")

    value = unicodedata.normalize(
        "NFKD",
        value
    )

    value = "".join(
        c
        for c in value
        if not unicodedata.combining(c)
    )

    value = re.sub(
        r"[^a-zA-Z0-9 ]+",
        " ",
        value
    )

    value = re.sub(
        r"\s+",
        " ",
        value
    )

    return value.strip().lower()


def filesystem_name(team):

    team = os.path.splitext(team)[0]

    team = team.replace("_", " ")

    team = unicodedata.normalize(
        "NFKD",
        team
    )

    team = "".join(
        c
        for c in team
        if not unicodedata.combining(c)
    )

    team = re.sub(
        r"[^a-zA-Z0-9]+",
        "_",
        team
    )

    team = re.sub(
        r"_+",
        "_",
        team
    )

    return team.strip("_")


# ============================================================
# TEAM NAME ALIASES
#
# These handle common differences between our folder names
# and ESPN's names.
# ============================================================

TEAM_ALIASES = {

    "la clippers":
        "los angeles clippers",

    "la lakers":
        "los angeles lakers",

    "ny knicks":
        "new york knicks",

    "ny nets":
        "brooklyn nets",

    "sf giants":
        "san francisco giants",

    "kc royals":
        "kansas city royals",

    "tb rays":
        "tampa bay rays",

    "st louis cardinals":
        "st. louis cardinals",

    "sd padres":
        "san diego padres",

    "az diamondbacks":
        "arizona diamondbacks",

    "washington commanders":
        "washington commanders",

    "las vegas raiders":
        "las vegas raiders",

    "vegas golden knights":
        "vegas golden knights",

    "utah mammoth":
        "utah mammoth",

    "utah hockey club":
        "utah mammoth",
}


# ============================================================
# HTTP HELPERS
# ============================================================

def create_session():

    session = requests.Session()

    session.headers.update(
        SESSION_HEADERS
    )

    return session


def request_with_retry(
    session,
    url,
    stream=False
):

    last_error = None

    for attempt in range(
        1,
        MAX_RETRIES + 1
    ):

        try:

            response = session.get(
                url,
                timeout=REQUEST_TIMEOUT,
                stream=stream
            )

            response.raise_for_status()

            return response

        except Exception as exc:

            last_error = exc

            if attempt >= MAX_RETRIES:

                break

            print(
                f"Retrying request "
                f"({attempt}/{MAX_RETRIES - 1}): "
                f"{url}"
            )

            time.sleep(
                RETRY_DELAY * attempt
            )

    raise RuntimeError(
        f"Request failed after "
        f"{MAX_RETRIES} attempts: "
        f"{url} "
        f"-> {last_error}"
    )


# ============================================================
# DISCOVER TEAMS FROM EXISTING SPORTS-LOGOS
#
# IMPORTANT:
#
# Existing logo files are NOT read as artwork.
#
# Folder names are the authoritative list of teams.
# ============================================================

def discover_source_teams():

    teams_by_league = {
        league: {}
        for league in LEAGUES
    }

    if not ROOT.is_dir():

        raise RuntimeError(
            f"Sports logo directory does not exist: "
            f"{ROOT}"
        )

    for league in sorted(LEAGUES):

        league_root = (
            ROOT
            /
            league
        )

        if not league_root.is_dir():

            raise RuntimeError(
                f"Missing league directory: "
                f"{league_root}"
            )

        team_folders = sorted(
            path
            for path in league_root.iterdir()
            if path.is_dir()
        )

        if not team_folders:

            raise RuntimeError(
                f"No team folders found in "
                f"{league_root}"
            )

        for team_folder in team_folders:

            team_name = team_folder.name

            key = clean_name(
                team_name
            )

            if not key:

                raise RuntimeError(
                    f"Invalid team folder: "
                    f"{team_folder}"
                )

            if key in teams_by_league[league]:

                raise RuntimeError(
                    f"Duplicate team detected "
                    f"in {league}: "
                    f"{team_name}"
                )

            teams_by_league[league][key] = {
                "name": team_name,
                "folder": team_folder,
            }

    return teams_by_league


# ============================================================
# ESPN TEAM API
# ============================================================

def fetch_espn_teams(
    league
):

    endpoint = (
        f"{ESPN_API_BASE}/"
        f"{ESPN_LEAGUES[league]}/"
        f"teams?limit=1000"
    )

    print()
    print(
        f"Downloading ESPN {league} team data..."
    )

    session = create_session()

    response = request_with_retry(
        session,
        endpoint
    )

    data = response.json()

    sports = data.get(
        "sports",
        []
    )

    if not sports:

        raise RuntimeError(
            f"ESPN returned no sports data "
            f"for {league}"
        )

    leagues = sports[0].get(
        "leagues",
        []
    )

    if not leagues:

        raise RuntimeError(
            f"ESPN returned no league data "
            f"for {league}"
        )

    teams = leagues[0].get(
        "teams",
        []
    )

    if not teams:

        raise RuntimeError(
            f"ESPN returned no teams "
            f"for {league}"
        )

    result = []

    for item in teams:

        team = item.get(
            "team",
            {}
        )

        if not team:

            continue

        result.append(team)

    if not result:

        raise RuntimeError(
            f"ESPN returned no usable "
            f"teams for {league}"
        )

    print(
        f"ESPN returned {len(result)} "
        f"{league} teams."
    )

    return result


# ============================================================
# ESPN TEAM NAME INDEX
# ============================================================

def espn_team_names(team):

    values = []

    for key in (
        "displayName",
        "shortDisplayName",
        "name",
        "location",
        "abbreviation",
        "slug",
        "nickname",
    ):

        value = team.get(key)

        if value:

            values.append(
                clean_name(
                    str(value)
                )
            )

    return values


def normalized_team_key(
    value
):

    value = clean_name(
        value
    )

    if value in TEAM_ALIASES:

        value = TEAM_ALIASES[value]

    return value


# ============================================================
# FIND ESPN MATCH
# ============================================================

def find_espn_team(
    folder_name,
    espn_teams
):

    target = normalized_team_key(
        folder_name
    )

    exact_matches = []

    for team in espn_teams:

        names = espn_team_names(
            team
        )

        for name in names:

            if normalized_team_key(name) == target:

                exact_matches.append(
                    team
                )

                break

    if len(exact_matches) == 1:

        return exact_matches[0]

    if len(exact_matches) > 1:

        raise RuntimeError(
            f"Multiple ESPN teams matched "
            f"{folder_name}: "
            f"{exact_matches}"
        )

    # --------------------------------------------------------
    # Secondary matching.
    #
    # Compare normalized names after removing common
    # geographic words and punctuation.
    # --------------------------------------------------------

    def simplify(value):

        value = normalized_team_key(
            value
        )

        replacements = {
            "los angeles": "la",
            "new york": "ny",
            "san francisco": "sf",
            "tampa bay": "tb",
            "kansas city": "kc",
            "st louis": "st",
        }

        for old, new in replacements.items():

            value = value.replace(
                old,
                new
            )

        return value

    simplified_target = simplify(
        folder_name
    )

    matches = []

    for team in espn_teams:

        for name in espn_team_names(team):

            if simplify(name) == simplified_target:

                matches.append(
                    team
                )

                break

    if len(matches) == 1:

        return matches[0]

    if len(matches) > 1:

        raise RuntimeError(
            f"Multiple ESPN teams matched "
            f"{folder_name}: "
            f"{matches}"
        )

    return None


# ============================================================
# FIND ESPN LOGO URL
# ============================================================

def find_logo_url(
    espn_team
):

    logos = espn_team.get(
        "logos",
        []
    )

    if not logos:

        return None

    # Prefer the primary logo.
    for logo in logos:

        href = logo.get(
            "href"
        )

        if not href:

            continue

        rel = logo.get(
            "rel",
            []
        )

        if isinstance(rel, str):

            rel = [rel]

        if (
            "default"
            in
            [str(x).lower() for x in rel]
        ):

            return href

    # Otherwise use the first valid logo.
    for logo in logos:

        href = logo.get(
            "href"
        )

        if href:

            return href

    return None


# ============================================================
# DOWNLOAD ONE ESPN LOGO
# ============================================================

def download_espn_logo(
    league,
    team_name,
    espn_team
):

    logo_url = find_logo_url(
        espn_team
    )

    if not logo_url:

        raise RuntimeError(
            f"ESPN supplied no logo URL "
            f"for {league} / {team_name}"
        )

    destination_folder = (
        DOWNLOAD_ROOT
        /
        league
    )

    destination_folder.mkdir(
        parents=True,
        exist_ok=True
    )

    destination = (
        destination_folder
        /
        f"{filesystem_name(team_name)}.png"
    )

    session = create_session()

    response = request_with_retry(
        session,
        logo_url,
        stream=True
    )

    with open(
        destination,
        "wb"
    ) as output:

        for chunk in response.iter_content(
            chunk_size=1024 * 64
        ):

            if chunk:

                output.write(
                    chunk
                )

    # --------------------------------------------------------
    # Validate that the downloaded file is actually an image.
    # --------------------------------------------------------

    try:

        with Image.open(destination) as image:

            image.load()

            if (
                image.width <= 0
                or
                image.height <= 0
            ):

                raise RuntimeError(
                    "Invalid dimensions."
                )

    except Exception as exc:

        if destination.exists():

            destination.unlink()

        raise RuntimeError(
            f"Downloaded ESPN logo is not "
            f"a valid image: "
            f"{destination}: {exc}"
        )

    return destination


# ============================================================
# BUILD ESPN SOURCE LIBRARY
# ============================================================

def build_external_source_library(
    teams_by_league
):

    print()
    print("=" * 70)
    print("DOWNLOADING NEW LOGO SOURCES FROM ESPN")
    print("=" * 70)

    if DOWNLOAD_ROOT.exists():

        print()
        print(
            f"Removing previous ESPN download cache: "
            f"{DOWNLOAD_ROOT}"
        )

        shutil.rmtree(
            DOWNLOAD_ROOT
        )

    DOWNLOAD_ROOT.mkdir(
        parents=True,
        exist_ok=True
    )

    matched = {}

    for league in sorted(LEAGUES):

        print()
        print("=" * 70)
        print(
            f"GETTING ESPN {league} LOGOS"
        )
        print("=" * 70)

        espn_teams = fetch_espn_teams(
            league
        )

        league_matches = {}

        missing = []

        for team in sorted(
            teams_by_league[league].values(),
            key=lambda item: clean_name(
                item["name"]
            )
        ):

            team_name = team["name"]

            espn_team = find_espn_team(
                team_name,
                espn_teams
            )

            if espn_team is None:

                missing.append(
                    team_name
                )

                continue

            logo_url = find_logo_url(
                espn_team
            )

            if not logo_url:

                missing.append(
                    team_name
                )

                continue

            league_matches[
                clean_name(team_name)
            ] = {
                "name": team_name,
                "espn_team": espn_team,
                "url": logo_url,
            }

        if missing:

            print()
            print(
                f"ERROR: ESPN logos could not "
                f"be matched for {league}:"
            )

            for name in missing:

                print(
                    f"  - {name}"
                )

            raise RuntimeError(
                f"Aborting because {len(missing)} "
                f"{league} teams do not have "
                f"an unambiguous ESPN logo match."
            )

        # ----------------------------------------------------
        # Download concurrently.
        # ----------------------------------------------------

        jobs = []

        with ThreadPoolExecutor(
            max_workers=DOWNLOAD_WORKERS
        ) as executor:

            for team in sorted(
                teams_by_league[league].values(),
                key=lambda item: clean_name(
                    item["name"]
                )
            ):

                key = clean_name(
                    team["name"]
                )

                match = league_matches[key]

                jobs.append(
                    executor.submit(
                        download_espn_logo,
                        league,
                        team["name"],
                        match["espn_team"]
                    )
                )

            completed = 0

            for future in as_completed(jobs):

                path = future.result()

                completed += 1

                print(
                    f"[{completed}/{len(jobs)}] "
                    f"{league}: "
                    f"{path.name}"
                )

        matched[league] = league_matches

    print()
    print(
        "All requested teams were matched "
        "to ESPN logo sources."
    )

    return matched


# ============================================================
# LOAD IMAGE
# ============================================================

def load_image(
    source_path
):

    with Image.open(source_path) as image:

        image = image.convert(
            "RGBA"
        )

        image.load()

        return image.copy()


# ============================================================
# REMOVE EDGE-CONNECTED WHITE BACKGROUND
# ============================================================

def remove_edge_white_background(
    image
):

    image = image.convert(
        "RGBA"
    )

    width, height = image.size

    if width <= 0 or height <= 0:

        raise RuntimeError(
            "Invalid image dimensions."
        )

    pixels = image.load()

    visited = bytearray(
        width * height
    )

    queue = deque()

    def pixel_is_background(
        x,
        y
    ):

        r, g, b, a = pixels[x, y]

        if a <= ALPHA_THRESHOLD:

            return True

        return (
            r >= WHITE_THRESHOLD
            and
            g >= WHITE_THRESHOLD
            and
            b >= WHITE_THRESHOLD
        )

    def add_if_background(
        x,
        y
    ):

        index = (
            y * width
            +
            x
        )

        if visited[index]:

            return

        if not pixel_is_background(
            x,
            y
        ):

            return

        visited[index] = 1

        queue.append(
            (x, y)
        )

    # Seed all edges.
    for x in range(width):

        add_if_background(
            x,
            0
        )

        if height > 1:

            add_if_background(
                x,
                height - 1
            )

    for y in range(height):

        add_if_background(
            0,
            y
        )

        if width > 1:

            add_if_background(
                width - 1,
                y
            )

    # Flood fill.
    while queue:

        x, y = queue.popleft()

        neighbors = (
            (x - 1, y),
            (x + 1, y),
            (x, y - 1),
            (x, y + 1),
        )

        for nx, ny in neighbors:

            if (
                nx < 0
                or
                nx >= width
                or
                ny < 0
                or
                ny >= height
            ):

                continue

            add_if_background(
                nx,
                ny
            )

    # Make background transparent.
    for y in range(height):

        for x in range(width):

            index = (
                y * width
                +
                x
            )

            if visited[index]:

                r, g, b, a = pixels[x, y]

                pixels[x, y] = (
                    r,
                    g,
                    b,
                    0
                )

    return image


# ============================================================
# TRIM TRANSPARENT SPACE
# ============================================================

def trim_transparency(
    image
):

    image = image.convert(
        "RGBA"
    )

    alpha = image.getchannel(
        "A"
    )

    bbox = alpha.getbbox()

    if bbox:

        image = image.crop(
            bbox
        )

    return image


# ============================================================
# CLEAN DOWNLOADED ESPN LOGO
# ============================================================

def clean_source_logo(
    source_path
):

    image = load_image(
        source_path
    )

    # ESPN logos normally already have transparency.
    #
    # If a source happens to contain a white rectangular
    # background, remove only the edge-connected white area.
    image = remove_edge_white_background(
        image
    )

    image = trim_transparency(
        image
    )

    if (
        image.width <= 0
        or
        image.height <= 0
    ):

        raise RuntimeError(
            f"Logo became empty after cleanup: "
            f"{source_path}"
        )

    return image


# ============================================================
# FIT LOGO
# ============================================================

def fit_logo(
    image,
    max_width,
    max_height
):

    image = trim_transparency(
        image
    )

    if (
        image.width <= 0
        or
        image.height <= 0
    ):

        raise RuntimeError(
            "Invalid logo image."
        )

    scale = min(
        max_width / image.width,
        max_height / image.height
    )

    width = max(
        1,
        int(
            round(
                image.width * scale
            )
        )
    )

    height = max(
        1,
        int(
            round(
                image.height * scale
            )
        )
    )

    return image.resize(
        (width, height),
        Image.Resampling.LANCZOS
    )


# ============================================================
# BUILD SOLO LOGO
# ============================================================

def build_solo_logo_from_clean_image(
    image,
    destination
):

    image = trim_transparency(
        image
    )

    max_width = int(
        SOLO_SIZE[0]
        *
        SOLO_LOGO_SCALE
    )

    max_height = int(
        SOLO_SIZE[1]
        *
        SOLO_LOGO_SCALE
    )

    logo = fit_logo(
        image,
        max_width,
        max_height
    )

    canvas = Image.new(
        "RGBA",
        SOLO_SIZE,
        (0, 0, 0, 0)
    )

    x = (
        SOLO_SIZE[0]
        -
        logo.width
    ) // 2

    y = (
        SOLO_SIZE[1]
        -
        logo.height
    ) // 2

    canvas.alpha_composite(
        logo,
        (x, y)
    )

    destination.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    canvas.save(
        destination,
        "PNG",
        optimize=True
    )


# ============================================================
# BUILD MATCHUP
#
# HOME = LEFT
# AWAY = RIGHT
# ============================================================

def build_matchup(
    home_clean_logo,
    away_clean_logo,
    destination
):

    half_width = (
        MATCHUP_SIZE[0]
        //
        2
    )

    home = fit_logo(
        home_clean_logo,
        int(
            half_width
            *
            MATCHUP_LOGO_WIDTH_SCALE
        ),
        int(
            MATCHUP_SIZE[1]
            *
            MATCHUP_LOGO_HEIGHT_SCALE
        )
    )

    away = fit_logo(
        away_clean_logo,
        int(
            half_width
            *
            MATCHUP_LOGO_WIDTH_SCALE
        ),
        int(
            MATCHUP_SIZE[1]
            *
            MATCHUP_LOGO_HEIGHT_SCALE
        )
    )

    canvas = Image.new(
        "RGBA",
        MATCHUP_SIZE,
        (0, 0, 0, 0)
    )

    home_x = (
        half_width
        -
        home.width
    ) // 2

    home_y = (
        MATCHUP_SIZE[1]
        -
        home.height
    ) // 2

    away_x = (
        half_width
        +
        (
            half_width
            -
            away.width
        )
        //
        2
    )

    away_y = (
        MATCHUP_SIZE[1]
        -
        away.height
    ) // 2

    canvas.alpha_composite(
        home,
        (
            home_x,
            home_y
        )
    )

    canvas.alpha_composite(
        away,
        (
            away_x,
            away_y
        )
    )

    destination.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    canvas.save(
        destination,
        "PNG",
        optimize=True
    )


# ============================================================
# BUILD ONE TEAM FOLDER
# ============================================================

def build_team_folder(
    league,
    home_team,
    all_teams,
    source_paths,
    destination_league
):

    home_name = home_team["name"]

    home_key = clean_name(
        home_name
    )

    home_source = source_paths[
        league
    ][
        home_key
    ]

    home_clean_logo = clean_source_logo(
        home_source
    )

    home_folder = (
        destination_league
        /
        filesystem_name(home_name)
    )

    home_folder.mkdir(
        parents=True,
        exist_ok=True
    )

    # --------------------------------------------------------
    # SOLO
    # --------------------------------------------------------

    solo_path = (
        home_folder
        /
        f"{filesystem_name(home_name)}.png"
    )

    build_solo_logo_from_clean_image(
        home_clean_logo,
        solo_path
    )

    generated = 1

    # --------------------------------------------------------
    # MATCHUPS
    # --------------------------------------------------------

    for away_team in all_teams:

        away_name = away_team["name"]

        if (
            clean_name(away_name)
            ==
            home_key
        ):

            continue

        away_key = clean_name(
            away_name
        )

        away_source = source_paths[
            league
        ][
            away_key
        ]

        away_clean_logo = clean_source_logo(
            away_source
        )

        matchup_filename = (
            f"{filesystem_name(home_name)}"
            f"_vs_"
            f"{filesystem_name(away_name)}"
            f".png"
        )

        matchup_path = (
            home_folder
            /
            matchup_filename
        )

        build_matchup(
            home_clean_logo,
            away_clean_logo,
            matchup_path
        )

        generated += 1

    expected = len(
        all_teams
    )

    if generated != expected:

        raise RuntimeError(
            f"{league} / {home_name}: "
            f"generated {generated} files, "
            f"expected {expected}"
        )

    return (
        league,
        home_name,
        generated
    )


# ============================================================
# BUILD LEAGUE
# ============================================================

def build_league(
    league,
    teams,
    source_paths,
    build_root
):

    print()
    print("=" * 70)
    print(
        f"BUILDING {league}"
    )
    print("=" * 70)

    sorted_teams = sorted(
        teams.values(),
        key=lambda item: clean_name(
            item["name"]
        )
    )

    destination_league = (
        build_root
        /
        league
    )

    destination_league.mkdir(
        parents=True,
        exist_ok=True
    )

    expected_per_team = len(
        sorted_teams
    )

    expected_files = (
        len(sorted_teams)
        *
        expected_per_team
    )

    print()
    print(
        f"Teams: {len(sorted_teams)}"
    )

    print(
        f"Files per team folder: "
        f"{expected_per_team}"
    )

    print(
        f"Expected files: "
        f"{expected_files}"
    )

    jobs = []

    with ThreadPoolExecutor(
        max_workers=BUILD_WORKERS
    ) as executor:

        for home_team in sorted_teams:

            jobs.append(
                executor.submit(
                    build_team_folder,
                    league,
                    home_team,
                    sorted_teams,
                    source_paths,
                    destination_league
                )
            )

        completed = 0

        for future in as_completed(
            jobs
        ):

            (
                result_league,
                team_name,
                generated
            ) = future.result()

            completed += 1

            print(
                f"[{completed}/{len(sorted_teams)}] "
                f"{result_league}: "
                f"{team_name} "
                f"-> {generated} files"
            )

    # Verify count.
    actual_files = list(
        destination_league.rglob(
            "*.png"
        )
    )

    if len(actual_files) != expected_files:

        raise RuntimeError(
            f"{league}: generated "
            f"{len(actual_files)} files, "
            f"expected {expected_files}"
        )

    # Verify every team folder.
    for team in sorted_teams:

        team_name = team["name"]

        team_folder = (
            destination_league
            /
            filesystem_name(team_name)
        )

        if not team_folder.is_dir():

            raise RuntimeError(
                f"Missing team folder: "
                f"{team_folder}"
            )

        files = list(
            team_folder.glob(
                "*.png"
            )
        )

        if len(files) != expected_per_team:

            raise RuntimeError(
                f"{league} / {team_name}: "
                f"folder contains "
                f"{len(files)} files, "
                f"expected "
                f"{expected_per_team}"
            )

        solo = (
            team_folder
            /
            f"{filesystem_name(team_name)}.png"
        )

        if not solo.is_file():

            raise RuntimeError(
                f"Missing solo logo: "
                f"{solo}"
            )

        for opponent in sorted_teams:

            opponent_name = opponent["name"]

            if (
                clean_name(opponent_name)
                ==
                clean_name(team_name)
            ):

                continue

            matchup = (
                team_folder
                /
                (
                    f"{filesystem_name(team_name)}"
                    f"_vs_"
                    f"{filesystem_name(opponent_name)}"
                    f".png"
                )
            )

            if not matchup.is_file():

                raise RuntimeError(
                    f"Missing matchup: "
                    f"{matchup}"
                )

    print()
    print(
        f"{league} VERIFIED: "
        f"{len(sorted_teams)} team folders / "
        f"{expected_files} PNG files"
    )

    return expected_files


# ============================================================
# VERIFY GENERATED LIBRARY
# ============================================================

def verify_generated_library(
    build_root,
    teams_by_league
):

    print()
    print("=" * 70)
    print("VERIFYING COMPLETE GENERATED LIBRARY")
    print("=" * 70)

    total_expected = 0
    total_found = 0

    for league in sorted(LEAGUES):

        teams = teams_by_league[
            league
        ]

        expected = (
            len(teams)
            *
            len(teams)
        )

        league_root = (
            build_root
            /
            league
        )

        files = list(
            league_root.rglob(
                "*.png"
            )
        )

        print(
            f"{league}: "
            f"{len(files)}/{expected}"
        )

        if len(files) != expected:

            raise RuntimeError(
                f"{league}: expected "
                f"{expected} PNG files but "
                f"found {len(files)}"
            )

        for path in files:

            try:

                with Image.open(
                    path
                ) as image:

                    image.verify()

                with Image.open(
                    path
                ) as image:

                    if image.mode != "RGBA":

                        raise RuntimeError(
                            f"Image is not RGBA: "
                            f"{path}"
                        )

            except Exception as exc:

                raise RuntimeError(
                    f"Invalid generated image "
                    f"{path}: {exc}"
                )

        total_expected += expected

        total_found += len(files)

    print()
    print(
        f"TOTAL: {total_found}/"
        f"{total_expected} PNG files verified."
    )

    if total_found != total_expected:

        raise RuntimeError(
            "Final generated file count does "
            "not match expected count."
        )


# ============================================================
# VERIFY TRANSPARENCY
# ============================================================

def verify_transparency(
    build_root
):

    print()
    print("=" * 70)
    print("VERIFYING TRANSPARENT BACKGROUNDS")
    print("=" * 70)

    checked = 0

    for path in build_root.rglob(
        "*.png"
    ):

        with Image.open(
            path
        ) as image:

            image = image.convert(
                "RGBA"
            )

            alpha = image.getchannel(
                "A"
            )

            minimum, maximum = (
                alpha.getextrema()
            )

            if minimum != 0:

                raise RuntimeError(
                    f"No transparent pixels "
                    f"found in: {path}"
                )

        checked += 1

    print()
    print(
        f"Transparency verified on "
        f"{checked} PNG files."
    )


# ============================================================
# VERIFY DIMENSIONS
# ============================================================

def verify_dimensions(
    build_root
):

    print()
    print("=" * 70)
    print("VERIFYING OUTPUT DIMENSIONS")
    print("=" * 70)

    solo_count = 0
    matchup_count = 0

    for path in build_root.rglob(
        "*.png"
    ):

        with Image.open(
            path
        ) as image:

            actual = (
                image.width,
                image.height
            )

            if "_vs_" in path.stem:

                expected = MATCHUP_SIZE

                matchup_count += 1

            else:

                expected = SOLO_SIZE

                solo_count += 1

            if actual != expected:

                raise RuntimeError(
                    f"Wrong dimensions: "
                    f"{path} is {actual}, "
                    f"expected {expected}"
                )

    print()
    print(
        f"Solo logos verified: "
        f"{solo_count}"
    )

    print(
        f"Matchup logos verified: "
        f"{matchup_count}"
    )


# ============================================================
# VERIFY SOURCE DOWNLOADS
# ============================================================

def verify_downloaded_sources(
    source_paths,
    teams_by_league
):

    print()
    print("=" * 70)
    print("VERIFYING DOWNLOADED ESPN SOURCES")
    print("=" * 70)

    total = 0

    for league in sorted(LEAGUES):

        for team in teams_by_league[
            league
        ].values():

            team_name = team["name"]

            key = clean_name(
                team_name
            )

            source = source_paths[
                league
            ][
                key
            ]

            if not source.is_file():

                raise RuntimeError(
                    f"Missing ESPN source: "
                    f"{source}"
                )

            try:

                with Image.open(
                    source
                ) as image:

                    image.load()

                    if (
                        image.width <= 0
                        or
                        image.height <= 0
                    ):

                        raise RuntimeError(
                            "Invalid dimensions."
                        )

            except Exception as exc:

                raise RuntimeError(
                    f"Invalid ESPN source "
                    f"{source}: {exc}"
                )

            total += 1

    print()
    print(
        f"Verified {total} ESPN logo sources."
    )


# ============================================================
# INSTALL
# ============================================================

def install_new_library():

    if BACKUP_ROOT.exists():

        shutil.rmtree(
            BACKUP_ROOT
        )

    print()
    print("=" * 70)
    print("INSTALLING NEW SPORTS LOGO LIBRARY")
    print("=" * 70)

    if ROOT.exists():

        print(
            "Moving existing sports-logos "
            "to temporary backup."
        )

        ROOT.rename(
            BACKUP_ROOT
        )

    try:

        BUILD_ROOT.rename(
            ROOT
        )

    except Exception:

        if (
            BACKUP_ROOT.exists()
            and
            not ROOT.exists()
        ):

            BACKUP_ROOT.rename(
                ROOT
            )

        raise

    if BACKUP_ROOT.exists():

        shutil.rmtree(
            BACKUP_ROOT
        )

    print()
    print(
        "New sports-logos library installed."
    )


# ============================================================
# VERIFY INSTALLED LIBRARY
# ============================================================

def verify_installed_library(
    teams_by_league
):

    print()
    print("=" * 70)
    print("VERIFYING INSTALLED SPORTS LOGO LIBRARY")
    print("=" * 70)

    total_expected = 0
    total_found = 0

    for league in sorted(LEAGUES):

        teams = teams_by_league[
            league
        ]

        expected = (
            len(teams)
            *
            len(teams)
        )

        league_root = (
            ROOT
            /
            league
        )

        if not league_root.is_dir():

            raise RuntimeError(
                f"Missing installed league: "
                f"{league_root}"
            )

        files = list(
            league_root.rglob(
                "*.png"
            )
        )

        if len(files) != expected:

            raise RuntimeError(
                f"{league}: installed "
                f"{len(files)} files, "
                f"expected {expected}"
            )

        for team in teams.values():

            team_name = team["name"]

            team_folder = (
                league_root
                /
                filesystem_name(
                    team_name
                )
            )

            if not team_folder.is_dir():

                raise RuntimeError(
                    f"Missing installed team "
                    f"folder: {team_folder}"
                )

            solo = (
                team_folder
                /
                f"{filesystem_name(team_name)}.png"
            )

            if not solo.is_file():

                raise RuntimeError(
                    f"Missing installed solo "
                    f"logo: {solo}"
                )

            for opponent in teams.values():

                opponent_name = (
                    opponent["name"]
                )

                if (
                    clean_name(
                        opponent_name
                    )
                    ==
                    clean_name(
                        team_name
                    )
                ):

                    continue

                matchup = (
                    team_folder
                    /
                    (
                        f"{filesystem_name(team_name)}"
                        f"_vs_"
                        f"{filesystem_name(opponent_name)}"
                        f".png"
                    )
                )

                if not matchup.is_file():

                    raise RuntimeError(
                        f"Missing installed "
                        f"matchup: {matchup}"
                    )

        print(
            f"{league}: "
            f"{len(files)}/{expected} verified"
        )

        total_expected += expected

        total_found += len(files)

    print()
    print(
        f"Installed library verified: "
        f"{total_found}/{total_expected} files."
    )

    if total_found != total_expected:

        raise RuntimeError(
            "Installed library verification failed."
        )


# ============================================================
# CLEANUP DOWNLOAD CACHE
# ============================================================

def cleanup_download_cache():

    if DOWNLOAD_ROOT.exists():

        print()
        print(
            f"Removing temporary ESPN source cache: "
            f"{DOWNLOAD_ROOT}"
        )

        shutil.rmtree(
            DOWNLOAD_ROOT
        )


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 70)
    print("ESPN SPORTS LOGO DOWNLOADER / CLEANER / REBUILDER")
    print("=" * 70)

    print()
    print("TEAM LIST SOURCE:")
    print(
        "  Existing sports-logos folder names"
    )

    print()
    print("LOGO ARTWORK SOURCE:")
    print(
        "  ESPN team logo data"
    )

    print()
    print("FINAL OUTPUT:")
    print(
        "  sports-logos/<LEAGUE>/<TEAM>/"
    )

    print()
    print("PROCESS:")
    print(
        "  Existing PNG artwork is NOT used."
    )

    print(
        "  Existing matchup files are NOT used."
    )

    print(
        "  Team folders are used only to determine "
        "which teams must be rebuilt."
    )

    print(
        "  ESPN supplies the new logo artwork."
    )

    print(
        "  Downloaded logos are converted to RGBA."
    )

    print(
        "  Edge-connected white backgrounds are removed."
    )

    print(
        "  Logos are tightly cropped."
    )

    print(
        "  Solo logos become 1024x1024 transparent PNGs."
    )

    print(
        "  Matchups become 1024x512 transparent PNGs."
    )

    print(
        "  Home team is always on the LEFT."
    )

    print(
        "  Away team is always on the RIGHT."
    )

    print(
        "  Every team gets every other team in its league."
    )

    print()
    print("SAFETY:")
    print(
        "  The existing sports-logos directory is never "
        "modified during construction."
    )

    print(
        "  A separate build is created first."
    )

    print(
        "  The build is completely verified before installation."
    )

    print(
        "  If even ONE team cannot be matched to an ESPN logo, "
        "the entire run stops."
    )

    print(
        "  The old sports-logos library remains untouched "
        "if anything fails."
    )

    print()
    print(
        f"Build workers: {BUILD_WORKERS}"
    )

    print(
        f"Download workers: {DOWNLOAD_WORKERS}"
    )

    print(
        f"Solo size: "
        f"{SOLO_SIZE[0]}x{SOLO_SIZE[1]}"
    )

    print(
        f"Solo artwork scale: "
        f"{int(SOLO_LOGO_SCALE * 100)}%"
    )

    print(
        f"Matchup size: "
        f"{MATCHUP_SIZE[0]}x{MATCHUP_SIZE[1]}"
    )

    # --------------------------------------------------------
    # Remove incomplete previous build.
    # --------------------------------------------------------

    if BUILD_ROOT.exists():

        print()
        print(
            f"Removing previous incomplete build: "
            f"{BUILD_ROOT}"
        )

        shutil.rmtree(
            BUILD_ROOT
        )

    # --------------------------------------------------------
    # Discover teams from existing library.
    # --------------------------------------------------------

    teams_by_league = (
        discover_source_teams()
    )

    total_teams = sum(
        len(teams)
        for teams in teams_by_league.values()
    )

    print()
    print("=" * 70)
    print("TEAMS DISCOVERED")
    print("=" * 70)

    for league in sorted(LEAGUES):

        print(
            f"{league}: "
            f"{len(teams_by_league[league])} teams"
        )

    print()
    print(
        f"TOTAL TEAMS: {total_teams}"
    )

    # --------------------------------------------------------
    # Download completely new logo sources.
    # --------------------------------------------------------

    external_matches = (
        build_external_source_library(
            teams_by_league
        )
    )

    # --------------------------------------------------------
    # Build exact source path map.
    # --------------------------------------------------------

    source_paths = {
        league: {}
        for league in LEAGUES
    }

    for league in sorted(LEAGUES):

        for team in teams_by_league[
            league
        ].values():

            team_name = team["name"]

            key = clean_name(
                team_name
            )

            path = (
                DOWNLOAD_ROOT
                /
                league
                /
                f"{filesystem_name(team_name)}.png"
            )

            source_paths[
                league
            ][
                key
            ] = path

    verify_downloaded_sources(
        source_paths,
        teams_by_league
    )

    # --------------------------------------------------------
    # Calculate expected output.
    # --------------------------------------------------------

    print()
    print("=" * 70)
    print("EXPECTED OUTPUT")
    print("=" * 70)

    total_expected = 0

    for league in sorted(LEAGUES):

        count = len(
            teams_by_league[
                league
            ]
        )

        expected = (
            count
            *
            count
        )

        print(
            f"{league}: "
            f"{count} teams -> "
            f"{count} folders -> "
            f"{expected} files"
        )

        total_expected += expected

    print()
    print(
        f"TOTAL PNG FILES: "
        f"{total_expected}"
    )

    # --------------------------------------------------------
    # Build completely separate library.
    # --------------------------------------------------------

    generated_total = 0

    for league in sorted(LEAGUES):

        generated_total += build_league(
            league,
            teams_by_league[league],
            source_paths,
            BUILD_ROOT
        )

    # --------------------------------------------------------
    # Verify build.
    # --------------------------------------------------------

    verify_generated_library(
        BUILD_ROOT,
        teams_by_league
    )

    verify_transparency(
        BUILD_ROOT
    )

    verify_dimensions(
        BUILD_ROOT
    )

    # --------------------------------------------------------
    # INSTALL ONLY AFTER EVERYTHING PASSES.
    # --------------------------------------------------------

    install_new_library()

    # --------------------------------------------------------
    # Verify installed result.
    # --------------------------------------------------------

    verify_installed_library(
        teams_by_league
    )

    # --------------------------------------------------------
    # Remove temporary downloaded source logos.
    # --------------------------------------------------------

    cleanup_download_cache()

    # --------------------------------------------------------
    # FINAL REPORT.
    # --------------------------------------------------------

    print()
    print("=" * 70)
    print("FINISHED SUCCESSFULLY")
    print("=" * 70)

    print()
    print(
        f"Teams rebuilt: {total_teams}"
    )

    print(
        f"PNG files generated: "
        f"{generated_total}"
    )

    print(
        f"PNG files expected:  "
        f"{total_expected}"
    )

    print()
    print(
        "NEW logo artwork came from ESPN."
    )

    print(
        "Existing sports-logos PNG artwork "
        "was not used as the source."
    )

    print(
        "Existing matchup PNGs were not used."
    )

    print(
        "White edge-connected backgrounds "
        "were removed."
    )

    print(
        "Solo logos were rendered as "
        "1024x1024 transparent PNGs."
    )

    print(
        "Matchup logos were rendered as "
        "1024x512 transparent PNGs."
    )

    print(
        "Every team has a matchup against "
        "every other team in its league."
    )

    print(
        "Both matchup directions were generated."
    )

    print()
    print(
        "The rebuilt sports-logos library "
        "was installed only after verification."
    )


if __name__ == "__main__":

    main()
