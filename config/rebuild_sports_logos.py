import os
import re
import shutil
import unicodedata
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
# This directory is used only to discover the EXISTING TEAM
# NAMES / FOLDER STRUCTURE.
#
# The existing logo PNGs are NOT used as the new logo source.
#
# New logos are downloaded directly from the ESPN CDN.
#
# The existing sports-logos directory is never replaced until
# the complete new library has been downloaded, cleaned,
# generated, and verified.
# ============================================================

ROOT = Path("sports-logos")

# Temporary build directory.
BUILD_ROOT = Path("_sports_logos_rebuild")

# Temporary backup used during installation.
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
# SOLO LOGO SETTINGS
# ============================================================

# Final solo logo canvas.
SOLO_SIZE = (1024, 1024)

# Maximum percentage of the canvas occupied by artwork.
#
# The logo itself is tightly cropped first, then enlarged so
# that it occupies approximately 90% of the available canvas.
SOLO_LOGO_SCALE = 0.90


# ============================================================
# MATCHUP SETTINGS
# ============================================================

MATCHUP_SIZE = (1024, 512)

MATCHUP_LOGO_WIDTH_SCALE = 0.88
MATCHUP_LOGO_HEIGHT_SCALE = 0.88


# ============================================================
# WHITE BACKGROUND REMOVAL
# ============================================================

# Near-white pixels connected to the OUTSIDE edge are treated
# as background.
#
# White portions enclosed inside the actual logo are preserved.
WHITE_THRESHOLD = 245

# Existing pixels with alpha <= this are considered
# transparent during background detection.
ALPHA_THRESHOLD = 8


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
# These are deliberately hard-coded.
#
# IMPORTANT:
#
# We do NOT call:
#
#   site.api.espn.com
#
# The previous workflow failed because GitHub Actions received
# HTTP 403 from that API.
#
# We therefore use the existing team folders as the roster and
# use this mapping only to determine the ESPN CDN logo URL.
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

    # Possible current/folder naming variations.
    "cleveland indians": "cle",
    "tampa bay devil rays": "tb",
    "washington nationals": "wsh",

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

    # Common alternate folder names.
    "golden state": "gs",
    "la clippers": "lac",
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

    # Common variations.
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

    # Older / alternate NHL folder names.
    "arizona coyotes": "ari",
    "phoenix coyotes": "ari",
    "utah hockey club": "uta",
}


# ============================================================
# NAME NORMALIZATION
# ============================================================

def clean_name(value):

    value = os.path.splitext(
        value
    )[0]

    value = value.replace(
        "_",
        " "
    )

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

    team = os.path.splitext(
        team
    )[0]

    team = team.replace(
        "_",
        " "
    )

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

    key = clean_name(
        team_name
    )

    code = ESPN_CODES.get(
        key
    )

    if code:
        return code

    # --------------------------------------------------------
    # Last-resort abbreviation guesses for folders where the
    # team name itself is already an obvious ESPN abbreviation.
    #
    # We DO NOT use this silently for normal team names.
    # --------------------------------------------------------

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

    # Primary URL.
    primary = (
        f"{ESPN_CDN_BASE}/"
        f"{sport}/500/"
        f"{code}.png"
    )

    # ESPN also exposes scoreboard variants.
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
                    f"    Retry {attempt}/{MAX_RETRIES - 1}: "
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

            image = image.convert(
                "RGBA"
            )

            return image.copy()

    except Exception as exc:

        raise RuntimeError(
            f"Downloaded ESPN logo for "
            f"{league} / {team_name} "
            f"is not a valid image: "
            f"{exc}"
        )


# ============================================================
# REMOVE EDGE WHITE BACKGROUND
#
# IMPORTANT:
#
# We do NOT delete every white pixel.
#
# Only near-white pixels connected to the OUTSIDE edge are
# removed.
#
# Therefore:
#
#   white lettering = preserved
#   white baseball = preserved
#   white outlines = preserved
#   white internal details = preserved
#
# while:
#
#   giant white rectangular background = removed
# ============================================================

def remove_edge_white_background(
    image
):

    image = image.convert(
        "RGBA"
    )

    width, height = image.size

    if (
        width <= 0
        or
        height <= 0
    ):

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

        r, g, b, a = pixels[
            x,
            y
        ]

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
            (
                x,
                y
            )
        )

    # Seed every edge.
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
            (
                x - 1,
                y
            ),
            (
                x + 1,
                y
            ),
            (
                x,
                y - 1
            ),
            (
                x,
                y + 1
            ),
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

    # Make detected background transparent.
    for y in range(height):

        for x in range(width):

            index = (
                y * width
                +
                x
            )

            if visited[index]:

                r, g, b, a = pixels[
                    x,
                    y
                ]

                pixels[
                    x,
                    y
                ] = (
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

def clean_logo(
    image,
    league,
    team_name
):

    image = image.convert(
        "RGBA"
    )

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
            f"{league} / {team_name}"
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
        (
            width,
            height
        ),
        Image.Resampling.LANCZOS
    )


# ============================================================
# BUILD SOLO LOGO
#
# Final:
#
# 1024x1024
# RGBA
# Transparent
#
# Artwork approximately 90% of canvas.
# ============================================================

def build_solo_logo(
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
        (
            0,
            0,
            0,
            0
        )
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
        (
            x,
            y
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
# BUILD MATCHUP
#
# HOME = LEFT
# AWAY = RIGHT
#
# Both logos come from the newly downloaded ESPN CDN artwork.
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
        (
            0,
            0,
            0,
            0
        )
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
# SOURCE DISCOVERY
#
# IMPORTANT:
#
# Existing sports-logos provides ONLY the roster and folder
# names.
#
# The existing PNG files are deliberately NOT opened or used
# as the new logo source.
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

            team_name = (
                team_folder.name
            )

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

            # Verify a CDN mapping exists BEFORE doing any
            # downloads.
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
        print(
            f"{league}"
        )

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
# DOWNLOAD ONE TEAM LOGO
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

        cleaned = clean_logo(
            image,
            league,
            team_name
        )

        return {
            "league": league,
            "team": team_name,
            "code": team["espn_code"],
            "url": url,
            "image": cleaned,
        }

    finally:

        session.close()


# ============================================================
# DOWNLOAD ALL LOGOS
#
# Returns CLEANED logo images held in memory.
#
# Existing sports-logos is not modified.
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
                f"downloaded and cleaned"
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
        f"team logos downloaded and cleaned."
    )

    return cleaned_logos


# ============================================================
# BUILD ONE TEAM FOLDER
# ============================================================

def build_team_folder(
    league,
    home_team,
    all_teams,
    cleaned_logos,
    destination_league
):

    home_name = (
        home_team["name"]
    )

    home_key = (
        clean_name(
            home_name
        )
    )

    home_clean_logo = cleaned_logos[
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
        home_clean_logo,
        solo_path
    )

    generated = 1

    # --------------------------------------------------------
    # EVERY MATCHUP
    # --------------------------------------------------------

    for away_team in all_teams:

        away_name = (
            away_team["name"]
        )

        away_key = clean_name(
            away_name
        )

        if (
            away_key
            ==
            home_key
        ):

            continue

        away_clean_logo = cleaned_logos[
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
    cleaned_logos,
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
                    cleaned_logos,
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

    # --------------------------------------------------------
    # VERIFY COUNT
    # --------------------------------------------------------

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

    # --------------------------------------------------------
    # VERIFY FOLDERS
    # --------------------------------------------------------

    for team in sorted_teams:

        team_name = (
            team["name"]
        )

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

                    expected_size = (
                        MATCHUP_SIZE
                        if "_vs_" in path.stem
                        else SOLO_SIZE
                    )

                    actual_size = (
                        image.width,
                        image.height
                    )

                    if actual_size != expected_size:

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
# VERIFY TRANSPARENCY
# ============================================================

def verify_transparency(
    build_root,
    teams_by_league
):

    print()
    print("=" * 70)
    print("VERIFYING TRANSPARENT BACKGROUNDS")
    print("=" * 70)

    checked = 0

    for league in sorted(
        LEAGUES
    ):

        league_root = (
            build_root
            /
            league
        )

        for path in league_root.rglob(
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
                        f"found in generated "
                        f"logo: {path}"
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
    build_root,
    teams_by_league
):

    print()
    print("=" * 70)
    print("VERIFYING OUTPUT DIMENSIONS")
    print("=" * 70)

    solo_count = 0
    matchup_count = 0

    for league in sorted(
        LEAGUES
    ):

        teams = teams_by_league[
            league
        ]

        for team in teams.values():

            team_folder = (
                build_root
                /
                league
                /
                filesystem_name(
                    team["name"]
                )
            )

            for path in team_folder.glob(
                "*.png"
            ):

                with Image.open(
                    path
                ) as image:

                    if "_vs_" in path.stem:

                        expected = (
                            MATCHUP_SIZE
                        )

                        matchup_count += 1

                    else:

                        expected = (
                            SOLO_SIZE
                        )

                        solo_count += 1

                    actual = (
                        image.width,
                        image.height
                    )

                    if actual != expected:

                        raise RuntimeError(
                            f"Wrong dimensions: "
                            f"{path} "
                            f"is {actual}, "
                            f"expected "
                            f"{expected}"
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
# VERIFY NO WHITE EDGE BACKGROUNDS
#
# This specifically checks the four corners of every generated
# image. A transparent corner is what we want.
# ============================================================

def verify_corners_transparent(
    build_root
):

    print()
    print("=" * 70)
    print("VERIFYING CORNER TRANSPARENCY")
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

            width, height = (
                image.size
            )

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
                        f"Corner is not transparent "
                        f"in {path} "
                        f"at ({x}, {y})"
                    )

        checked += 1

    print()
    print(
        f"Corner transparency verified on "
        f"{checked} PNG files."
    )


# ============================================================
# INSTALL NEW LIBRARY
#
# THIS IS THE ONLY PLACE WHERE sports-logos IS REPLACED.
#
# It is called only after all verification passes.
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

    # --------------------------------------------------------
    # Move existing library to backup.
    # --------------------------------------------------------

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

        # ----------------------------------------------------
        # Install verified build.
        # ----------------------------------------------------

        BUILD_ROOT.rename(
            ROOT
        )

    except Exception:

        # ----------------------------------------------------
        # Rollback.
        # ----------------------------------------------------

        if (
            BACKUP_ROOT.exists()
            and
            not ROOT.exists()
        ):

            BACKUP_ROOT.rename(
                ROOT
            )

        raise

    # --------------------------------------------------------
    # Delete old library only after successful replacement.
    # --------------------------------------------------------

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
    teams_by_league
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

                expected_size = (
                    MATCHUP_SIZE
                    if "_vs_" in path.stem
                    else SOLO_SIZE
                )

                actual_size = (
                    image.width,
                    image.height
                )

                if actual_size != expected_size:

                    raise RuntimeError(
                        f"Installed image "
                        f"has wrong dimensions: "
                        f"{path}"
                    )

        for team in teams.values():

            team_name = (
                team["name"]
            )

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
    print(
        "ESPN API:"
    )

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
        "  3. Download the 500px ESPN CDN logo."
    )

    print(
        "  4. Remove edge-connected white backgrounds."
    )

    print(
        "  5. Preserve legitimate enclosed white logo details."
    )

    print(
        "  6. Trim transparent space."
    )

    print(
        "  7. Build 1024x1024 transparent solo logos."
    )

    print(
        "  8. Build 1024x512 transparent matchups."
    )

    print(
        "  9. Verify the complete library."
    )

    print(
        " 10. Replace sports-logos only after success."
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
        "  Existing solo PNGs are not used as new logo sources."
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
        f"Solo canvas: "
        f"{SOLO_SIZE[0]}x{SOLO_SIZE[1]}"
    )

    print(
        f"Solo artwork scale: "
        f"{int(SOLO_LOGO_SCALE * 100)}%"
    )

    print(
        f"Matchup canvas: "
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
    # Verify every team has a CDN mapping BEFORE downloading
    # anything.
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
    #
    # Nothing in sports-logos is modified here.
    # --------------------------------------------------------

    cleaned_logos = (
        download_all_logos(
            teams_by_league
        )
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
                cleaned_logos,
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

    verify_transparency(
        BUILD_ROOT,
        teams_by_league
    )

    verify_corners_transparent(
        BUILD_ROOT
    )

    verify_dimensions(
        BUILD_ROOT,
        teams_by_league
    )

    # --------------------------------------------------------
    # ONLY NOW replace sports-logos.
    # --------------------------------------------------------

    install_new_library()

    # --------------------------------------------------------
    # Verify actual installed library.
    # --------------------------------------------------------

    verify_installed_library(
        teams_by_league
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
        "Every team now has a newly downloaded "
        "ESPN CDN logo."
    )

    print(
        "Edge-connected white backgrounds were "
        "removed."
    )

    print(
        "Enclosed white logo details were preserved."
    )

    print(
        "Solo logos were tightly cropped and rendered "
        "as 1024x1024 transparent PNGs."
    )

    print(
        "Matchups were rebuilt as 1024x512 "
        "transparent PNGs."
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
