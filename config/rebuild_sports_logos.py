import io
import os
import re
import sys
import time
import requests

from PIL import Image, ImageOps

# ============================================================
# SPORTS LOGO REPLACEMENT SCRIPT
#
# PURPOSE:
#   Replace the existing sports logo artwork while preserving
#   every existing filename and directory path.
#
# SUPPORTED:
#   MLB
#   NBA
#   NFL
#   NHL
#
# EXISTING FILE EXAMPLES:
#
#   Tennessee_Titans.png
#   Tennessee_Titans_vs_Arizona_Cardinals.png
#   Arizona_Cardinals_vs_Tennessee_Titans.png
#
# NOTHING IS RENAMED.
# NOTHING IS MOVED.
# ============================================================


ROOT = "sports-logos"

LEAGUES = {
    "MLB",
    "NBA",
    "NFL",
    "NHL",
}

TIMEOUT = 30

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/151.0 Safari/537.36"
    )
}


# ============================================================
# VERIFIED / MANUAL SOURCE OVERRIDES
#
# Put the exact CDNLogo image URL for a team here.
#
# These are the sources we have explicitly selected so far.
# Additional teams can be added as verified URLs are collected.
# ============================================================

TEAM_SOURCES = {
    "Tennessee_Titans":
        "https://static.cdnlogo.com/logos/t/73/tennessee-titans.png",

    # Add verified sources here:
    #
    # "Los_Angeles_Rams":
    #     "https://static.cdnlogo.com/logos/...",
}


# ============================================================
# TEAM NAME NORMALIZATION
#
# Existing filenames are converted to a canonical lookup name.
# This allows names such as:
#
#   Los_Angeles_Rams
#   New_York_Yankees
#   Tampa_Bay_Buccaneers
#
# to be handled consistently.
# ============================================================

ALIASES = {
    # NFL
    "Washington_Redskins": "Washington_Commanders",
    "Washington_Football_Team": "Washington_Commanders",

    # MLB
    "Cleveland_Indians": "Cleveland_Guardians",

    # NBA
    "New_Jersey_Nets": "Brooklyn_Nets",
    "Charlotte_Bobcats": "Charlotte_Hornets",

    # NHL
    "Phoenix_Coyotes": "Arizona_Coyotes",
    "Atlanta_Thrashers": "Winnipeg_Jets",
}


# ============================================================
# REQUEST SESSION
# ============================================================

session = requests.Session()
session.headers.update(HEADERS)


# ============================================================
# DOWNLOAD
# ============================================================

def download_image(url):
    print(f"    Downloading:")
    print(f"    {url}")

    response = session.get(
        url,
        timeout=TIMEOUT
    )

    response.raise_for_status()

    image = Image.open(
        io.BytesIO(response.content)
    )

    image.load()

    return image.convert("RGBA")


# ============================================================
# TEAM NAME HELPERS
# ============================================================

def canonical_team(team):
    return ALIASES.get(team, team)


def filename_to_teams(filename):
    """
    Converts:

        Tennessee_Titans.png

    into:

        ["Tennessee_Titans"]

    and:

        Tennessee_Titans_vs_Arizona_Cardinals.png

    into:

        [
            "Tennessee_Titans",
            "Arizona_Cardinals"
        ]
    """

    name = os.path.splitext(filename)[0]

    if "_vs_" in name:
        first, second = name.split(
            "_vs_",
            1
        )

        return [
            canonical_team(first),
            canonical_team(second)
        ]

    return [
        canonical_team(name)
    ]


# ============================================================
# SOURCE CACHE
# ============================================================

SOURCE_CACHE = {}


def get_team_logo(team):
    """
    Download a source logo once and reuse it for all matchup
    files involving that team.
    """

    team = canonical_team(team)

    if team in SOURCE_CACHE:
        return SOURCE_CACHE[team].copy()

    url = TEAM_SOURCES.get(team)

    if not url:
        raise RuntimeError(
            f"No verified logo source configured for: {team}\n"
            f"Add {team!r} to TEAM_SOURCES."
        )

    image = download_image(url)

    SOURCE_CACHE[team] = image

    return image.copy()


# ============================================================
# TRANSPARENT CANVAS HELPERS
# ============================================================

def trim_transparency(image):
    """
    Remove transparent borders around the downloaded source
    logo so the actual logo can be scaled correctly.
    """

    image = image.convert("RGBA")

    alpha = image.getchannel("A")

    bbox = alpha.getbbox()

    if bbox:
        image = image.crop(bbox)

    return image


def fit_logo(image, max_width, max_height):
    """
    Scale a logo proportionally into the requested area.
    """

    image = trim_transparency(image)

    if image.width == 0 or image.height == 0:
        return image

    ratio = min(
        max_width / image.width,
        max_height / image.height
    )

    width = max(
        1,
        int(image.width * ratio)
    )

    height = max(
        1,
        int(image.height * ratio)
    )

    return image.resize(
        (width, height),
        Image.Resampling.LANCZOS
    )


# ============================================================
# SOLO LOGO
# ============================================================

def rebuild_solo(existing_path, team):
    """
    Replace the existing solo logo while preserving:
      - filename
      - directory
      - canvas dimensions
    """

    existing = Image.open(
        existing_path
    ).convert("RGBA")

    width = existing.width
    height = existing.height

    source = get_team_logo(team)

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

    x = (width - logo.width) // 2
    y = (height - logo.height) // 2

    canvas.alpha_composite(
        logo,
        (x, y)
    )

    canvas.save(
        existing_path,
        "PNG",
        optimize=True
    )


# ============================================================
# MATCHUP LOGO
# ============================================================

def rebuild_matchup(existing_path, home_team, away_team):
    """
    Rebuild an existing directional matchup logo.

    The filename determines the direction:

        Home_vs_Away.png

    Therefore:

        Tennessee_Titans_vs_Arizona_Cardinals.png

    always places Tennessee first and Arizona second.

    The existing PNG dimensions are retained.
    """

    existing = Image.open(
        existing_path
    ).convert("RGBA")

    width = existing.width
    height = existing.height

    home_logo = get_team_logo(home_team)
    away_logo = get_team_logo(away_team)

    # Preserve the existing canvas size.
    #
    # The two logos are placed side-by-side with transparent
    # background. The filename remains untouched.
    #
    # This gives:
    #
    # HOME  |  AWAY
    #
    # and the reverse matchup naturally becomes:
    #
    # AWAY  |  HOME
    #

    half_width = width // 2

    home = fit_logo(
        home_logo,
        int(half_width * 0.88),
        int(height * 0.88)
    )

    away = fit_logo(
        away_logo,
        int(half_width * 0.88),
        int(height * 0.88)
    )

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
        half_width +
        ((half_width - away.width) // 2)
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
        existing_path,
        "PNG",
        optimize=True
    )


# ============================================================
# FILE DISCOVERY
# ============================================================

def logo_files():
    for league in sorted(LEAGUES):

        league_path = os.path.join(
            ROOT,
            league
        )

        if not os.path.isdir(league_path):
            continue

        for directory, _, files in os.walk(
            league_path
        ):

            for filename in sorted(files):

                if not filename.lower().endswith(
                    ".png"
                ):
                    continue

                yield (
                    league,
                    directory,
                    filename
                )


# ============================================================
# MAIN
# ============================================================

def main():

    print()
    print("=" * 60)
    print("SPORTS LOGO REPLACEMENT")
    print("=" * 60)
    print()

    total = 0
    replaced = 0
    skipped = 0
    failed = 0

    for league, directory, filename in logo_files():

        total += 1

        path = os.path.join(
            directory,
            filename
        )

        teams = filename_to_teams(
            filename
        )

        try:

            if len(teams) == 1:

                team = teams[0]

                print(
                    f"[{league}] SOLO: "
                    f"{filename}"
                )

                rebuild_solo(
                    path,
                    team
                )

                replaced += 1

            elif len(teams) == 2:

                home_team = teams[0]
                away_team = teams[1]

                print(
                    f"[{league}] MATCHUP: "
                    f"{filename}"
                )

                print(
                    f"    HOME: {home_team}"
                )

                print(
                    f"    AWAY: {away_team}"
                )

                rebuild_matchup(
                    path,
                    home_team,
                    away_team
                )

                replaced += 1

            else:

                print(
                    f"SKIPPED: {path}"
                )

                skipped += 1

        except Exception as exc:

            failed += 1

            print()
            print(
                f"ERROR: {path}"
            )
            print(
                f"       {exc}"
            )
            print()

    print()
    print("=" * 60)
    print("COMPLETE")
    print("=" * 60)
    print()
    print(f"Files found:     {total}")
    print(f"Files replaced:  {replaced}")
    print(f"Files skipped:   {skipped}")
    print(f"Files failed:    {failed}")
    print()
    print("Existing filenames and paths were not changed.")
    print()

    if failed:
        sys.exit(1)


if __name__ == "__main__":
    main()
