import os
import re
import shutil
import unicodedata

from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from collections import deque

from PIL import Image


# ============================================================
# CONFIG
# ============================================================

# ============================================================
# SPORTS-LOGOS IS BOTH:
#
#   1. THE CURRENT SOURCE
#   2. THE FINAL DESTINATION
#
# The existing sports-logos library is read first.
# A completely separate temporary build is then created.
# Only after the entire build passes verification is the
# existing sports-logos directory replaced.
#
# NO temp/New folder is used.
# NO external downloads are performed.
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

# Number of team folders processed simultaneously.
BUILD_WORKERS = 8


# ============================================================
# SOLO LOGO SETTINGS
# ============================================================

# Final solo logo canvas.
SOLO_SIZE = (1024, 1024)

# Percentage of the canvas the actual logo artwork is allowed
# to occupy.
#
# Increasing this makes logos appear larger in TiviMate.
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

# Pixels at or above this value are considered white enough
# to potentially be background.
WHITE_THRESHOLD = 245

# Alpha values at or below this are treated as transparent.
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
# SOURCE DISCOVERY
#
# sports-logos is the source.
#
# IMPORTANT:
#
# We ONLY use the individual team logo from each team folder.
#
# Example:
#
# sports-logos/
#   MLB/
#     Boston_Red_Sox/
#       Boston_Red_Sox.png
#       Boston_Red_Sox_vs_Tampa_Bay_Rays.png
#
# The ONLY source is:
#
#   Boston_Red_Sox/Boston_Red_Sox.png
#
# Existing matchup files are NEVER used as sources.
# ============================================================

def find_solo_source(team_folder):

    team_key = clean_name(
        team_folder.name
    )

    candidates = []

    for path in team_folder.iterdir():

        if not path.is_file():
            continue

        if path.suffix.lower() != ".png":
            continue

        if clean_name(path.stem) == team_key:
            candidates.append(path)

    if len(candidates) == 0:

        raise RuntimeError(
            f"Missing solo team logo in "
            f"{team_folder}"
        )

    if len(candidates) > 1:

        raise RuntimeError(
            f"Multiple solo team logos found in "
            f"{team_folder}: "
            f"{candidates}"
        )

    return candidates[0]


def discover_source_teams():

    teams_by_league = {
        league: {}
        for league in LEAGUES
    }

    if not ROOT.is_dir():

        raise RuntimeError(
            f"Sports logo source directory does not exist: "
            f"{ROOT}"
        )

    for league in sorted(LEAGUES):

        league_root = ROOT / league

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

            source_logo = find_solo_source(
                team_folder
            )

            key = clean_name(
                team_name
            )

            if not key:

                raise RuntimeError(
                    f"Invalid team folder name: "
                    f"{team_folder}"
                )

            if key in teams_by_league[league]:

                raise RuntimeError(
                    f"Duplicate team detected in "
                    f"{league}: {team_folder.name}"
                )

            teams_by_league[league][key] = {
                "name": team_name,
                "folder": team_folder,
                "source": source_logo,
            }

    return teams_by_league


# ============================================================
# VERIFY SOURCE LIBRARY
# ============================================================

def verify_source_library(
    teams_by_league
):

    print()
    print("=" * 70)
    print("VERIFYING SPORTS-LOGOS SOURCE")
    print("=" * 70)

    print()
    print(
        f"Source: {ROOT}"
    )

    print()
    print(
        "The existing sports-logos library will be "
        "read-only until the new build is verified."
    )

    total_teams = 0

    for league in sorted(LEAGUES):

        teams = teams_by_league[league]

        print()
        print(
            f"{league}: {len(teams)} teams"
        )

        if not teams:

            raise RuntimeError(
                f"{league} contains no teams."
            )

        for team in sorted(
            teams.values(),
            key=lambda item: clean_name(
                item["name"]
            )
        ):

            source = team["source"]

            if not source.is_file():

                raise RuntimeError(
                    f"Missing source logo: "
                    f"{source}"
                )

            try:

                with Image.open(source) as image:

                    image.load()

                    if (
                        image.width <= 0
                        or image.height <= 0
                    ):

                        raise RuntimeError(
                            "Invalid image dimensions."
                        )

            except Exception as exc:

                raise RuntimeError(
                    f"Invalid source logo "
                    f"{source}: {exc}"
                )

        total_teams += len(teams)

    print()
    print(
        f"Total source teams: {total_teams}"
    )

    if total_teams == 0:

        raise RuntimeError(
            "No source teams were discovered."
        )

    return total_teams


# ============================================================
# LOAD SOURCE IMAGE
# ============================================================

def load_source_logo(
    source_path
):

    with Image.open(source_path) as image:

        image = image.convert("RGBA")

        image.load()

        return image.copy()


# ============================================================
# REMOVE WHITE BACKGROUND
#
# IMPORTANT:
#
# We do NOT simply delete every white pixel.
#
# White pixels that are enclosed inside the logo are preserved.
#
# We only remove near-white pixels that are connected to the
# outside edges of the image.
#
# This means white lettering, white outlines, white baseball
# details, etc. can remain intact.
# ============================================================

def remove_edge_white_background(
    image
):

    image = image.convert("RGBA")

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

    def pixel_is_background(x, y):

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

    def add_if_background(x, y):

        index = (
            y * width
            +
            x
        )

        if visited[index]:

            return

        if not pixel_is_background(x, y):

            return

        visited[index] = 1

        queue.append(
            (x, y)
        )

    # --------------------------------------------------------
    # Seed the flood fill from every image edge.
    # --------------------------------------------------------

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

    # --------------------------------------------------------
    # Flood-fill all connected white background.
    # --------------------------------------------------------

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

    # --------------------------------------------------------
    # Convert detected background to transparent.
    # --------------------------------------------------------

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

    image = image.convert("RGBA")

    alpha = image.getchannel("A")

    bbox = alpha.getbbox()

    if bbox:

        image = image.crop(
            bbox
        )

    return image


# ============================================================
# CLEAN SOURCE LOGO
#
# Pipeline:
#
#   source PNG
#       ↓
#   RGBA
#       ↓
#   remove edge-connected white background
#       ↓
#   trim transparent space
#       ↓
#   return clean artwork
# ============================================================

def clean_source_logo(
    source_path
):

    image = load_source_logo(
        source_path
    )

    image = remove_edge_white_background(
        image
    )

    image = trim_transparency(
        image
    )

    if (
        image.width <= 0
        or image.height <= 0
    ):

        raise RuntimeError(
            f"Logo became empty after cleanup: "
            f"{source_path}"
        )

    return image


# ============================================================
# FIT LOGO TO MAXIMUM AREA
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
# BUILD FINAL SOLO LOGO
#
# Output:
#
#   1024 x 1024
#   RGBA
#   transparent
#
# Artwork fills approximately 90% of the canvas.
# ============================================================

def build_solo_logo(
    source_path,
    destination
):

    image = clean_source_logo(
        source_path
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
# HOME TEAM ALWAYS LEFT.
# AWAY TEAM ALWAYS RIGHT.
#
# IMPORTANT:
#
# Matchups are built from CLEANED SOLO LOGOS.
#
# They are NOT built from existing matchup files.
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
#
# Every team receives:
#
#   Team.png
#
# PLUS:
#
#   Team_vs_Opponent.png
#
# for every other team in that league.
# ============================================================

def build_team_folder(
    league,
    home_team,
    all_teams,
    destination_league
):

    home_name = home_team["name"]

    home_source = home_team["source"]

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
    # CLEAN HOME SOLO LOGO ONCE.
    # --------------------------------------------------------

    home_clean_logo = clean_source_logo(
        home_source
    )

    # --------------------------------------------------------
    # CREATE FINAL SOLO LOGO.
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
    # BUILD EVERY MATCHUP.
    #
    # Clean each opponent's source independently.
    # Existing matchup files are never touched as sources.
    # --------------------------------------------------------

    for away_team in all_teams:

        away_name = away_team["name"]

        if (
            clean_name(away_name)
            ==
            clean_name(home_name)
        ):
            continue

        away_source = away_team["source"]

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
# BUILD SOLO FROM ALREADY CLEANED IMAGE
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
# BUILD ENTIRE LEAGUE
# ============================================================

def build_league(
    league,
    teams,
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
        f"Expected files in {league}: "
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
                    destination_league
                )
            )

        completed = 0

        for future in as_completed(jobs):

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
    # VERIFY FILE COUNT.
    # --------------------------------------------------------

    actual_files = list(
        destination_league.rglob("*.png")
    )

    if len(actual_files) != expected_files:

        raise RuntimeError(
            f"{league}: generated "
            f"{len(actual_files)} PNG files, "
            f"expected {expected_files}"
        )

    # --------------------------------------------------------
    # VERIFY EVERY TEAM FOLDER.
    # --------------------------------------------------------

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
            team_folder.glob("*.png")
        )

        if len(files) != expected_per_team:

            raise RuntimeError(
                f"{league} / {team_name}: "
                f"folder contains {len(files)} "
                f"files, expected "
                f"{expected_per_team}"
            )

        solo = (
            team_folder
            /
            f"{filesystem_name(team_name)}.png"
        )

        if not solo.is_file():

            raise RuntimeError(
                f"Missing solo logo: {solo}"
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
# VERIFY COMPLETE GENERATED LIBRARY
# ============================================================

def verify_generated_library(
    build_root,
    teams_by_league
):

    print()
    print("=" * 70)
    print("VERIFYING COMPLETE CLEANED LIBRARY")
    print("=" * 70)

    total_expected = 0
    total_found = 0

    for league in sorted(LEAGUES):

        teams = teams_by_league[league]

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
            league_root.rglob("*.png")
        )

        print()
        print(
            f"{league}: "
            f"{len(files)}/{expected}"
        )

        if len(files) != expected:

            raise RuntimeError(
                f"{league}: expected "
                f"{expected} PNG files but found "
                f"{len(files)}"
            )

        for path in files:

            try:

                with Image.open(path) as image:

                    image.verify()

                with Image.open(path) as image:

                    if image.mode != "RGBA":

                        raise RuntimeError(
                            f"Image is not RGBA: "
                            f"{path}"
                        )

                    if (
                        image.width != 1024
                        and
                        path.name.lower().endswith(
                            ".png"
                        )
                    ):
                        # Matchup files intentionally have
                        # 1024x512 dimensions.
                        pass

            except Exception as exc:

                raise RuntimeError(
                    f"Invalid generated image "
                    f"{path}: {exc}"
                )

        total_expected += expected
        total_found += len(files)

    print()
    print(
        f"TOTAL: {total_found}/{total_expected} "
        f"PNG files verified."
    )

    if total_found != total_expected:

        raise RuntimeError(
            "Final generated file count does "
            "not match expected count."
        )


# ============================================================
# VERIFY TRANSPARENCY
#
# Confirms the output actually contains transparent pixels.
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

    for league in sorted(LEAGUES):

        league_root = (
            build_root
            /
            league
        )

        for path in league_root.rglob(
            "*.png"
        ):

            with Image.open(path) as image:

                image = image.convert("RGBA")

                alpha = image.getchannel(
                    "A"
                )

                extrema = alpha.getextrema()

                if extrema is None:

                    raise RuntimeError(
                        f"Could not inspect alpha: "
                        f"{path}"
                    )

                minimum, maximum = extrema

                if minimum != 0:

                    raise RuntimeError(
                        f"No transparent pixels found "
                        f"in generated logo: {path}"
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

    for league in sorted(LEAGUES):

        teams = teams_by_league[league]

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

                with Image.open(path) as image:

                    if (
                        "_vs_" in path.stem
                    ):

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
                            f"expected {expected}"
                        )

    print()
    print(
        f"Solo logos verified: {solo_count}"
    )

    print(
        f"Matchup logos verified: {matchup_count}"
    )


# ============================================================
# INSTALL NEW LIBRARY
#
# Existing sports-logos is NOT removed until the entire build
# has passed all verification.
# ============================================================

def install_new_library():

    if BACKUP_ROOT.exists():

        shutil.rmtree(
            BACKUP_ROOT
        )

    print()
    print("=" * 70)
    print("INSTALLING CLEANED SPORTS LOGO LIBRARY")
    print("=" * 70)

    print()
    print(
        f"SOURCE: {ROOT}"
    )

    print(
        f"NEW BUILD: {BUILD_ROOT}"
    )

    # --------------------------------------------------------
    # Move current source out of the way.
    # --------------------------------------------------------

    if ROOT.exists():

        print()
        print(
            "Moving existing sports-logos to temporary backup."
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
        # Roll back if installation fails.
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
    # Delete backup only after successful installation.
    # --------------------------------------------------------

    if BACKUP_ROOT.exists():

        shutil.rmtree(
            BACKUP_ROOT
        )

    print()
    print(
        "Cleaned sports-logos library installed successfully."
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

        teams = teams_by_league[league]

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
            league_root.rglob("*.png")
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
                filesystem_name(team_name)
            )

            if not team_folder.is_dir():

                raise RuntimeError(
                    f"Missing installed team folder: "
                    f"{team_folder}"
                )

            solo = (
                team_folder
                /
                f"{filesystem_name(team_name)}.png"
            )

            if not solo.is_file():

                raise RuntimeError(
                    f"Missing installed solo logo: "
                    f"{solo}"
                )

            for opponent in teams.values():

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
                        f"Missing installed matchup: "
                        f"{matchup}"
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
# MAIN
# ============================================================

def main():

    print("=" * 70)
    print("SPORTS LOGO CLEANUP AND MATCHUP REBUILDER")
    print("=" * 70)

    print()
    print("SOURCE AND DESTINATION:")
    print(
        "  sports-logos/<LEAGUE>/<TEAM>/<TEAM>.png"
    )

    print()
    print("PROCESS:")
    print(
        "  Existing solo PNGs are cleaned."
    )

    print(
        "  White backgrounds connected to the image edge "
        "are made transparent."
    )

    print(
        "  Legitimate enclosed white portions of logos "
        "are preserved."
    )

    print(
        "  Artwork is tightly cropped."
    )

    print(
        "  Solo logos are rendered at 1024x1024."
    )

    print(
        "  Artwork fills approximately 90% of the canvas."
    )

    print(
        "  Matchups are rendered at 1024x512."
    )

    print(
        "  Every matchup is rebuilt from cleaned solo logos."
    )

    print()
    print("SAFETY:")
    print(
        "  The original sports-logos directory is NOT "
        "modified during the build."
    )

    print(
        "  A separate temporary build is created first."
    )

    print(
        "  The current library is replaced ONLY after "
        "complete verification."
    )

    print(
        "  No external downloads are performed."
    )

    print()
    print(
        f"Build workers: {BUILD_WORKERS}"
    )

    print(
        f"Solo size: {SOLO_SIZE[0]}x{SOLO_SIZE[1]}"
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
    # Clean up an incomplete previous build.
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
    # Discover current source library.
    # --------------------------------------------------------

    teams_by_league = (
        discover_source_teams()
    )

    total_teams = (
        verify_source_library(
            teams_by_league
        )
    )

    # --------------------------------------------------------
    # Calculate expected output.
    # --------------------------------------------------------

    print()
    print("=" * 70)
    print("EXPECTED CLEANED LIBRARY")
    print("=" * 70)

    total_expected = 0

    for league in sorted(LEAGUES):

        team_count = len(
            teams_by_league[league]
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
        f"TOTAL TEAMS: {total_teams}"
    )

    print(
        f"TOTAL PNG FILES: {total_expected}"
    )

    # --------------------------------------------------------
    # Build everything from the CURRENT sports-logos source.
    # --------------------------------------------------------

    generated_total = 0

    for league in sorted(LEAGUES):

        generated_total += build_league(
            league,
            teams_by_league[league],
            BUILD_ROOT
        )

    # --------------------------------------------------------
    # Verify complete build.
    # --------------------------------------------------------

    verify_generated_library(
        BUILD_ROOT,
        teams_by_league
    )

    verify_transparency(
        BUILD_ROOT,
        teams_by_league
    )

    verify_dimensions(
        BUILD_ROOT,
        teams_by_league
    )

    # --------------------------------------------------------
    # Install only after everything passes.
    # --------------------------------------------------------

    install_new_library()

    # --------------------------------------------------------
    # Verify installed library.
    # --------------------------------------------------------

    verify_installed_library(
        teams_by_league
    )

    # --------------------------------------------------------
    # Final report.
    # --------------------------------------------------------

    print()
    print("=" * 70)
    print("FINISHED")
    print("=" * 70)

    print()
    print(
        f"SOURCE USED: {ROOT}"
    )

    print(
        f"Source teams: {total_teams}"
    )

    print(
        f"PNG files generated: {generated_total}"
    )

    print(
        f"PNG files expected:  {total_expected}"
    )

    print()
    print(
        "The existing sports-logos solo PNGs were used "
        "as the source."
    )

    print(
        "White edge-connected backgrounds were removed."
    )

    print(
        "Legitimate enclosed white logo details were preserved."
    )

    print(
        "Solo logos were cropped and enlarged to "
        "1024x1024 transparent PNGs."
    )

    print(
        "Matchup logos were rebuilt from the cleaned "
        "solo logos at 1024x512."
    )

    print(
        "Existing matchup files were never used as sources."
    )

    print(
        "The rebuilt sports-logos library was installed "
        "only after verification succeeded."
    )

    print(
        "No external downloads were performed."
    )


if __name__ == "__main__":
    main()
