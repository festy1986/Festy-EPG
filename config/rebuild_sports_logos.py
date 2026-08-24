import os
import re
import shutil
import unicodedata
import time

from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests
from PIL import Image


# ============================================================
# CONFIG
# ============================================================

ROOT = Path("sports-logos")

BUILD_ROOT = Path("_sports_logos_rebuild")

BACKUP_ROOT = Path("_sports_logos_old")

LEAGUES = {
    "MLB",
    "NBA",
    "NFL",
    "NHL",
}

BUILD_WORKERS = 8


# ============================================================
# NETWORK SETTINGS
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


# ============================================================
# MATCHUP SETTINGS
#
# IMPORTANT:
#
# ESPN solo logos are NEVER resized.
#
# They remain at their native ESPN CDN dimensions.
#
# Matchup images use a 1024x512 transparent canvas.
#
# Native ESPN logos are placed on that canvas without
# enlargement.
#
# A small edge margin guarantees that no logo touches the
# outer edge of the matchup canvas.
# ============================================================

MATCHUP_SIZE = (1024, 512)

MATCHUP_LOGO_WIDTH_SCALE = 0.88
MATCHUP_LOGO_HEIGHT_SCALE = 0.88

MATCHUP_EDGE_MARGIN = 2


# ============================================================
# ESPN CDN
# ============================================================

ESPN_CDN_BASE = (
    "https://a.espncdn.com/i/teamlogos"
)

ESPN_CDN_SCOREBOARD_BASE = (
    "https://a.espncdn.com/i/teamlogos"
)


# ============================================================
# ESPN TEAM ABBREVIATIONS
#
# No ESPN team-data API is used.
#
# The existing team folders provide the roster.
#
# This mapping determines the direct ESPN CDN logo URL.
# ============================================================

ESPN_CODES = {

    # ========================================================
    # MLB
    # ========================================================

    "arizona diamondbacks": "ari",
    "atlanta braves": "atl",
    "baltimore orioles": "bal",
    "boston red sox": "bos",
    "chicago cubs": "chc",
    "chicago white sox": "chw",
    "cincinnati reds": "cin",
    "cleveland guardians": "cle",
    "colorado rockies": "col",
    "detroit tigers": "det",
    "houston astros": "hou",
    "kansas city royals": "kc",
    "los angeles angels": "laa",
    "los angeles dodgers": "lad",
    "miami marlins": "mia",
    "milwaukee brewers": "mil",
    "minnesota twins": "min",
    "new york mets": "nym",
    "new york yankees": "nyy",
    "oakland athletics": "oak",
    "athletics": "oak",
    "philadelphia phillies": "phi",
    "pittsburgh pirates": "pit",
    "san diego padres": "sd",
    "san francisco giants": "sf",
    "seattle mariners": "sea",
    "st louis cardinals": "stl",
    "tampa bay rays": "tb",
    "texas rangers": "tex",
    "toronto blue jays": "tor",
    "washington nationals": "wsh",

    "cleveland indians": "cle",
    "tampa bay devil rays": "tb",

    # ========================================================
    # NBA
    # ========================================================

    "atlanta hawks": "atl",
    "boston celtics": "bos",
    "brooklyn nets": "bkn",
    "charlotte hornets": "cha",
    "chicago bulls": "chi",
    "cleveland cavaliers": "cle",
    "dallas mavericks": "dal",
    "denver nuggets": "den",
    "detroit pistons": "det",
    "golden state warriors": "gs",
    "houston rockets": "hou",
    "indiana pacers": "ind",
    "la clippers": "lac",
    "los angeles clippers": "lac",
    "los angeles lakers": "lal",
    "memphis grizzlies": "mem",
    "miami heat": "mia",
    "milwaukee bucks": "mil",
    "minnesota timberwolves": "min",
    "new orleans pelicans": "no",
    "new york knicks": "ny",
    "oklahoma city thunder": "okc",
    "orlando magic": "orl",
    "philadelphia 76ers": "phi",
    "phoenix suns": "phx",
    "portland trail blazers": "por",
    "sacramento kings": "sac",
    "san antonio spurs": "sa",
    "toronto raptors": "tor",
    "utah jazz": "utah",
    "washington wizards": "wsh",

    "golden state": "gs",
    "oklahoma city": "okc",
    "philadelphia sixers": "phi",

    # ========================================================
    # NFL
    # ========================================================

    "arizona cardinals": "ari",
    "atlanta falcons": "atl",
    "baltimore ravens": "bal",
    "buffalo bills": "buf",
    "carolina panthers": "car",
    "chicago bears": "chi",
    "cincinnati bengals": "cin",
    "cleveland browns": "cle",
    "dallas cowboys": "dal",
    "denver broncos": "den",
    "detroit lions": "det",
    "green bay packers": "gb",
    "houston texans": "hou",
    "indianapolis colts": "ind",
    "jacksonville jaguars": "jax",
    "kansas city chiefs": "kc",
    "las vegas raiders": "lv",
    "los angeles chargers": "lac",
    "los angeles rams": "lar",
    "miami dolphins": "mia",
    "minnesota vikings": "min",
    "new england patriots": "ne",
    "new orleans saints": "no",
    "new york giants": "nyg",
    "new york jets": "nyj",
    "philadelphia eagles": "phi",
    "pittsburgh steelers": "pit",
    "san francisco 49ers": "sf",
    "seattle seahawks": "sea",
    "tampa bay buccaneers": "tb",
    "tennessee titans": "ten",
    "washington commanders": "wsh",

    "washington football team": "wsh",
    "washington redskins": "wsh",
    "oakland raiders": "lv",
    "st louis rams": "lar",
    "san diego chargers": "lac",

    # ========================================================
    # NHL
    # ========================================================

    "anaheim ducks": "ana",
    "boston bruins": "bos",
    "buffalo sabres": "buf",
    "calgary flames": "cgy",
    "carolina hurricanes": "car",
    "chicago blackhawks": "chi",
    "colorado avalanche": "col",
    "columbus blue jackets": "cbj",
    "dallas stars": "dal",
    "detroit red wings": "det",
    "edmonton oilers": "edm",
    "florida panthers": "fla",
    "los angeles kings": "la",
    "minnesota wild": "min",
    "montreal canadiens": "mtl",
    "nashville predators": "nsh",
    "new jersey devils": "nj",
    "new york islanders": "nyi",
    "new york rangers": "nyr",
    "ottawa senators": "ott",
    "philadelphia flyers": "phi",
    "pittsburgh penguins": "pit",
    "san jose sharks": "sj",
    "seattle kraken": "sea",
    "st louis blues": "stl",
    "tampa bay lightning": "tb",
    "toronto maple leafs": "tor",
    "utah mammoth": "uta",
    "vancouver canucks": "van",
    "vegas golden knights": "vgk",
    "washington capitals": "wsh",
    "winnipeg jets": "wpg",

    "arizona coyotes": "ari",
    "phoenix coyotes": "ari",
    "utah hockey club": "uta",
}


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
# ESPN CODE LOOKUP
# ============================================================

def get_espn_code(
    league,
    team_name
):

    key = clean_name(team_name)

    code = ESPN_CODES.get(key)

    if code:

        return code

    raise RuntimeError(
        f"No ESPN CDN code is configured for "
        f"{league} team: {team_name}"
    )


# ============================================================
# ESPN CDN URL
# ============================================================

def espn_logo_urls(
    league,
    code
):

    sport = league.lower()

    primary = (
        f"{ESPN_CDN_BASE}/"
        f"{sport}/500/"
        f"{code}.png"
    )

    scoreboard = (
        f"{ESPN_CDN_SCOREBOARD_BASE}/"
        f"{sport}/500/"
        f"scoreboard/"
        f"{code}.png"
    )

    return [
        primary,
        scoreboard,
    ]


# ============================================================
# HTTP REQUEST WITH RETRIES
# ============================================================

def request_with_retry(
    session,
    url
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
                headers={
                    "User-Agent": USER_AGENT,
                    "Accept": (
                        "image/avif,image/webp,"
                        "image/apng,image/svg+xml,"
                        "image/*,*/*;q=0.8"
                    ),
                    "Referer": "https://www.espn.com/",
                },
            )

            response.raise_for_status()

            return response

        except Exception as exc:

            last_error = exc

            if attempt < MAX_RETRIES:

                print(
                    f"    Retry {attempt}/"
                    f"{MAX_RETRIES - 1}: "
                    f"{url}"
                )

                time.sleep(
                    RETRY_DELAY * attempt
                )

    raise RuntimeError(
        f"Request failed after "
        f"{MAX_RETRIES} attempts: "
        f"{url} -> {last_error}"
    )


# ============================================================
# DOWNLOAD ESPN LOGO
#
# IMPORTANT:
#
# The downloaded ESPN image is returned exactly as provided.
#
# No white-background removal.
# No trimming.
# No resizing.
# No enlargement.
# No modification of the artwork.
# ============================================================

def download_espn_logo(
    session,
    league,
    team_name
):

    code = get_espn_code(
        league,
        team_name
    )

    urls = espn_logo_urls(
        league,
        code
    )

    last_error = None

    for url in urls:

        try:

            print(
                f"    Downloading: "
                f"{league} / {team_name} "
                f"-> {url}"
            )

            response = request_with_retry(
                session,
                url
            )

            content = response.content

            if not content:

                raise RuntimeError(
                    "ESPN returned an empty response."
                )

            return content, url

        except Exception as exc:

            last_error = exc

    raise RuntimeError(
        f"Could not download ESPN logo for "
        f"{league} / {team_name}: "
        f"{last_error}"
    )


# ============================================================
# LOAD DOWNLOADED LOGO
#
# The native ESPN dimensions are retained.
# ============================================================

def load_downloaded_logo(
    content,
    league,
    team_name
):

    try:

        from io import BytesIO

        with Image.open(
            BytesIO(content)
        ) as image:

            image.load()

            # Preserve the actual ESPN dimensions.
            # Convert only to RGBA so the PNG output has an
            # explicit alpha channel.
            image = image.convert("RGBA")

            return image.copy()

    except Exception as exc:

        raise RuntimeError(
            f"Downloaded ESPN logo for "
            f"{league} / {team_name} "
            f"is not a valid image: "
            f"{exc}"
        )


# ============================================================
# DOWNLOAD ONE TEAM LOGO
#
# NO CLEANUP.
#
# The returned image is the ESPN CDN logo at its native size.
# ============================================================

def download_one_team_logo(
    league,
    team
):

    team_name = team["name"]

    session = requests.Session()

    try:

        content, url = download_espn_logo(
            session,
            league,
            team_name
        )

        image = load_downloaded_logo(
            content,
            league,
            team_name
        )

        return {
            "league": league,
            "team": team_name,
            "code": team["espn_code"],
            "url": url,
            "image": image,
            "native_size": (
                image.width,
                image.height
            ),
        }

    finally:

        session.close()


# ============================================================
# DOWNLOAD ALL LOGOS
#
# Existing sports-logos is not modified.
#
# The actual ESPN logos are retained in their native
# dimensions.
# ============================================================

def download_all_logos(
    teams_by_league
):

    print()
    print("=" * 70)
    print("DOWNLOADING NEW LOGO SOURCES FROM ESPN CDN")
    print("=" * 70)

    cleaned_logos = {}

    jobs = []

    total_teams = sum(
        len(
            teams_by_league[
                league
            ]
        )
        for league in LEAGUES
    )

    completed = 0

    with ThreadPoolExecutor(
        max_workers=BUILD_WORKERS
    ) as executor:

        for league in sorted(
            LEAGUES
        ):

            for team in teams_by_league[
                league
            ].values():

                jobs.append(
                    executor.submit(
                        download_one_team_logo,
                        league,
                        team
                    )
                )

        for future in as_completed(
            jobs
        ):

            result = future.result()

            completed += 1

            key = (
                result["league"],
                clean_name(
                    result["team"]
                )
            )

            cleaned_logos[
                key
            ] = result["image"]

            print(
                f"[{completed}/{total_teams}] "
                f"{result['league']}: "
                f"{result['team']} "
                f"({result['code']}) "
                f"downloaded "
                f"{result['native_size'][0]}x"
                f"{result['native_size'][1]}"
            )

    if len(
        cleaned_logos
    ) != total_teams:

        raise RuntimeError(
            f"Downloaded "
            f"{len(cleaned_logos)} "
            f"logos but expected "
            f"{total_teams}"
        )

    print()
    print(
        f"SUCCESS: "
        f"{len(cleaned_logos)}/{total_teams} "
        f"team logos downloaded."
    )

    return cleaned_logos


# ============================================================
# BUILD SOLO LOGO
#
# IMPORTANT:
#
# The solo logo is written at the EXACT native ESPN CDN
# dimensions.
#
# There is NO 1024x1024 canvas.
# There is NO scaling.
# There is NO trimming.
# There is NO background removal.
# ============================================================

def build_solo_logo(
    image,
    destination
):

    if image.width <= 0 or image.height <= 0:

        raise RuntimeError(
            "Invalid ESPN logo dimensions."
        )

    destination.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    image.save(
        destination,
        "PNG",
        optimize=True
    )


# ============================================================
# FIT LOGO FOR MATCHUP
#
# IMPORTANT:
#
# Logos are NEVER enlarged.
#
# If the native ESPN logo is already smaller than the
# available matchup area, its native dimensions are retained.
#
# If an ESPN logo is larger than the available matchup area,
# it is reduced only enough to fit.
#
# This does NOT alter the source logo held in memory.
# ============================================================

def fit_logo_for_matchup(
    image,
    max_width,
    max_height
):

    if image.width <= 0 or image.height <= 0:

        raise RuntimeError(
            "Invalid logo image."
        )

    scale = min(
        1.0,
        max_width / image.width,
        max_height / image.height
    )

    if scale >= 1.0:

        return image.copy()

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
        (
            width,
            height
        ),
        Image.Resampling.LANCZOS
    )


# ============================================================
# BUILD MATCHUP
#
# HOME = LEFT
# AWAY = RIGHT
#
# The original ESPN logo artwork is used.
#
# Native-size logos are never enlarged.
#
# A small transparent edge margin is guaranteed.
# ============================================================

def build_matchup(
    home_logo,
    away_logo,
    destination
):

    canvas_width, canvas_height = MATCHUP_SIZE

    half_width = (
        canvas_width
        //
        2
    )

    available_width = (
        int(
            half_width
            *
            MATCHUP_LOGO_WIDTH_SCALE
        )
        -
        (
            MATCHUP_EDGE_MARGIN
            *
            2
        )
    )

    available_height = (
        int(
            canvas_height
            *
            MATCHUP_LOGO_HEIGHT_SCALE
        )
        -
        (
            MATCHUP_EDGE_MARGIN
            *
            2
        )
    )

    available_width = max(
        1,
        available_width
    )

    available_height = max(
        1,
        available_height
    )

    home = fit_logo_for_matchup(
        home_logo,
        available_width,
        available_height
    )

    away = fit_logo_for_matchup(
        away_logo,
        available_width,
        available_height
    )

    canvas = Image.new(
        "RGBA",
        MATCHUP_SIZE,
        (
            0,
            0,
            0,
            0
        )
    )

    # --------------------------------------------------------
    # LEFT / HOME
    # --------------------------------------------------------

    home_area_left = MATCHUP_EDGE_MARGIN

    home_area_right = (
        half_width
        -
        MATCHUP_EDGE_MARGIN
    )

    home_area_width = (
        home_area_right
        -
        home_area_left
    )

    home_x = (
        home_area_left
        +
        (
            home_area_width
            -
            home.width
        )
        //
        2
    )

    home_y = (
        canvas_height
        -
        home.height
    ) // 2

    # --------------------------------------------------------
    # RIGHT / AWAY
    # --------------------------------------------------------

    away_area_left = (
        half_width
        +
        MATCHUP_EDGE_MARGIN
    )

    away_area_right = (
        canvas_width
        -
        MATCHUP_EDGE_MARGIN
    )

    away_area_width = (
        away_area_right
        -
        away_area_left
    )

    away_x = (
        away_area_left
        +
        (
            away_area_width
            -
            away.width
        )
        //
        2
    )

    away_y = (
        canvas_height
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
# SOURCE DISCOVERY
#
# Existing sports-logos provides ONLY:
#
#   - league names
#   - team folder names
#
# Existing PNGs are NEVER used as logo sources.
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

    for league in sorted(
        LEAGUES
    ):

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
                    f"Invalid team folder name: "
                    f"{team_folder}"
                )

            if key in teams_by_league[
                league
            ]:

                raise RuntimeError(
                    f"Duplicate team detected in "
                    f"{league}: "
                    f"{team_name}"
                )

            code = get_espn_code(
                league,
                team_name
            )

            teams_by_league[
                league
            ][key] = {
                "name": team_name,
                "folder": team_folder,
                "espn_code": code,
            }

    return teams_by_league


# ============================================================
# VERIFY TEAM COUNTS
# ============================================================

def verify_team_counts(
    teams_by_league
):

    print()
    print("=" * 70)
    print("VERIFYING TEAM ROSTER")
    print("=" * 70)

    expected_counts = {
        "MLB": 30,
        "NBA": 30,
        "NFL": 32,
        "NHL": 32,
    }

    total = 0

    for league in sorted(
        LEAGUES
    ):

        actual = len(
            teams_by_league[
                league
            ]
        )

        expected = expected_counts[
            league
        ]

        print()
        print(
            f"{league}: "
            f"{actual} teams"
        )

        if actual != expected:

            raise RuntimeError(
                f"{league}: expected "
                f"{expected} teams but found "
                f"{actual}"
            )

        total += actual

    print()
    print(
        f"TOTAL TEAMS: {total}"
    )

    if total != 124:

        raise RuntimeError(
            f"Expected 124 total teams but found "
            f"{total}"
        )

    return total


# ============================================================
# PRE-VERIFY ESPN MAPPINGS
# ============================================================

def verify_espn_mappings(
    teams_by_league
):

    print()
    print("=" * 70)
    print("VERIFYING ESPN CDN MAPPINGS")
    print("=" * 70)

    for league in sorted(
        LEAGUES
    ):

        print()
        print(league)

        for team in sorted(
            teams_by_league[
                league
            ].values(),
            key=lambda item: clean_name(
                item["name"]
            )
        ):

            print(
                f"  {team['name']}"
                f" -> "
                f"{team['espn_code']}"
            )


# ============================================================
# VERIFY NATIVE ESPN DIMENSIONS
# ============================================================
#
# The 124 solo logos must remain at exactly the dimensions
# supplied by ESPN.
#
# This function records those dimensions from the downloaded
# source images and verifies the final solo files against them.
# ============================================================

def verify_native_dimensions(
    build_root,
    native_dimensions
):

    print()
    print("=" * 70)
    print("VERIFYING NATIVE ESPN LOGO DIMENSIONS")
    print("=" * 70)

    checked = 0

    for key, expected_size in sorted(
        native_dimensions.items()
    ):

        league, team_key = key

        team_name = team_key

        team_folder = None

        league_root = (
            build_root
            /
            league
        )

        for folder in league_root.iterdir():

            if (
                folder.is_dir()
                and
                clean_name(
                    folder.name
                )
                == team_key
            ):

                team_folder = folder
                break

        if team_folder is None:

            raise RuntimeError(
                f"Could not locate generated "
                f"folder for "
                f"{league} / {team_name}"
            )

        solo = (
            team_folder
            /
            f"{filesystem_name(team_folder.name)}.png"
        )

        if not solo.is_file():

            raise RuntimeError(
                f"Missing solo logo: {solo}"
            )

        with Image.open(
            solo
        ) as image:

            actual = (
                image.width,
                image.height
            )

            if actual != expected_size:

                raise RuntimeError(
                    f"Native ESPN dimensions changed "
                    f"for {league} / "
                    f"{team_folder.name}: "
                    f"{actual}, expected "
                    f"{expected_size}"
                )

        checked += 1

    print()
    print(
        f"Native ESPN dimensions verified on "
        f"{checked} solo logos."
    )


# ============================================================
# BUILD ONE TEAM FOLDER
# ============================================================

def build_team_folder(
    league,
    home_team,
    all_teams,
    downloaded_logos,
    destination_league
):

    home_name = home_team["name"]

    home_key = clean_name(
        home_name
    )

    home_logo = downloaded_logos[
        (
            league,
            home_key
        )
    ]

    home_folder = (
        destination_league
        /
        filesystem_name(
            home_name
        )
    )

    home_folder.mkdir(
        parents=True,
        exist_ok=True
    )

    # --------------------------------------------------------
    # SOLO
    #
    # Exact native ESPN dimensions.
    # --------------------------------------------------------

    solo_path = (
        home_folder
        /
        (
            f"{filesystem_name(home_name)}"
            f".png"
        )
    )

    build_solo_logo(
        home_logo,
        solo_path
    )

    generated = 1

    # --------------------------------------------------------
    # EVERY MATCHUP
    # --------------------------------------------------------

    for away_team in all_teams:

        away_name = away_team["name"]

        away_key = clean_name(
            away_name
        )

        if away_key == home_key:

            continue

        away_logo = downloaded_logos[
            (
                league,
                away_key
            )
        ]

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
            home_logo,
            away_logo,
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
    downloaded_logos,
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
                    downloaded_logos,
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

    actual_files = list(
        destination_league.rglob(
            "*.png"
        )
    )

    if len(actual_files) != expected_files:

        raise RuntimeError(
            f"{league}: generated "
            f"{len(actual_files)} PNG files, "
            f"expected {expected_files}"
        )

    for team in sorted_teams:

        team_name = team["name"]

        team_folder = (
            destination_league
            /
            filesystem_name(
                team_name
            )
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
            (
                f"{filesystem_name(team_name)}"
                f".png"
            )
        )

        if not solo.is_file():

            raise RuntimeError(
                f"Missing solo logo: "
                f"{solo}"
            )

        for opponent in sorted_teams:

            opponent_name = opponent["name"]

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
# VERIFY COMPLETE GENERATED LIBRARY
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

    for league in sorted(
        LEAGUES
    ):

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

        print()
        print(
            f"{league}: "
            f"{len(files)}/{expected}"
        )

        if len(files) != expected:

            raise RuntimeError(
                f"{league}: expected "
                f"{expected} PNG files "
                f"but found "
                f"{len(files)}"
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

                    if "_vs_" in path.stem:

                        expected_size = (
                            MATCHUP_SIZE
                        )

                    else:

                        # Solo dimensions are checked
                        # separately against the native
                        # ESPN dimensions.

                        expected_size = (
                            image.width,
                            image.height
                        )

                    actual_size = (
                        image.width,
                        image.height
                    )

                    if (
                        "_vs_" in path.stem
                        and
                        actual_size
                        !=
                        expected_size
                    ):

                        raise RuntimeError(
                            f"Wrong dimensions: "
                            f"{path} "
                            f"is {actual_size}, "
                            f"expected "
                            f"{expected_size}"
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
        f"TOTAL: "
        f"{total_found}/{total_expected} "
        f"PNG files verified."
    )

    if total_found != total_expected:

        raise RuntimeError(
            "Final generated file count does "
            "not match expected count."
        )


# ============================================================
# VERIFY PNG FILES
# ============================================================

def verify_png_files(
    build_root
):

    print()
    print("=" * 70)
    print("VERIFYING PNG FILES")
    print("=" * 70)

    checked = 0

    for path in build_root.rglob(
        "*.png"
    ):

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
                f"Invalid PNG: "
                f"{path}: {exc}"
            )

        checked += 1

    print()
    print(
        f"{checked} PNG files verified."
    )


# ============================================================
# VERIFY MATCHUP DIMENSIONS
# ============================================================

def verify_matchup_dimensions(
    build_root
):

    print()
    print("=" * 70)
    print("VERIFYING MATCHUP DIMENSIONS")
    print("=" * 70)

    checked = 0

    for path in build_root.rglob(
        "*.png"
    ):

        if "_vs_" not in path.stem:

            continue

        with Image.open(
            path
        ) as image:

            actual = (
                image.width,
                image.height
            )

            if actual != MATCHUP_SIZE:

                raise RuntimeError(
                    f"Wrong matchup dimensions: "
                    f"{path} is {actual}, "
                    f"expected {MATCHUP_SIZE}"
                )

        checked += 1

    print()
    print(
        f"Matchup dimensions verified on "
        f"{checked} PNG files."
    )


# ============================================================
# VERIFY MATCHUP CORNER TRANSPARENCY
#
# Only matchup files are checked.
#
# The corners must remain transparent because the matchup
# canvas itself is transparent.
# ============================================================

def verify_matchup_corners_transparent(
    build_root
):

    print()
    print("=" * 70)
    print("VERIFYING MATCHUP CORNER TRANSPARENCY")
    print("=" * 70)

    checked = 0

    for path in build_root.rglob(
        "*.png"
    ):

        if "_vs_" not in path.stem:

            continue

        with Image.open(
            path
        ) as image:

            image = image.convert(
                "RGBA"
            )

            width, height = image.size

            points = (
                (
                    0,
                    0
                ),
                (
                    width - 1,
                    0
                ),
                (
                    0,
                    height - 1
                ),
                (
                    width - 1,
                    height - 1
                ),
            )

            for x, y in points:

                _, _, _, alpha = (
                    image.getpixel(
                        (
                            x,
                            y
                        )
                    )
                )

                if alpha != 0:

                    raise RuntimeError(
                        f"Matchup corner is not "
                        f"transparent in "
                        f"{path} "
                        f"at ({x}, {y})"
                    )

        checked += 1

    print()
    print(
        f"Matchup corner transparency "
        f"verified on {checked} PNG files."
    )


# ============================================================
# VERIFY TRANSPARENCY
#
# We do NOT require every image to contain transparent pixels
# around the artwork because the ESPN solo logo itself is
# preserved exactly as provided.
#
# Matchup canvases are explicitly verified separately.
# ============================================================

def verify_transparency(
    build_root
):

    print()
    print("=" * 70)
    print("VERIFYING TRANSPARENCY")
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

            if "_vs_" in path.stem:

                # Matchups must have transparency because
                # their canvas is transparent.
                alpha = image.getchannel(
                    "A"
                )

                minimum, maximum = (
                    alpha.getextrema()
                )

                if minimum != 0:

                    raise RuntimeError(
                        f"Matchup has no transparent "
                        f"pixels: {path}"
                    )

        checked += 1

    print()
    print(
        f"{checked} PNG files checked for "
        f"transparency."
    )


# ============================================================
# INSTALL NEW LIBRARY
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

    print()
    print(
        f"CURRENT LIBRARY: {ROOT}"
    )

    print(
        f"NEW VERIFIED BUILD: {BUILD_ROOT}"
    )

    if ROOT.exists():

        print()
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
        "New ESPN-sourced sports-logos "
        "library installed successfully."
    )


# ============================================================
# VERIFY INSTALLED LIBRARY
# ============================================================

def verify_installed_library(
    teams_by_league,
    native_dimensions
):

    print()
    print("=" * 70)
    print("VERIFYING INSTALLED SPORTS LOGO LIBRARY")
    print("=" * 70)

    total_expected = 0
    total_found = 0

    for league in sorted(
        LEAGUES
    ):

        teams = teams_by_league[
            league
        ]

        expected_per_team = len(
            teams
        )

        expected = (
            len(teams)
            *
            expected_per_team
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
                f"expected "
                f"{expected}"
            )

        for path in files:

            with Image.open(
                path
            ) as image:

                if image.mode != "RGBA":

                    raise RuntimeError(
                        f"Installed image "
                        f"is not RGBA: "
                        f"{path}"
                    )

                if "_vs_" in path.stem:

                    expected_size = (
                        MATCHUP_SIZE
                    )

                    actual_size = (
                        image.width,
                        image.height
                    )

                    if actual_size != expected_size:

                        raise RuntimeError(
                            f"Installed matchup "
                            f"has wrong dimensions: "
                            f"{path}"
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
                    f"Missing installed "
                    f"team folder: "
                    f"{team_folder}"
                )

            solo = (
                team_folder
                /
                (
                    f"{filesystem_name(team_name)}"
                    f".png"
                )
            )

            if not solo.is_file():

                raise RuntimeError(
                    f"Missing installed "
                    f"solo logo: "
                    f"{solo}"
                )

            expected_native = native_dimensions[
                (
                    league,
                    clean_name(
                        team_name
                    )
                )
            ]

            with Image.open(
                solo
            ) as image:

                actual_native = (
                    image.width,
                    image.height
                )

                if actual_native != expected_native:

                    raise RuntimeError(
                        f"Installed solo logo "
                        f"dimension changed: "
                        f"{solo} "
                        f"is {actual_native}, "
                        f"expected "
                        f"{expected_native}"
                    )

            for opponent in teams.values():

                opponent_name = opponent["name"]

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
                        f"matchup: "
                        f"{matchup}"
                    )

        print(
            f"{league}: "
            f"{len(files)}/{expected} "
            f"verified"
        )

        total_expected += expected
        total_found += len(files)

    print()
    print(
        f"Installed library verified: "
        f"{total_found}/{total_expected} "
        f"files."
    )

    if total_found != total_expected:

        raise RuntimeError(
            "Installed library verification "
            "failed."
        )


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 70)
    print("ESPN CDN SPORTS LOGO DOWNLOADER + REBUILDER")
    print("=" * 70)

    print()
    print("ROSTER SOURCE:")
    print(
        "  Existing sports-logos team folders"
    )

    print()
    print("LOGO SOURCE:")
    print(
        "  ESPN CDN"
    )

    print()
    print("ESPN TEAM API:")
    print(
        "  NOT USED"
    )

    print()
    print("PROCESS:")

    print(
        "  1. Read the existing 124 team folders."
    )

    print(
        "  2. Map each team to its ESPN CDN abbreviation."
    )

    print(
        "  3. Download the direct ESPN CDN logo."
    )

    print(
        "  4. Preserve the ESPN logo exactly as supplied."
    )

    print(
        "  5. Preserve native ESPN dimensions."
    )

    print(
        "  6. Preserve ESPN transparency."
    )

    print(
        "  7. Build native-size solo logos."
    )

    print(
        "  8. Build 1024x512 transparent matchups."
    )

    print(
        "  9. Never enlarge an ESPN logo."
    )

    print(
        " 10. Verify the complete library."
    )

    print(
        " 11. Replace sports-logos only after success."
    )

    print()
    print("IMPORTANT:")
    print(
        "  No white-background removal is performed."
    )

    print(
        "  No logo trimming is performed."
    )

    print(
        "  No solo-logo resizing is performed."
    )

    print(
        "  No solo-logo stretching is performed."
    )

    print(
        "  ESPN native dimensions are retained."
    )

    print(
        "  ESPN logo artwork is not altered."
    )

    print()
    print("SAFETY:")

    print(
        "  Existing sports-logos is not modified during "
        "download/build."
    )

    print(
        "  Existing matchup files are never used as sources."
    )

    print(
        "  Existing solo PNGs are never used as new logo sources."
    )

    print(
        "  If any team fails, the old library remains intact."
    )

    print(
        "  No ESPN team-data API is called."
    )

    print()
    print(
        f"Build workers: {BUILD_WORKERS}"
    )

    print(
        f"Matchup canvas: "
        f"{MATCHUP_SIZE[0]}x{MATCHUP_SIZE[1]}"
    )

    print(
        f"Matchup edge margin: "
        f"{MATCHUP_EDGE_MARGIN}px"
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
    # Discover roster.
    # --------------------------------------------------------

    teams_by_league = (
        discover_source_teams()
    )

    total_teams = (
        verify_team_counts(
            teams_by_league
        )
    )

    # --------------------------------------------------------
    # Verify mappings before downloading.
    # --------------------------------------------------------

    verify_espn_mappings(
        teams_by_league
    )

    # --------------------------------------------------------
    # Calculate expected files.
    # --------------------------------------------------------

    print()
    print("=" * 70)
    print("EXPECTED OUTPUT")
    print("=" * 70)

    total_expected = 0

    for league in sorted(
        LEAGUES
    ):

        team_count = len(
            teams_by_league[
                league
            ]
        )

        expected = (
            team_count
            *
            team_count
        )

        print(
            f"{league}: "
            f"{team_count} teams -> "
            f"{team_count} folders -> "
            f"{expected} files"
        )

        total_expected += expected

    print()
    print(
        f"TOTAL TEAMS: "
        f"{total_teams}"
    )

    print(
        f"TOTAL PNG FILES: "
        f"{total_expected}"
    )

    # --------------------------------------------------------
    # DOWNLOAD ALL NEW ESPN LOGOS.
    # --------------------------------------------------------

    downloaded_logos = (
        download_all_logos(
            teams_by_league
        )
    )

    # --------------------------------------------------------
    # Record native dimensions BEFORE building.
    # --------------------------------------------------------

    native_dimensions = {}

    for key, image in downloaded_logos.items():

        native_dimensions[
            key
        ] = (
            image.width,
            image.height
        )

    # --------------------------------------------------------
    # Build entire new library.
    # --------------------------------------------------------

    generated_total = 0

    for league in sorted(
        LEAGUES
    ):

        generated_total += (
            build_league(
                league,
                teams_by_league[
                    league
                ],
                downloaded_logos,
                BUILD_ROOT
            )
        )

    # --------------------------------------------------------
    # COMPLETE BUILD VERIFICATION.
    # --------------------------------------------------------

    verify_generated_library(
        BUILD_ROOT,
        teams_by_league
    )

    verify_png_files(
        BUILD_ROOT
    )

    verify_native_dimensions(
        BUILD_ROOT,
        native_dimensions
    )

    verify_matchup_dimensions(
        BUILD_ROOT
    )

    verify_matchup_corners_transparent(
        BUILD_ROOT
    )

    verify_transparency(
        BUILD_ROOT
    )

    # --------------------------------------------------------
    # ONLY NOW replace sports-logos.
    # --------------------------------------------------------

    install_new_library()

    # --------------------------------------------------------
    # Verify actual installed library.
    # --------------------------------------------------------

    verify_installed_library(
        teams_by_league,
        native_dimensions
    )

    # --------------------------------------------------------
    # Final report.
    # --------------------------------------------------------

    print()
    print("=" * 70)
    print("FINISHED SUCCESSFULLY")
    print("=" * 70)

    print()
    print(
        "LOGO SOURCE:"
    )

    print(
        "  ESPN CDN"
    )

    print()
    print(
        "ESPN TEAM API:"
    )

    print(
        "  NOT USED"
    )

    print()
    print(
        f"Teams processed: "
        f"{total_teams}"
    )

    print(
        f"PNG files generated: "
        f"{generated_total}"
    )

    print(
        f"PNG files expected: "
        f"{total_expected}"
    )

    print()
    print(
        "Every team has a newly downloaded "
        "ESPN CDN logo."
    )

    print(
        "ESPN logo artwork was not cleaned, "
        "trimmed, or otherwise altered."
    )

    print(
        "Solo logos remain at their exact "
        "native ESPN dimensions."
    )

    print(
        "Solo logos are never enlarged or stretched."
    )

    print(
        "ESPN-provided transparency is preserved."
    )

    print(
        "Matchups use the same ESPN source artwork "
        "without enlargement."
    )

    print(
        "Matchups are 1024x512 transparent PNGs."
    )

    print(
        "A transparent edge margin prevents matchup "
        "logos from touching the canvas boundary."
    )

    print(
        "Every team has a matchup against every "
        "other team in its league."
    )

    print(
        "Both home/away matchup directions were generated."
    )

    print(
        "The old sports-logos library was not replaced "
        "until the complete build passed verification."
    )

    print()
    print(
        "ESPN CDN logo source verified and installed."
    )


if __name__ == "__main__":

    main()
