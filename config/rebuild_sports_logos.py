import io
import os
import re
import sys
import shutil
import tempfile
import unicodedata
from pathlib import Path
from difflib import SequenceMatcher
from urllib.parse import urljoin
from html.parser import HTMLParser

import requests
from PIL import Image

try:
    import cairosvg
except ImportError:
    cairosvg = None


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

LOGO_CDN_BASE = "https://logocdn.com"

LEAGUE_URLS = {
    "MLB": f"{LOGO_CDN_BASE}/mlb/",
    "NBA": f"{LOGO_CDN_BASE}/nba/",
    "NFL": f"{LOGO_CDN_BASE}/nfl/",
    "NHL": f"{LOGO_CDN_BASE}/nhl/",
}

REQUEST_TIMEOUT = 30

REQUEST_DELAY = 0.15

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/151.0 Safari/537.36"
    )
}


# ============================================================
# TEAM NAME ALIASES
# ============================================================

ALIASES = {
    "Los_Angeles_Angels":
        "Los Angeles Angels",

    "Los_Angeles_Angels_Of_Anaheim":
        "Los Angeles Angels",

    "Cleveland_Indians":
        "Cleveland Guardians",

    "Washington_Redskins":
        "Washington Commanders",

    "Washington_Football_Team":
        "Washington Commanders",

    "New_Jersey_Nets":
        "Brooklyn Nets",

    "Charlotte_Bobcats":
        "Charlotte Hornets",

    "Phoenix_Coyotes":
        "Arizona Coyotes",

    "Atlanta_Thrashers":
        "Winnipeg Jets",

    "Oakland_Athletics":
        "Athletics",

    "Las_Vegas_Raiders":
        "Las Vegas Raiders",

    "St_Louis_Rams":
        "Los Angeles Rams",

    "San_Diego_Chargers":
        "Los Angeles Chargers",

    # Current NHL naming
    "Utah_Hockey_Club":
        "Utah Mammoth",
}


# ============================================================
# NORMALIZATION
# ============================================================

def clean_name(value):

    value = os.path.splitext(
        str(value)
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
        str(raw)
    )[0]

    if raw in ALIASES:

        return ALIASES[raw]

    return raw.replace(
        "_",
        " "
    )


def filename_team_name(raw):

    return display_team_name(
        raw
    )


# ============================================================
# HTTP
# ============================================================

session = requests.Session()

session.headers.update(
    HEADERS
)


def get(url):

    response = session.get(
        url,
        timeout=REQUEST_TIMEOUT
    )

    response.raise_for_status()

    return response


# ============================================================
# HTML PARSER
# ============================================================

class LogoCDNParser(HTMLParser):

    def __init__(self):

        super().__init__(
            convert_charrefs=True
        )

        self.images = []

        self.links = []

        self.current_link = None

        self.current_text = []

    def handle_starttag(
        self,
        tag,
        attrs
    ):

        attributes = dict(
            attrs
        )

        tag = tag.lower()

        if tag == "img":

            self.images.append(
                attributes
            )

        elif tag == "a":

            self.current_link = {
                "href":
                    attributes.get(
                        "href"
                    ),

                "text": []
            }

            self.current_text = []

    def handle_data(
        self,
        data
    ):

        if self.current_link is not None:

            self.current_text.append(
                data
            )

    def handle_endtag(
        self,
        tag
    ):

        if tag.lower() != "a":

            return

        if self.current_link is not None:

            self.current_link[
                "text"
            ] = " ".join(
                self.current_text
            ).strip()

            self.links.append(
                self.current_link
            )

        self.current_link = None

        self.current_text = []


# ============================================================
# TEAM MATCHING
# ============================================================

def score_name(
    wanted,
    candidate
):

    wanted = clean_name(
        wanted
    )

    candidate = clean_name(
        candidate
    )

    if not wanted or not candidate:

        return 0.0

    if wanted == candidate:

        return 1.0

    if wanted in candidate:

        return 0.97

    if candidate in wanted:

        return 0.95

    return SequenceMatcher(
        None,
        wanted,
        candidate
    ).ratio()


def team_variations(team):

    original = display_team_name(
        team
    )

    variations = [
        original
    ]

    normalized = clean_name(
        original
    )

    replacements = {
        "los angeles angels":
            [
                "Los Angeles Angels",
                "Los Angeles Angels of Anaheim",
                "Anaheim Angels",
            ],

        "athletics":
            [
                "Athletics",
                "Oakland Athletics",
            ],

        "arizona coyotes":
            [
                "Arizona Coyotes",
                "Phoenix Coyotes",
            ],

        "utah mammoth":
            [
                "Utah Mammoth",
                "Utah Hockey Club",
            ],

        "brooklyn nets":
            [
                "Brooklyn Nets",
                "New Jersey Nets",
            ],

        "charlotte hornets":
            [
                "Charlotte Hornets",
                "Charlotte Bobcats",
            ],

        "winnipeg jets":
            [
                "Winnipeg Jets",
                "Atlanta Thrashers",
            ],
    }

    if normalized in replacements:

        variations.extend(
            replacements[
                normalized
            ]
        )

    output = []

    seen = set()

    for value in variations:

        key = clean_name(
            value
        )

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
# EXTRACT IMAGE URL
# ============================================================

def extract_image_urls(
    page_url,
    html_text,
    parser
):

    candidates = []

    # --------------------------------------------------------
    # IMG TAGS
    # --------------------------------------------------------

    for img in parser.images:

        for attribute in (
            "src",
            "data-src",
            "data-lazy-src",
            "data-original",
        ):

            value = img.get(
                attribute
            )

            if not value:

                continue

            value = value.strip()

            value = urljoin(
                page_url,
                value
            )

            if value not in candidates:

                candidates.append(
                    value
                )

    # --------------------------------------------------------
    # RAW HTML
    # --------------------------------------------------------

    patterns = [

        r'https?://[^"\']+\.(?:svg|png|webp)',

        r'//[^"\']+\.(?:svg|png|webp)',

    ]

    for pattern in patterns:

        matches = re.findall(
            pattern,
            html_text,
            re.IGNORECASE
        )

        for value in matches:

            value = value.strip()

            if value.startswith(
                "//"
            ):

                value = (
                    "https:"
                    + value
                )

            value = value.replace(
                "\\/",
                "/"
            )

            if value not in candidates:

                candidates.append(
                    value
                )

    # --------------------------------------------------------
    # PREFER SVG
    # --------------------------------------------------------

    svg = [
        x
        for x in candidates
        if ".svg" in x.lower()
    ]

    if svg:

        return svg

    png = [
        x
        for x in candidates
        if ".png" in x.lower()
    ]

    if png:

        return png

    return candidates


# ============================================================
# GET CURRENT TEAM LOGOS FROM LOGO CDN
# ============================================================

SOURCE_CACHE = {}


def collect_league_sources(
    league
):

    if league in SOURCE_CACHE:

        return SOURCE_CACHE[
            league
        ]

    url = LEAGUE_URLS[
        league
    ]

    print()

    print(
        f"Downloading {league} logo index:"
    )

    print(
        f"  {url}"
    )

    response = get(
        url
    )

    parser = LogoCDNParser()

    parser.feed(
        response.text
    )

    entries = []

    seen = set()

    # --------------------------------------------------------
    # Logo CDN pages contain links surrounding the current
    # team logo. We identify those links and inspect the
    # nearby image references.
    # --------------------------------------------------------

    for link in parser.links:

        title = link.get(
            "text",
            ""
        ).strip()

        href = link.get(
            "href"
        )

        if not title or not href:

            continue

        # Ignore navigation/history links.
        if (
            "histor" in title.lower()
            or "see " in title.lower()
            or "missing" in title.lower()
        ):

            continue

        href = urljoin(
            url,
            href
        )

        # ----------------------------------------------------
        # Team names on Logo CDN are headings/links. Only keep
        # names that look like team entries.
        # ----------------------------------------------------

        if len(
            title.split()
        ) < 2:

            continue

        key = (
            clean_name(title),
            href
        )

        if key in seen:

            continue

        seen.add(
            key
        )

        entries.append(
            {
                "name":
                    title,

                "page":
                    href,
            }
        )

    # --------------------------------------------------------
    # If links aren't sufficient, parse image alt/title data.
    # --------------------------------------------------------

    for image in parser.images:

        title = (
            image.get("alt")
            or image.get("title")
            or ""
        ).strip()

        src = (
            image.get("src")
            or image.get("data-src")
            or ""
        ).strip()

        if not title or not src:

            continue

        if len(
            title.split()
        ) < 2:

            continue

        key = (
            clean_name(title),
            src
        )

        if key in seen:

            continue

        seen.add(
            key
        )

        entries.append(
            {
                "name":
                    title,

                "image":
                    urljoin(
                        url,
                        src
                    ),
            }
        )

    # --------------------------------------------------------
    # Download each candidate team page where necessary.
    # --------------------------------------------------------

    resolved = []

    resolved_names = set()

    for entry in entries:

        name = entry[
            "name"
        ]

        page = entry.get(
            "page"
        )

        image = entry.get(
            "image"
        )

        if image:

            resolved.append(
                {
                    "name":
                        name,

                    "image":
                        image,

                    "page":
                        page or url,
                }
            )

            resolved_names.add(
                clean_name(name)
            )

            continue

        if not page:

            continue

        try:

            page_response = get(
                page
            )

            page_parser = LogoCDNParser()

            page_parser.feed(
                page_response.text
            )

            image_urls = (
                extract_image_urls(
                    page,
                    page_response.text,
                    page_parser
                )
            )

            if not image_urls:

                continue

            resolved.append(
                {
                    "name":
                        name,

                    "image":
                        image_urls[0],

                    "page":
                        page,
                }
            )

            resolved_names.add(
                clean_name(name)
            )

        except Exception:

            continue

    SOURCE_CACHE[
        league
    ] = resolved

    print(
        f"  Found {len(resolved)} logo entries."
    )

    return resolved


# ============================================================
# FIND TEAM SOURCE
# ============================================================

def find_team_source(
    league,
    team
):

    variations = team_variations(
        team
    )

    entries = collect_league_sources(
        league
    )

    scored = []

    for entry in entries:

        name = entry[
            "name"
        ]

        image = entry[
            "image"
        ]

        best = 0.0

        for variation in variations:

            best = max(
                best,
                score_name(
                    variation,
                    name
                )
            )

        scored.append(
            (
                best,
                name,
                image,
                entry.get(
                    "page"
                )
            )
        )

    if not scored:

        raise RuntimeError(
            f"No {league} logos were "
            "available from Logo CDN."
        )

    scored.sort(
        reverse=True,
        key=lambda x: x[0]
    )

    best = scored[0]

    if best[0] < 0.75:

        raise RuntimeError(
            f"Could not match "
            f"{league} team '{team}'. "
            f"Best result was '{best[1]}' "
            f"with score {best[0]:.3f}."
        )

    print(
        f"  Source match: {best[1]}"
    )

    print(
        f"  Score: {best[0]:.3f}"
    )

    print(
        f"  Image: {best[2]}"
    )

    return (
        best[2],
        best[3]
    )


# ============================================================
# DOWNLOAD AND DECODE LOGO
# ============================================================

IMAGE_CACHE = {}


def download_logo(
    league,
    team
):

    key = (
        league,
        clean_name(team)
    )

    if key in IMAGE_CACHE:

        return IMAGE_CACHE[
            key
        ].copy()

    image_url, page_url = (
        find_team_source(
            league,
            team
        )
    )

    response = get(
        image_url
    )

    content_type = (
        response.headers.get(
            "Content-Type",
            ""
        ).lower()
    )

    raw = response.content

    # --------------------------------------------------------
    # SVG
    # --------------------------------------------------------

    if (
        ".svg" in image_url.lower()
        or "svg" in content_type
        or raw.lstrip().startswith(
            b"<svg"
        )
    ):

        if cairosvg is None:

            raise RuntimeError(
                "CairoSVG is required to "
                f"process {team}."
            )

        png_bytes = (
            cairosvg.svg2png(
                bytestring=raw
            )
        )

        image = Image.open(
            io.BytesIO(
                png_bytes
            )
        )

    else:

        image = Image.open(
            io.BytesIO(
                raw
            )
        )

    image.load()

    image = image.convert(
        "RGBA"
    )

    IMAGE_CACHE[
        key
    ] = image

    return image.copy()


# ============================================================
# SAVE TEMP SOURCE LOGO
# ============================================================

def save_temp_logo(
    league,
    team,
    image
):

    league_dir = (
        TEMP_ROOT
        / league
    )

    league_dir.mkdir(
        parents=True,
        exist_ok=True
    )

    path = (
        league_dir
        / f"{team}.png"
    )

    image.save(
        path,
        "PNG",
        optimize=True
    )

    return path


# ============================================================
# DISCOVER EXISTING FILES
# ============================================================

def discover_files():

    for league in sorted(
        LEAGUES
    ):

        league_dir = (
            ROOT
            / league
        )

        if not league_dir.is_dir():

            continue

        for path in sorted(
            league_dir.rglob("*.png")
        ):

            yield (
                league,
                path
            )


def teams_from_file(
    path
):

    filename = path.stem

    if "_vs_" in filename:

        home, away = (
            filename.split(
                "_vs_",
                1
            )
        )

        return [
            display_team_name(home),
            display_team_name(away)
        ]

    return [
        display_team_name(filename)
    ]


# ============================================================
# DISCOVER ALL TEAMS IN EXISTING LIBRARY
# ============================================================

def discover_all_teams():

    teams = {}

    for league, path in discover_files():

        for team in teams_from_file(
            path
        ):

            key = (
                clean_name(team)
            )

            teams[
                (
                    league,
                    key
                )
            ] = team

    return teams


# ============================================================
# COMPLETE CURRENT BIG-4 SOURCE LIBRARY
#
# This downloads ALL current teams, not merely the teams found
# in existing files.
# ============================================================

def download_all_current_logos():

    print()

    print("=" * 70)
    print("DOWNLOADING CURRENT BIG-4 LOGOS")
    print("=" * 70)

    if TEMP_ROOT.exists():

        shutil.rmtree(
            TEMP_ROOT
        )

    TEMP_ROOT.mkdir(
        parents=True,
        exist_ok=True
    )

    total_expected = {
        "MLB": 30,
        "NBA": 30,
        "NFL": 32,
        "NHL": 32,
    }

    downloaded = 0

    failures = []

    for league in (
        "MLB",
        "NBA",
        "NFL",
        "NHL",
    ):

        print()

        print(
            f"{league}: "
            f"expected {total_expected[league]}"
        )

        sources = (
            collect_league_sources(
                league
            )
        )

        # ----------------------------------------------------
        # Build unique current-team matches.
        # ----------------------------------------------------

        selected = {}

        for source in sources:

            name = source[
                "name"
            ]

            key = clean_name(
                name
            )

            # Ignore obvious historical entries.
            if key in selected:

                continue

            selected[
                key
            ] = source

        # ----------------------------------------------------
        # Download every current source entry.
        # ----------------------------------------------------

        league_count = 0

        for number, source in enumerate(
            selected.values(),
            start=1
        ):

            team = source[
                "name"
            ]

            print()

            print(
                f"[{league} "
                f"{number}/{len(selected)}] "
                f"{team}"
            )

            try:

                image = download_logo(
                    league,
                    team
                )

                save_temp_logo(
                    league,
                    team,
                    image
                )

                league_count += 1

                downloaded += 1

                print(
                    f"  Saved: "
                    f"{TEMP_ROOT / league / (team + '.png')}"
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
                    f"  FAILED: {exc}"
                )

    print()

    print("=" * 70)
    print("TEMPORARY SOURCE LIBRARY")
    print("=" * 70)

    print()

    print(
        f"Logos downloaded: {downloaded}"
    )

    if failures:

        print()

        print(
            "Failures:"
        )

        for league, team, error in failures:

            print(
                f"  {league}: "
                f"{team} -> {error}"
            )

        raise RuntimeError(
            f"{len(failures)} source logo(s) "
            "failed to download."
        )

    # --------------------------------------------------------
    # Verify exact expected counts.
    # --------------------------------------------------------

    for league, expected in (
        total_expected.items()
    ):

        actual = len(
            list(
                (
                    TEMP_ROOT
                    / league
                ).glob("*.png")
            )
        )

        if actual != expected:

            raise RuntimeError(
                f"{league}: expected "
                f"{expected} logos but downloaded "
                f"{actual}."
            )

    print()

    print(
        "All 124 current team logos "
        "downloaded successfully."
    )


# ============================================================
# FIND TEMP LOGO FOR TEAM
# ============================================================

def find_temp_logo(
    league,
    team
):

    directory = (
        TEMP_ROOT
        / league
    )

    if not directory.is_dir():

        raise RuntimeError(
            f"Temporary {league} "
            "logo directory does not exist."
        )

    wanted = clean_name(
        team
    )

    candidates = []

    for path in directory.glob(
        "*.png"
    ):

        candidate = clean_name(
            path.stem
        )

        score = 0.0

        for variation in team_variations(
            team
        ):

            score = max(
                score,
                score_name(
                    variation,
                    candidate
                )
            )

        candidates.append(
            (
                score,
                path
            )
        )

    candidates.sort(
        reverse=True,
        key=lambda x: x[0]
    )

    if not candidates:

        raise RuntimeError(
            f"No temporary logo found "
            f"for {league}: {team}"
        )

    score, path = candidates[0]

    if score < 0.75:

        raise RuntimeError(
            f"Could not match temporary "
            f"{league} logo for {team}."
        )

    return path


# ============================================================
# LOAD TEMP LOGO
# ============================================================

def load_temp_logo(
    league,
    team
):

    path = find_temp_logo(
        league,
        team
    )

    with Image.open(
        path
    ) as image:

        image.load()

        return image.convert(
            "RGBA"
        ).copy()


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
    league,
    team
):

    width, height = (
        existing_dimensions(
            path
        )
    )

    source = load_temp_logo(
        league,
        team
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
    league,
    home_team,
    away_team
):

    width, height = (
        existing_dimensions(
            path
        )
    )

    home_source = load_temp_logo(
        league,
        home_team
    )

    away_source = load_temp_logo(
        league,
        away_team
    )

    half_width = width // 2

    home = fit_logo(
        home_source,
        int(half_width * 0.88),
        int(height * 0.88)
    )

    away = fit_logo(
        away_source,
        int(half_width * 0.88),
        int(height * 0.88)
    )

    canvas = Image.new(
        "RGBA",
        (width, height),
        (0, 0, 0, 0)
    )

    home_x = (
        half_width
        - home.width
    ) // 2

    home_y = (
        height
        - home.height
    ) // 2

    away_x = (
        half_width
        + (
            (
                half_width
                - away.width
            ) // 2
        )
    )

    away_y = (
        height
        - away.height
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
# BUILD NEW LIBRARY IN STAGING DIRECTORY
# ============================================================

def build_staging_library():

    print()

    print("=" * 70)
    print("BUILDING STAGED SPORTS-LOGOS LIBRARY")
    print("=" * 70)

    staging = Path(
        tempfile.mkdtemp(
            prefix="sports-logos-build-"
        )
    )

    try:

        # ----------------------------------------------------
        # Preserve the exact existing directory structure.
        # ----------------------------------------------------

        files = list(
            discover_files()
        )

        total = len(
            files
        )

        rebuilt = 0

        failures = []

        for number, (
            league,
            original_path
        ) in enumerate(
            files,
            start=1
        ):

            relative = (
                original_path.relative_to(
                    ROOT
                )
            )

            destination = (
                staging
                / relative
            )

            destination.parent.mkdir(
                parents=True,
                exist_ok=True
            )

            shutil.copy2(
                original_path,
                destination
            )

            teams = teams_from_file(
                original_path
            )

            try:

                if len(teams) == 1:

                    print()

                    print(
                        f"[{number}/{total}] "
                        f"{league} SOLO"
                    )

                    print(
                        f"  {relative}"
                    )

                    rebuild_solo(
                        destination,
                        league,
                        teams[0]
                    )

                else:

                    print()

                    print(
                        f"[{number}/{total}] "
                        f"{league} MATCHUP"
                    )

                    print(
                        f"  {relative}"
                    )

                    print(
                        f"  HOME: {teams[0]}"
                    )

                    print(
                        f"  AWAY: {teams[1]}"
                    )

                    rebuild_matchup(
                        destination,
                        league,
                        teams[0],
                        teams[1]
                    )

                rebuilt += 1

            except Exception as exc:

                failures.append(
                    (
                        league,
                        relative,
                        str(exc)
                    )
                )

        if failures:

            print()

            print(
                "Staged rebuild failed."
            )

            for league, path, error in failures:

                print(
                    f"  {league}: "
                    f"{path} -> {error}"
                )

            raise RuntimeError(
                f"{len(failures)} library "
                "file(s) failed to rebuild."
            )

        print()

        print(
            f"Successfully rebuilt "
            f"{rebuilt}/{total} existing files."
        )

        return staging

    except Exception:

        shutil.rmtree(
            staging,
            ignore_errors=True
        )

        raise


# ============================================================
# ATOMICALLY REPLACE EXISTING LIBRARY
# ============================================================

def replace_library(
    staging
):

    print()

    print("=" * 70)
    print("REPLACING EXISTING SPORTS-LOGOS LIBRARY")
    print("=" * 70)

    backup = (
        ROOT.parent
        / (
            ROOT.name
            + ".backup"
        )
    )

    if backup.exists():

        shutil.rmtree(
            backup
        )

    # --------------------------------------------------------
    # Move current library out of the way.
    # --------------------------------------------------------

    if ROOT.exists():

        ROOT.rename(
            backup
        )

    try:

        staging.rename(
            ROOT
        )

    except Exception:

        if ROOT.exists():

            shutil.rmtree(
                ROOT
            )

        if backup.exists():

            backup.rename(
                ROOT
            )

        raise

    # --------------------------------------------------------
    # New library is now active.
    # Remove backup only after successful replacement.
    # --------------------------------------------------------

    if backup.exists():

        shutil.rmtree(
            backup
        )

    print()

    print(
        "Existing sports-logos library "
        "successfully replaced."
    )


# ============================================================
# MAIN
# ============================================================

def main():

    print()

    print("=" * 70)
    print("SPORTS LOGO LIBRARY REBUILDER")
    print("=" * 70)

    if not ROOT.is_dir():

        print()

        print(
            f"ERROR: {ROOT} does not exist."
        )

        sys.exit(1)

    existing = discover_all_teams()

    if not existing:

        print()

        print(
            "ERROR: No existing sports logos found."
        )

        sys.exit(1)

    print()

    print(
        f"Existing library contains "
        f"{len(existing)} unique "
        "league/team combinations."
    )

    print()

    for league in sorted(
        LEAGUES
    ):

        count = sum(
            1
            for (
                existing_league,
                _key
            ) in existing
            if existing_league == league
        )

        print(
            f"  {league}: "
            f"{count} unique teams used "
            "by existing library"
        )

    # ========================================================
    # STEP 1
    # DOWNLOAD ALL 124 CURRENT LOGOS
    # ========================================================

    try:

        download_all_current_logos()

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

    # ========================================================
    # STEP 2
    # BUILD ENTIRE LIBRARY IN STAGING
    # ========================================================

    staging = None

    try:

        staging = (
            build_staging_library()
        )

    except Exception as exc:

        print()

        print("=" * 70)
        print("ABORTED DURING REBUILD")
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

    # ========================================================
    # STEP 3
    # REPLACE EXISTING LIBRARY
    # ========================================================

    try:

        replace_library(
            staging
        )

    except Exception as exc:

        print()

        print("=" * 70)
        print("ABORTED DURING REPLACEMENT")
        print("=" * 70)

        print()

        print(
            "Existing sports-logos library "
            "was restored/left untouched."
        )

        print()

        print(
            f"Reason: {exc}"
        )

        if staging and staging.exists():

            shutil.rmtree(
                staging,
                ignore_errors=True
            )

        sys.exit(1)

    # ========================================================
    # CLEAN TEMP SOURCE LIBRARY
    # ========================================================

    if TEMP_ROOT.exists():

        shutil.rmtree(
            TEMP_ROOT
        )

    # ========================================================
    # FINAL
    # ========================================================

    print()

    print("=" * 70)
    print("FINISHED")
    print("=" * 70)

    print()

    print(
        "Downloaded: 124 current MLB/NBA/NFL/NHL logos"
    )

    print(
        "Rebuilt:   existing sports-logos library"
    )

    print(
        "Structure: preserved"
    )

    print(
        "Filenames: preserved"
    )

    print(
        "Temporary source library: removed"
    )

    print()

    print(
        "No logo library replacement occurred "
        "until all source logos and rebuilds succeeded."
    )


if __name__ == "__main__":

    main()
