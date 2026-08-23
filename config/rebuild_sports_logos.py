import io
import os
import re
import sys
import time
import shutil
import unicodedata
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from html.parser import HTMLParser
from urllib.parse import urljoin

import requests
from PIL import Image


# ============================================================
# CONFIG
# ============================================================

ROOT = Path("sports-logos")
TEMP_ROOT = Path("_temp_sports_logos")

LEAGUES = {
    "MLB",
    "NBA",
    "NFL",
    "NHL",
}

# Maximum time allowed for one HTTP request.
REQUEST_TIMEOUT = 30

# Number of files rebuilt simultaneously.
REBUILD_WORKERS = 8

# Maximum amount of time allowed for one rebuild job.
REBUILD_TIMEOUT = 60

# Number of retry passes AFTER the initial pass.
# Total attempts = 1 initial pass + 2 retries = 3 passes.
REBUILD_RETRY_PASSES = 2

# SportsLogos.Net league identifiers.
SPORTSLOGOS_LEAGUE_IDS = {
    "MLB": 4,
    "NHL": 5,
    "NBA": 6,
    "NFL": 7,
}

SPORTSLOGOS_BASE = "https://www.sportslogos.net"

# SportsLogos.Net logo CDN.
SPORTSLOGOS_CONTENT_BASE = "https://content.sportslogos.net"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/151.0 Safari/537.36"
    ),
    "Accept": (
        "text/html,application/xhtml+xml,"
        "application/xml;q=0.9,image/avif,image/webp,"
        "image/apng,*/*;q=0.8"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}


# ============================================================
# TEAM NAME ALIASES
#
# These are the names used by the EXISTING library.
# Do not rename existing files.
# ============================================================

ALIASES = {
    "Los_Angeles_Angels": "Los Angeles Angels",
    "Los_Angeles_Angels_Of_Anaheim": "Los Angeles Angels",

    "Cleveland_Indians": "Cleveland Guardians",

    "Washington_Redskins": "Washington Commanders",
    "Washington_Football_Team": "Washington Commanders",

    "New_Jersey_Nets": "Brooklyn Nets",
    "Charlotte_Bobcats": "Charlotte Hornets",

    "Phoenix_Coyotes": "Arizona Coyotes",

    "Atlanta_Thrashers": "Winnipeg Jets",

    "Oakland_Athletics": "Athletics",

    "Las_Vegas_Raiders": "Las Vegas Raiders",

    "St_Louis_Rams": "Los Angeles Rams",
    "San_Diego_Chargers": "Los Angeles Chargers",
}


# ============================================================
# SPORTSLOGOS.NET NAME OVERRIDES
#
# These are only used to locate the corresponding team page
# on SportsLogos.Net.
# ============================================================

SPORTSLOGOS_NAME_OVERRIDES = {

    # --------------------------------------------------------
    # NBA
    # --------------------------------------------------------

    ("NBA", "LA Clippers"):
        [
            "Los Angeles Clippers",
            "LA Clippers",
        ],

    ("NBA", "LA Lakers"):
        [
            "Los Angeles Lakers",
            "LA Lakers",
        ],

    # --------------------------------------------------------
    # MLB
    # --------------------------------------------------------

    ("MLB", "St Louis Cardinals"):
        [
            "St. Louis Cardinals",
            "St Louis Cardinals",
        ],

    ("MLB", "Athletics"):
        [
            "Athletics",
            "Oakland Athletics",
        ],

    # --------------------------------------------------------
    # NHL
    # --------------------------------------------------------

    ("NHL", "St Louis Blues"):
        [
            "St. Louis Blues",
            "St Louis Blues",
        ],

    ("NHL", "Utah Mammoth"):
        [
            "Utah Mammoth",
        ],

    ("NHL", "Utah Hockey Club"):
        [
            "Utah Mammoth",
            "Utah Hockey Club",
        ],
}


# ============================================================
# HTTP
# ============================================================

session = requests.Session()
session.headers.update(HEADERS)


def get(url):

    response = session.get(
        url,
        timeout=REQUEST_TIMEOUT,
        allow_redirects=True,
    )

    response.raise_for_status()

    return response


# ============================================================
# HTML PARSER
# ============================================================

class SportsLogosHTMLParser(HTMLParser):

    def __init__(self):

        super().__init__(
            convert_charrefs=True
        )

        self.links = []

        self.images = []

        self.current_anchor = None

        self.current_anchor_text = []

    def handle_starttag(
        self,
        tag,
        attrs
    ):

        attributes = dict(
            attrs
        )

        if tag.lower() == "a":

            self.current_anchor = {
                "href": attributes.get(
                    "href"
                ),
                "text": "",
            }

            self.current_anchor_text = []

        elif tag.lower() == "img":

            self.images.append(
                {
                    "src": attributes.get(
                        "src"
                    ),
                    "data_src": attributes.get(
                        "data-src"
                    ),
                    "data_original": attributes.get(
                        "data-original"
                    ),
                    "alt": attributes.get(
                        "alt",
                        ""
                    ),
                    "title": attributes.get(
                        "title",
                        ""
                    ),
                }
            )

    def handle_data(
        self,
        data
    ):

        if self.current_anchor is not None:

            self.current_anchor_text.append(
                data
            )

    def handle_endtag(
        self,
        tag
    ):

        if (
            tag.lower() == "a"
            and self.current_anchor is not None
        ):

            text = " ".join(
                self.current_anchor_text
            )

            text = re.sub(
                r"\s+",
                " ",
                text
            ).strip()

            self.current_anchor[
                "text"
            ] = text

            self.links.append(
                self.current_anchor
            )

            self.current_anchor = None

            self.current_anchor_text = []


def parse_html(
    html_text
):

    parser = SportsLogosHTMLParser()

    parser.feed(
        html_text
    )

    return parser


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


def display_team_name(raw):

    raw = os.path.splitext(
        raw
    )[0]

    if raw in ALIASES:

        return ALIASES[raw]

    return raw.replace(
        "_",
        " "
    )


def sportslogos_team_names(
    league,
    team
):

    values = []

    override = SPORTSLOGOS_NAME_OVERRIDES.get(
        (
            league,
            team
        ),
        []
    )

    values.extend(
        override
    )

    values.append(
        team
    )

    output = []

    seen = set()

    for value in values:

        key = clean_name(
            value
        )

        if not key:
            continue

        if key in seen:
            continue

        seen.add(
            key
        )

        output.append(
            value
        )

    return output


# ============================================================
# GENERIC SPORTSLOGOS.NET SLUG GENERATION
# ============================================================

def sportslogos_slugs(
    team
):

    normalized = clean_name(
        team
    )

    values = [
        normalized
    ]

    if normalized.startswith(
        "la "
    ):

        values.append(
            normalized.replace(
                "la ",
                "los angeles "
            )
        )

    values.append(
        normalized.replace(
            "st ",
            "st louis "
        )
    )

    values.append(
        normalized.replace(
            "saint ",
            "st louis "
        )
    )

    output = []

    seen = set()

    for value in values:

        slug = re.sub(
            r"\s+",
            "-",
            value
        )

        slug = re.sub(
            r"[^a-z0-9-]",
            "",
            slug
        )

        slug = re.sub(
            r"-+",
            "-",
            slug
        ).strip("-")

        if not slug:
            continue

        if slug in seen:
            continue

        seen.add(
            slug
        )

        output.append(
            slug
        )

    return output


# ============================================================
# SPORTSLOGOS.NET YEAR EXTRACTION
# ============================================================

def extract_logo_year(
    url
):

    if not url:
        return None

    match = re.search(
        r"/logos/view/[^/]+/[^/]+/(\d{4})/",
        url
    )

    if not match:
        return None

    try:

        return int(
            match.group(1)
        )

    except ValueError:

        return None


# ============================================================
# DISCOVER TEAM PAGE FROM SPORTSLOGOS.NET
#
# We use the current league/year index to locate the official
# SportsLogos.Net team-history page.
#
# We do NOT guess a logo URL.
# ============================================================

def sportslogos_year_page(
    league,
    year=2026
):

    league_id = SPORTSLOGOS_LEAGUE_IDS[
        league
    ]

    return (
        f"{SPORTSLOGOS_BASE}/teams/"
        f"list_by_year/"
        f"{league_id}{year}/"
        f"{year}-{league}-Logos-By-Year/"
    )


def team_name_matches(
    requested,
    candidate
):

    requested_clean = clean_name(
        requested
    )

    candidate_clean = clean_name(
        candidate
    )

    if requested_clean == candidate_clean:

        return True

    requested_words = set(
        requested_clean.split()
    )

    candidate_words = set(
        candidate_clean.split()
    )

    if not requested_words:
        return False

    overlap = (
        len(
            requested_words
            & candidate_words
        )
        / len(
            requested_words
        )
    )

    return overlap >= 0.80


def discover_team_history_url_from_year_page(
    league,
    team
):

    names = sportslogos_team_names(
        league,
        team
    )

    name_keys = {
        clean_name(name)
        for name in names
    }

    for year in range(
        2026,
        2018,
        -1
    ):

        url = sportslogos_year_page(
            league,
            year
        )

        try:

            response = get(
                url
            )

        except Exception:

            continue

        parser = parse_html(
            response.text
        )

        candidates = []

        for link in parser.links:

            href = link.get(
                "href"
            )

            text = link.get(
                "text",
                ""
            )

            if not href:
                continue

            if "/logos/list_by_team/" not in href:
                continue

            candidates.append(
                (
                    text,
                    urljoin(
                        SPORTSLOGOS_BASE,
                        href
                    )
                )
            )

        for text, href in candidates:

            candidate_clean = clean_name(
                text
            )

            if candidate_clean in name_keys:

                return href

        for text, href in candidates:

            for requested_name in names:

                if team_name_matches(
                    requested_name,
                    text
                ):

                    return href

    return None


# ============================================================
# DISCOVER PRIMARY LOGO PAGE
#
# The team-history page contains separate sections for:
#
#   Primary Logos
#   Alternate Logos
#   Jersey Logos
#   Wordmark Logos
#   Primary Dark Logos
#   etc.
#
# We ONLY accept an exact Primary-Logo URL.
#
# The newest year is selected.
# ============================================================

def discover_primary_logo_page(
    league,
    team
):

    print(
        f"  Finding SportsLogos.Net team page "
        f"for {team}..."
    )

    team_page = (
        discover_team_history_url_from_year_page(
            league,
            team
        )
    )

    if not team_page:

        raise RuntimeError(
            f"Could not locate SportsLogos.Net "
            f"team history page for {league}: {team}"
        )

    print(
        f"  Team history: {team_page}"
    )

    response = get(
        team_page
    )

    parser = parse_html(
        response.text
    )

    primary_links = []

    for link in parser.links:

        href = link.get(
            "href"
        )

        if not href:
            continue

        full_url = urljoin(
            SPORTSLOGOS_BASE,
            href
        )

        # EXACT Primary Logo only.
        #
        # This intentionally excludes:
        #
        # Primary-Dark-Logo
        # Alternate-Logo
        # Jersey-Logo
        # Cap-Logo
        # Wordmark-Logo
        # etc.
        if not re.search(
            r"/Primary-Logo/?$",
            full_url,
            re.IGNORECASE
        ):

            continue

        year = extract_logo_year(
            full_url
        )

        if year is None:
            continue

        primary_links.append(
            (
                year,
                full_url,
                link.get(
                    "text",
                    ""
                )
            )
        )

    if not primary_links:

        raise RuntimeError(
            f"No Primary Logo entries found on "
            f"SportsLogos.Net team page for "
            f"{league}: {team}"
        )

    primary_links.sort(
        key=lambda item: (
            item[0],
            item[1]
        ),
        reverse=True
    )

    selected_year, selected_url, selected_text = (
        primary_links[0]
    )

    return (
        team_page,
        selected_year,
        selected_url
    )


# ============================================================
# EXTRACT FULL-RESOLUTION LOGO IMAGE
#
# SportsLogos.Net logo pages contain the actual image hosted
# on content.sportslogos.net.
#
# We deliberately select the image from the logo page instead
# of trying to construct a CDN filename ourselves.
# ============================================================

def extract_logo_image_url(
    logo_page_url,
    html_text,
    team
):

    parser = parse_html(
        html_text
    )

    candidates = []

    for image in parser.images:

        sources = [
            image.get(
                "src"
            ),
            image.get(
                "data_src"
            ),
            image.get(
                "data_original"
            ),
        ]

        alt = (
            image.get(
                "alt",
                ""
            )
            or ""
        ).lower()

        title = (
            image.get(
                "title",
                ""
            )
            or ""
        ).lower()

        for source in sources:

            if not source:
                continue

            full_url = urljoin(
                logo_page_url,
                source
            )

            lower_url = full_url.lower()

            if (
                "content.sportslogos.net"
                not in lower_url
            ):

                continue

            score = 0

            if (
                "logo"
                in alt
            ):

                score += 5

            if (
                "primary"
                in alt
            ):

                score += 5

            if (
                clean_name(team)
                in clean_name(alt)
            ):

                score += 4

            if (
                "logo"
                in title
            ):

                score += 2

            if (
                "primary"
                in title
            ):

                score += 2

            if (
                "thumb"
                in lower_url
                or "thumbnail"
                in lower_url
            ):

                score -= 5

            candidates.append(
                (
                    score,
                    full_url
                )
            )

    if not candidates:

        raise RuntimeError(
            f"Could not find a SportsLogos.Net "
            f"content image on {logo_page_url}"
        )

    candidates.sort(
        key=lambda item: (
            item[0],
            len(item[1])
        ),
        reverse=True
    )

    return candidates[0][1]


# ============================================================
# DOWNLOAD SPORTSLOGOS.NET PRIMARY LOGO
# ============================================================

def download_sportslogos_logo(
    league,
    team
):

    (
        team_page,
        selected_year,
        logo_page
    ) = discover_primary_logo_page(
        league,
        team
    )

    print(
        f"  Selected Primary Logo year: "
        f"{selected_year}"
    )

    print(
        f"  Primary Logo page: "
        f"{logo_page}"
    )

    response = get(
        logo_page
    )

    image_url = extract_logo_image_url(
        logo_page,
        response.text,
        team
    )

    print(
        f"  High-definition source: "
        f"{image_url}"
    )

    image_response = session.get(
        image_url,
        timeout=REQUEST_TIMEOUT,
        allow_redirects=True,
    )

    image_response.raise_for_status()

    if not image_response.content:

        raise RuntimeError(
            "SportsLogos.Net returned an "
            "empty image."
        )

    try:

        image = Image.open(
            io.BytesIO(
                image_response.content
            )
        )

        image.load()

    except Exception as exc:

        raise RuntimeError(
            f"Could not decode SportsLogos.Net "
            f"image: {exc}"
        )

    image = image.convert(
        "RGBA"
    )

    if (
        image.width <= 0
        or image.height <= 0
    ):

        raise RuntimeError(
            "SportsLogos.Net image has "
            "invalid dimensions."
        )

    print(
        "  Source type: "
        "SPORTSLOGOS.NET CURRENT PRIMARY"
    )

    print(
        f"  Source size: "
        f"{image.width}x{image.height}"
    )

    return image


# ============================================================
# DISCOVER EXISTING LIBRARY
# ============================================================

def discover_files():

    for league in sorted(
        LEAGUES
    ):

        league_dir = ROOT / league

        if not league_dir.is_dir():
            continue

        for path in sorted(
            league_dir.rglob("*.png")
        ):

            yield league, path


def teams_from_file(
    path
):

    filename = path.stem

    if "_vs_" in filename:

        home, away = filename.split(
            "_vs_",
            1
        )

        return [
            display_team_name(home),
            display_team_name(away),
        ]

    return [
        display_team_name(filename)
    ]


def discover_all_teams():

    teams = {
        league: {}
        for league in LEAGUES
    }

    for league, path in discover_files():

        for team in teams_from_file(
            path
        ):

            key = clean_name(
                team
            )

            teams[league][key] = team

    return teams


# ============================================================
# TEMP DIRECTORY
# ============================================================

def reset_temp_directory():

    if TEMP_ROOT.exists():

        shutil.rmtree(
            TEMP_ROOT
        )

    for league in sorted(
        LEAGUES
    ):

        (
            TEMP_ROOT / league
        ).mkdir(
            parents=True,
            exist_ok=True
        )


# ============================================================
# DOWNLOAD ALL CURRENT PRIMARY LOGOS
# ============================================================

def download_all_logos(
    teams_by_league
):

    print()
    print("=" * 70)
    print(
        "DOWNLOADING SPORTSLOGOS.NET PRIMARY LOGOS"
    )
    print("=" * 70)

    print()
    print(
        "Source: SportsLogos.Net"
    )

    print(
        "Selection: newest available Primary Logo"
    )

    print(
        "Primary Dark / Alternate / Jersey / "
        "Cap / Wordmark logos are excluded."
    )

    print(
        f"HTTP request timeout: "
        f"{REQUEST_TIMEOUT} seconds"
    )

    reset_temp_directory()

    downloaded = {}

    failures = []

    total_expected = sum(
        len(value)
        for value in teams_by_league.values()
    )

    total_done = 0

    for league in sorted(
        LEAGUES
    ):

        teams = sorted(
            teams_by_league[league].values(),
            key=clean_name
        )

        print()
        print(
            f"{league}: expected {len(teams)}"
        )

        downloaded[league] = {}

        for number, team in enumerate(
            teams,
            start=1
        ):

            print()
            print(
                f"[{league} "
                f"{number}/{len(teams)}] "
                f"{team}"
            )

            try:

                image = download_sportslogos_logo(
                    league,
                    team
                )

                destination = (
                    TEMP_ROOT
                    / league
                    / f"{team}.png"
                )

                image.save(
                    destination,
                    "PNG",
                    optimize=True
                )

                with Image.open(
                    destination
                ) as verify:

                    verify.load()

                    if (
                        verify.width <= 0
                        or verify.height <= 0
                    ):

                        raise RuntimeError(
                            "Downloaded image "
                            "failed verification."
                        )

                downloaded[league][
                    clean_name(team)
                ] = destination

                total_done += 1

                print(
                    f"  Saved: {destination}"
                )

            except Exception as exc:

                failures.append(
                    (
                        league,
                        team,
                        str(exc)
                    )
                )

                print(
                    f"  ERROR: {exc}"
                )

    print()
    print("=" * 70)
    print("TEMPORARY SOURCE LIBRARY")
    print("=" * 70)

    print(
        f"SportsLogos.Net primary logos downloaded: "
        f"{total_done}/{total_expected}"
    )

    if failures:

        print()
        print(
            "FAILED LOGOS:"
        )

        for league, team, error in failures:

            print(
                f"  {league}: {team}"
            )

            print(
                f"    {error}"
            )

        raise RuntimeError(
            f"Only {total_done} of "
            f"{total_expected} logos downloaded."
        )

    return downloaded


# ============================================================
# VERIFY TEMP LIBRARY
# ============================================================

def verify_temp_library(
    teams_by_league,
    downloaded
):

    print()
    print("=" * 70)
    print("VERIFYING TEMPORARY LOGO LIBRARY")
    print("=" * 70)

    expected = 0
    found = 0

    for league in sorted(
        LEAGUES
    ):

        teams = teams_by_league[
            league
        ]

        expected += len(
            teams
        )

        for team in teams.values():

            path = downloaded[
                league
            ].get(
                clean_name(team)
            )

            if not path:

                raise RuntimeError(
                    f"Missing temporary logo: "
                    f"{league}: {team}"
                )

            if not path.is_file():

                raise RuntimeError(
                    f"Missing temporary file: "
                    f"{path}"
                )

            try:

                with Image.open(
                    path
                ) as image:

                    image.verify()

            except Exception as exc:

                raise RuntimeError(
                    f"Invalid temporary logo "
                    f"{path}: {exc}"
                )

            found += 1

    print(
        f"Verified {found}/{expected} "
        f"temporary logos."
    )

    if found != expected:

        raise RuntimeError(
            "Temporary logo count does not "
            "match expected team count."
        )


# ============================================================
# IMAGE PROCESSING
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
        or image.height <= 0
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
            image.width * scale
        )
    )

    height = max(
        1,
        int(
            image.height * scale
        )
    )

    return image.resize(
        (width, height),
        Image.Resampling.LANCZOS
    )


def existing_dimensions(
    path
):

    with Image.open(
        path
    ) as image:

        return image.size


# ============================================================
# REBUILD SOLO
# ============================================================

def rebuild_solo(
    path,
    source_path
):

    width, height = existing_dimensions(
        path
    )

    with Image.open(
        source_path
    ) as source:

        source = source.convert(
            "RGBA"
        )

        logo = fit_logo(
            source,
            int(width * 0.90),
            int(height * 0.90)
        )

    canvas = Image.new(
        "RGBA",
        (width, height),
        (0, 0, 0, 0)
    )

    x = (
        width - logo.width
    ) // 2

    y = (
        height - logo.height
    ) // 2

    canvas.alpha_composite(
        logo,
        (x, y)
    )

    canvas.save(
        path,
        "PNG",
        optimize=True
    )


# ============================================================
# REBUILD MATCHUP
# ============================================================

def rebuild_matchup(
    path,
    home_source,
    away_source
):

    width, height = existing_dimensions(
        path
    )

    with Image.open(
        home_source
    ) as home_image:

        home_image = home_image.convert(
            "RGBA"
        )

        home = fit_logo(
            home_image,
            int((width // 2) * 0.88),
            int(height * 0.88)
        )

    with Image.open(
        away_source
    ) as away_image:

        away_image = away_image.convert(
            "RGBA"
        )

        away = fit_logo(
            away_image,
            int((width // 2) * 0.88),
            int(height * 0.88)
        )

    half_width = width // 2

    canvas = Image.new(
        "RGBA",
        (width, height),
        (0, 0, 0, 0)
    )

    home_x = (
        half_width - home.width
    ) // 2

    home_y = (
        height - home.height
    ) // 2

    away_x = (
        half_width
        + (
            (half_width - away.width)
            // 2
        )
    )

    away_y = (
        height - away.height
    ) // 2

    canvas.alpha_composite(
        home,
        (home_x, home_y)
    )

    canvas.alpha_composite(
        away,
        (away_x, away_y)
    )

    canvas.save(
        path,
        "PNG",
        optimize=True
    )


# ============================================================
# SINGLE REBUILD JOB
# ============================================================

def rebuild_one(
    league,
    path,
    downloaded
):

    started = time.monotonic()

    teams = teams_from_file(
        path
    )

    if len(teams) == 1:

        team = teams[0]

        source = downloaded[
            league
        ][
            clean_name(team)
        ]

        rebuild_solo(
            path,
            source
        )

        details = (
            f"TEAM: {team}"
        )

    else:

        home_team = teams[0]
        away_team = teams[1]

        home_source = downloaded[
            league
        ][
            clean_name(home_team)
        ]

        away_source = downloaded[
            league
        ][
            clean_name(away_team)
        ]

        rebuild_matchup(
            path,
            home_source,
            away_source
        )

        details = (
            f"HOME: {home_team} | "
            f"AWAY: {away_team}"
        )

    elapsed = (
        time.monotonic()
        - started
    )

    if elapsed > REBUILD_TIMEOUT:

        raise TimeoutError(
            f"Rebuild exceeded "
            f"{REBUILD_TIMEOUT} second timeout "
            f"({elapsed:.1f}s)"
        )

    return (
        league,
        path,
        details
    )


# ============================================================
# REBUILD PASS
# ============================================================

def rebuild_pass(
    files,
    downloaded,
    pass_number,
    total_passes
):

    if not files:

        return (
            [],
            0
        )

    total = len(
        files
    )

    completed = 0
    replaced = 0
    failed = []

    print()
    print("=" * 70)
    print(
        f"REBUILD PASS "
        f"{pass_number}/{total_passes}"
    )
    print("=" * 70)

    print()
    print(
        f"Processing {total} files with "
        f"{REBUILD_WORKERS} workers..."
    )

    print(
        f"Per-file safety timeout: "
        f"{REBUILD_TIMEOUT} seconds"
    )

    print()

    with ThreadPoolExecutor(
        max_workers=REBUILD_WORKERS
    ) as executor:

        futures = {
            executor.submit(
                rebuild_one,
                league,
                path,
                downloaded
            ): (
                league,
                path
            )
            for league, path in files
        }

        for future in as_completed(
            futures
        ):

            league, path = futures[
                future
            ]

            completed += 1

            try:

                result_league, result_path, details = (
                    future.result()
                )

                replaced += 1

                print(
                    f"[{completed}/{total}] "
                    f"[PASS {pass_number}] "
                    f"[{result_league}] "
                    f"{result_path}"
                )

                print(
                    f"  {details}"
                )

            except Exception as exc:

                failed.append(
                    (
                        league,
                        path,
                        str(exc)
                    )
                )

                print(
                    f"[{completed}/{total}] "
                    f"[PASS {pass_number}] "
                    f"FAILED: {path}"
                )

                print(
                    f"  Reason: {exc}"
                )

    return (
        failed,
        replaced
    )


# ============================================================
# REBUILD EXISTING LIBRARY
# ============================================================

def rebuild_library(
    downloaded
):

    files = list(
        discover_files()
    )

    total = len(
        files
    )

    all_failures = {}

    total_replaced = 0

    pending = files

    # Initial pass + retry passes.
    total_passes = (
        1
        + REBUILD_RETRY_PASSES
    )

    for pass_number in range(
        1,
        total_passes + 1
    ):

        if not pending:
            break

        failed, replaced = rebuild_pass(
            pending,
            downloaded,
            pass_number,
            total_passes
        )

        total_replaced += replaced

        for league, path, error in failed:

            all_failures[
                (league, path)
            ] = error

        failed_keys = {
            (league, path)
            for league, path, error in failed
        }

        pending = [
            item
            for item in pending
            if item in failed_keys
        ]

        if pending:

            if pass_number < total_passes:

                print()
                print("=" * 70)
                print(
                    f"{len(pending)} files failed "
                    f"PASS {pass_number}."
                )

                print(
                    "They will be retried "
                    f"in PASS {pass_number + 1}."
                )

                print("=" * 70)

                time.sleep(1)

            else:

                print()
                print("=" * 70)
                print(
                    "FILES STILL FAILED AFTER "
                    f"{total_passes} PASSES"
                )
                print("=" * 70)

        else:

            print()
            print("=" * 70)
            print(
                f"PASS {pass_number} COMPLETE"
            )
            print(
                "All remaining files succeeded."
            )
            print("=" * 70)

    final_failures = []

    for league, path in pending:

        error = all_failures.get(
            (league, path),
            "Unknown failure"
        )

        final_failures.append(
            (
                league,
                path,
                error
            )
        )

    return (
        total,
        total_replaced,
        final_failures,
        total_passes
    )


# ============================================================
# FINAL VERIFY
# ============================================================

def verify_existing_library():

    print()
    print("=" * 70)
    print("VERIFYING REBUILT SPORTS LOGO LIBRARY")
    print("=" * 70)

    count = 0

    for league, path in discover_files():

        try:

            with Image.open(
                path
            ) as image:

                image.verify()

                if image.format != "PNG":

                    raise RuntimeError(
                        f"File is not PNG: "
                        f"{image.format}"
                    )

            count += 1

        except Exception as exc:

            raise RuntimeError(
                f"Invalid rebuilt image "
                f"{path}: {exc}"
            )

    print(
        f"Verified {count} existing "
        f"PNG logo files."
    )


# ============================================================
# CLEAN TEMP DIRECTORY
# ============================================================

def cleanup_temp_directory():

    if TEMP_ROOT.exists():

        print()
        print(
            "Deleting temporary source logo library..."
        )

        shutil.rmtree(
            TEMP_ROOT
        )

        print(
            f"Removed: {TEMP_ROOT}"
        )


# ============================================================
# MAIN
# ============================================================

def main():

    print()
    print("=" * 70)
    print("SPORTS LOGO LIBRARY REBUILDER")
    print("=" * 70)

    print()
    print(
        "Logo source: SportsLogos.Net"
    )

    print(
        "Logo selection: newest available Primary Logo"
    )

    print(
        "Primary Dark / Alternate / Jersey / "
        "Cap / Wordmark logos are excluded."
    )

    if not ROOT.is_dir():

        print()
        print(
            f"ERROR: {ROOT} does not exist."
        )

        sys.exit(1)

    teams_by_league = discover_all_teams()

    total_teams = sum(
        len(value)
        for value in teams_by_league.values()
    )

    if total_teams == 0:

        print()
        print(
            "ERROR: No existing PNG logos found."
        )

        sys.exit(1)

    print()
    print(
        f"Existing library contains "
        f"{total_teams} unique league/team "
        f"combinations."
    )

    for league in sorted(
        LEAGUES
    ):

        print(
            f"  {league}: "
            f"{len(teams_by_league[league])} "
            f"unique teams used by existing library"
        )

    # --------------------------------------------------------
    # DOWNLOAD PRIMARY LOGOS FIRST.
    #
    # sports-logos is untouched during this phase.
    # --------------------------------------------------------

    try:

        downloaded = download_all_logos(
            teams_by_league
        )

        verify_temp_library(
            teams_by_league,
            downloaded
        )

    except Exception as exc:

        print()
        print("=" * 70)
        print("ABORTED DURING DOWNLOAD")
        print("=" * 70)

        print()
        print(
            "Existing sports-logos library "
            "was NOT modified."
        )

        print()
        print(
            f"Reason: {exc}"
        )

        sys.exit(1)

    # --------------------------------------------------------
    # ALL SOURCE LOGOS EXIST.
    #
    # NOW rebuild the actual library.
    # --------------------------------------------------------

    print()
    print("=" * 70)
    print("REBUILDING EXISTING SPORTS LOGO LIBRARY")
    print("=" * 70)

    total, replaced, failed, total_passes = rebuild_library(
        downloaded
    )

    # --------------------------------------------------------
    # FINAL FAILURE REPORT
    # --------------------------------------------------------

    if failed:

        print()
        print("=" * 70)
        print("REBUILD FAILED")
        print("=" * 70)

        print()
        print(
            f"Files found:        {total}"
        )

        print(
            f"Files rebuilt:      {replaced}"
        )

        print(
            f"Files still failed: {len(failed)}"
        )

        print(
            f"Total attempts:     {total_passes}"
        )

        print()
        print(
            "FINAL FAILURE SUMMARY"
        )

        print(
            "-" * 70
        )

        for league, path, error in failed:

            print()
            print(
                f"LEAGUE: {league}"
            )

            print(
                f"FILE:   {path}"
            )

            print(
                f"ERROR:  {error}"
            )

        print()
        print(
            "-" * 70
        )

        print()
        print(
            "The failed files were skipped after "
            f"{total_passes} total attempts."
        )

        print(
            "The temporary source logos were "
            "NOT deleted."
        )

        print(
            f"Temporary source directory: "
            f"{TEMP_ROOT}"
        )

        sys.exit(1)

    # --------------------------------------------------------
    # FINAL VALIDATION.
    # --------------------------------------------------------

    try:

        verify_existing_library()

    except Exception as exc:

        print()
        print("=" * 70)
        print("FINAL VERIFICATION FAILED")
        print("=" * 70)

        print()
        print(
            str(exc)
        )

        print()
        print(
            "Temporary source logos were "
            "NOT deleted."
        )

        sys.exit(1)

    # --------------------------------------------------------
    # EVERYTHING PASSED.
    #
    # Delete the temporary source library.
    # --------------------------------------------------------

    cleanup_temp_directory()

    print()
    print("=" * 70)
    print("FINISHED")
    print("=" * 70)

    print()
    print(
        f"Unique source logos: {total_teams}"
    )

    print(
        f"Existing files found: {total}"
    )

    print(
        f"Files replaced: {replaced}"
    )

    print(
        "Files failed: 0"
    )

    print()

    print(
        "All existing filenames and "
        "directory paths were preserved."
    )

    print(
        "All rebuilt logos remain PNG."
    )

    print(
        "SportsLogos.Net was used as the "
        "logo source."
    )

    print(
        "The newest available Primary Logo "
        "was selected for each team."
    )

    print(
        "Primary Dark, Alternate, Jersey, "
        "Cap, and Wordmark logos were excluded."
    )

    print(
        f"Rebuild workers: {REBUILD_WORKERS}"
    )

    print(
        f"HTTP request timeout: "
        f"{REQUEST_TIMEOUT} seconds."
    )

    print(
        f"Per-file rebuild timeout: "
        f"{REBUILD_TIMEOUT} seconds."
    )

    print(
        f"Total rebuild attempts: "
        f"{total_passes}"
    )

    print(
        "Temporary source logos were deleted."
    )


if __name__ == "__main__":

    main()
