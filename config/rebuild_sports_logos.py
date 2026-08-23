import io
import os
import re
import sys
import time
import shutil
import unicodedata
from pathlib import Path

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

REQUEST_TIMEOUT = 30
REQUEST_DELAY = 0.10

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/151.0 Safari/537.36"
    )
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
# LOGOCDN SLUG OVERRIDES
#
# Logocdn does NOT always use the visible team name as its
# image filename.
#
# The important example:
#
# LA Clippers -> los-angeles-clippers
#
# Add explicit mappings here rather than trying to guess
# endlessly from display names.
# ============================================================

LOGOCDN_SLUG_OVERRIDES = {

    # --------------------------------------------------------
    # NBA
    # --------------------------------------------------------

    ("NBA", "LA Clippers"):
        ["los-angeles-clippers", "la-clippers"],

    ("NBA", "LA Lakers"):
        ["los-angeles-lakers", "la-lakers"],

    ("NBA", "New Orleans Pelicans"):
        ["new-orleans-pelicans"],

    ("NBA", "Oklahoma City Thunder"):
        ["oklahoma-city-thunder"],

    ("NBA", "Golden State Warriors"):
        ["golden-state-warriors"],

    ("NBA", "Portland Trail Blazers"):
        ["portland-trail-blazers"],

    ("NBA", "Minnesota Timberwolves"):
        ["minnesota-timberwolves"],

    ("NBA", "San Antonio Spurs"):
        ["san-antonio-spurs"],

    # --------------------------------------------------------
    # MLB
    # --------------------------------------------------------

    ("MLB", "St Louis Cardinals"):
        ["st-louis-cardinals", "st-louis-cardinals"],

    ("MLB", "Athletics"):
        ["athletics", "oakland-athletics"],

    ("MLB", "Los Angeles Angels"):
        [
            "los-angeles-angels",
            "los-angeles-angels-of-anaheim",
        ],

    # --------------------------------------------------------
    # NFL
    # --------------------------------------------------------

    ("NFL", "Los Angeles Rams"):
        ["los-angeles-rams", "st-louis-rams"],

    ("NFL", "Los Angeles Chargers"):
        ["los-angeles-chargers", "san-diego-chargers"],

    ("NFL", "Washington Commanders"):
        ["washington-commanders"],

    # --------------------------------------------------------
    # NHL
    # --------------------------------------------------------

    ("NHL", "Utah Mammoth"):
        ["utah-mammoth"],

    ("NHL", "Utah Hockey Club"):
        ["utah-mammoth", "utah-hockey-club"],

    ("NHL", "St Louis Blues"):
        ["st-louis-blues"],

    ("NHL", "New Jersey Devils"):
        ["new-jersey-devils"],

    ("NHL", "New York Islanders"):
        ["new-york-islanders"],

    ("NHL", "New York Rangers"):
        ["new-york-rangers"],
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


# ============================================================
# GENERIC SLUG GENERATION
# ============================================================

def generic_slugs(team):

    normalized = clean_name(
        team
    )

    slug = normalized.replace(
        " ",
        "-"
    )

    values = [
        slug
    ]

    # Common punctuation/name variations.
    values.append(
        slug.replace(
            "st-",
            "saint-"
        )
    )

    # NBA abbreviated LA naming.
    if normalized.startswith("la "):

        values.append(
            normalized.replace(
                "la ",
                "los-angeles-"
            ).replace(
                " ",
                "-"
            )
        )

    # Remove common suffixes that occasionally appear.
    values.append(
        slug.replace(
            "-football",
            ""
        )
    )

    output = []

    seen = set()

    for value in values:

        value = value.strip("-")

        if value and value not in seen:

            seen.add(value)

            output.append(value)

    return output


def logo_slugs(
    league,
    team
):

    values = []

    # Explicit mappings first.
    override = LOGOCDN_SLUG_OVERRIDES.get(
        (
            league,
            team
        ),
        []
    )

    values.extend(
        override
    )

    values.extend(
        generic_slugs(team)
    )

    output = []

    seen = set()

    for value in values:

        value = value.strip()

        if not value:

            continue

        if value in seen:

            continue

        seen.add(
            value
        )

        output.append(
            value
        )

    return output


# ============================================================
# LOGOCDN URL DISCOVERY
#
# Current logos can exist under different years.
#
# Try current first, then older versions.
# ============================================================

def logocdn_urls(
    league,
    team
):

    slugs = logo_slugs(
        league,
        team
    )

    # Current first.
    years = [
        "2026",
        "2025",
        "2024",
        "2023",
        "2022",
        "2021",
        "2020",
        "2019",
        "2018",
        "2017",
        "2016",
        "2015",
        "2014",
        "2013",
        "2012",
        "2011",
        "2010",
    ]

    urls = []

    for slug in slugs:

        for year in years:

            urls.append(
                (
                    f"https://i.logocdn.com/"
                    f"{league.lower()}/"
                    f"{year}/"
                    f"{slug}.svg"
                )
            )

            urls.append(
                (
                    f"https://i.logocdn.com/"
                    f"{league.lower()}/"
                    f"{year}/"
                    f"{slug}.png"
                )
            )

    return urls


# ============================================================
# DOWNLOAD FROM LOGOCDN
# ============================================================

def download_logocdn_logo(
    league,
    team
):

    urls = logocdn_urls(
        league,
        team
    )

    errors = []

    for url in urls:

        try:

            response = session.get(
                url,
                timeout=REQUEST_TIMEOUT,
                allow_redirects=True,
            )

            if response.status_code != 200:

                errors.append(
                    f"{response.status_code}: {url}"
                )

                continue

            if not response.content:

                continue

            content_type = (
                response.headers.get(
                    "Content-Type",
                    ""
                ).lower()
            )

            # ------------------------------------------------
            # SVG
            # ------------------------------------------------

            is_svg = (
                ".svg" in url.lower()
                or "svg" in content_type
                or response.content.lstrip().startswith(
                    b"<svg"
                )
                or response.content.lstrip().startswith(
                    b"<?xml"
                )
            )

            if is_svg:

                if cairosvg is None:

                    raise RuntimeError(
                        "CairoSVG is required to "
                        "convert SVG logos."
                    )

                png_bytes = cairosvg.svg2png(
                    bytestring=response.content
                )

                image = Image.open(
                    io.BytesIO(
                        png_bytes
                    )
                )

            else:

                image = Image.open(
                    io.BytesIO(
                        response.content
                    )
                )

            image.load()

            image = image.convert(
                "RGBA"
            )

            # Verify it is a real image.
            if (
                image.width <= 0
                or image.height <= 0
            ):

                continue

            print(
                f"  Source: {url}"
            )

            return image

        except Exception as exc:

            errors.append(
                f"{url}: {exc}"
            )

            continue

        finally:

            time.sleep(
                REQUEST_DELAY
            )

    raise RuntimeError(
        f"Could not download logo for "
        f"{league}: {team}"
    )


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


def teams_from_file(path):

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
# DOWNLOAD ALL 124 CURRENT LOGOS
# ============================================================

def download_all_logos(
    teams_by_league
):

    print()
    print("=" * 70)
    print("DOWNLOADING CURRENT BIG-4 LOGOS")
    print("=" * 70)

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

            print(
                f"[{league} "
                f"{number}/{len(teams)}] "
                f"{team}"
            )

            try:

                image = download_logocdn_logo(
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

                # Verify file immediately.
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
        f"Logos downloaded: "
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
# REBUILD EXISTING LIBRARY
#
# IMPORTANT:
# Existing filenames and directories are NEVER changed.
# ============================================================

def rebuild_library(
    downloaded
):

    total = 0
    replaced = 0
    failed = []

    for league, path in discover_files():

        total += 1

        teams = teams_from_file(
            path
        )

        print()
        print(
            f"[{league}]"
        )

        print(
            f"  {path}"
        )

        try:

            if len(teams) == 1:

                team = teams[0]

                source = downloaded[
                    league
                ][
                    clean_name(team)
                ]

                print(
                    f"  TEAM: {team}"
                )

                rebuild_solo(
                    path,
                    source
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

                print(
                    f"  HOME: {home_team}"
                )

                print(
                    f"  AWAY: {away_team}"
                )

                rebuild_matchup(
                    path,
                    home_source,
                    away_source
                )

            replaced += 1

        except Exception as exc:

            failed.append(
                (
                    path,
                    str(exc)
                )
            )

            print(
                f"  ERROR: {exc}"
            )

    return (
        total,
        replaced,
        failed
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

            count += 1

        except Exception as exc:

            raise RuntimeError(
                f"Invalid rebuilt image "
                f"{path}: {exc}"
            )

    print(
        f"Verified {count} existing logo files."
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
    # DOWNLOAD EVERYTHING FIRST.
    #
    # sports-logos is untouched during this entire phase.
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
    # EVERYTHING EXISTS.
    # NOW rebuild the actual library.
    # --------------------------------------------------------

    print()
    print("=" * 70)
    print("REBUILDING EXISTING SPORTS LOGO LIBRARY")
    print("=" * 70)

    total, replaced, failed = rebuild_library(
        downloaded
    )

    if failed:

        print()
        print("=" * 70)
        print("REBUILD FAILED")
        print("=" * 70)

        for path, error in failed:

            print()
            print(
                f"File: {path}"
            )

            print(
                f"Error: {error}"
            )

        print()
        print(
            "Some existing logo files could not "
            "be rebuilt."
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

        sys.exit(1)

    print()
    print("=" * 70)
    print("FINISHED")
    print("=" * 70)

    print()
    print(
        f"Files found:    {total}"
    )

    print(
        f"Files replaced: {replaced}"
    )

    print(
        f"Files failed:   0"
    )

    print()

    print(
        "Existing filenames and directory "
        "paths were preserved."
    )

    print(
        f"Temporary source logos remain in: "
        f"{TEMP_ROOT}"
    )


if __name__ == "__main__":

    main()
