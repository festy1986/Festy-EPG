import io
import os
import re
import sys
import shutil
import unicodedata

from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

from PIL import Image


# ============================================================
# CONFIG
# ============================================================

ROOT = Path("sports-logos")

# THIS IS NOW THE SOURCE OF TRUTH.
#
# The repository contains:
#
#   _temp_espn_logos/
#       MLB/
#           Arizona Diamondbacks.png
#           ...
#       NBA/
#           Atlanta Hawks.png
#           ...
#       NFL/
#           Arizona Cardinals.png
#           ...
#       NHL/
#           Anaheim Ducks.png
#           ...
#
SOURCE_ROOT = Path("_temp_espn_logos")

# Build into a completely separate directory first.
BUILD_ROOT = Path("_sports_logos_build")

LEAGUES = {
    "MLB",
    "NBA",
    "NFL",
    "NHL",
}

# Number of files generated simultaneously.
BUILD_WORKERS = 8

# ESPN source logos are square.
SOLO_SIZE = (512, 512)

# Matchup logos are side-by-side.
MATCHUP_SIZE = (1024, 512)

# Logo scale inside the canvas.
SOLO_SCALE = 0.90

MATCHUP_LOGO_WIDTH_SCALE = 0.88
MATCHUP_LOGO_HEIGHT_SCALE = 0.88


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


def output_team_name(
    team
):

    team = os.path.splitext(
        team
    )[0]

    team = team.replace(
        "_",
        " "
    )

    team = re.sub(
        r"\s+",
        " ",
        team
    ).strip()

    return team


def filesystem_name(
    team
):

    team = output_team_name(
        team
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
# SOURCE DISCOVERY
#
# IMPORTANT:
#
# The source directory itself defines the complete team list.
#
# We do NOT inspect sports-logos to determine which teams or
# matchups exist.
# ============================================================

def discover_source_teams():

    teams_by_league = {
        league: {}
        for league in LEAGUES
    }

    if not SOURCE_ROOT.is_dir():

        raise RuntimeError(
            f"Source directory does not exist: "
            f"{SOURCE_ROOT}"
        )

    for league in sorted(
        LEAGUES
    ):

        league_source = (
            SOURCE_ROOT
            /
            league
        )

        if not league_source.is_dir():

            raise RuntimeError(
                f"Missing source league directory: "
                f"{league_source}"
            )

        source_files = sorted(
            league_source.glob(
                "*.png"
            )
        )

        if not source_files:

            raise RuntimeError(
                f"No PNG source logos found in: "
                f"{league_source}"
            )

        for source_path in source_files:

            team = output_team_name(
                source_path.stem
            )

            key = clean_name(
                team
            )

            if not key:

                raise RuntimeError(
                    f"Invalid team filename: "
                    f"{source_path}"
                )

            if key in teams_by_league[league]:

                previous = teams_by_league[
                    league
                ][key]

                raise RuntimeError(
                    f"Duplicate team detected in "
                    f"{league}: "
                    f"{previous.name} and "
                    f"{source_path.name}"
                )

            teams_by_league[
                league
            ][key] = {
                "name": team,
                "source": source_path,
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
    print("VERIFYING ESPN SOURCE LIBRARY")
    print("=" * 70)

    total_teams = 0

    for league in sorted(
        LEAGUES
    ):

        teams = teams_by_league[
            league
        ]

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

            source = team[
                "source"
            ]

            if not source.is_file():

                raise RuntimeError(
                    f"Missing source logo: "
                    f"{source}"
                )

            try:

                with Image.open(
                    source
                ) as image:

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

        total_teams += len(
            teams
        )

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


def load_source_logo(
    source_path
):

    with Image.open(
        source_path
    ) as image:

        image = image.convert(
            "RGBA"
        )

        image.load()

        return image.copy()


# ============================================================
# BUILD SOLO LOGO
# ============================================================

def build_solo(
    source_path,
    destination
):

    source = load_source_logo(
        source_path
    )

    logo = fit_logo(
        source,
        int(
            SOLO_SIZE[0]
            *
            SOLO_SCALE
        ),
        int(
            SOLO_SIZE[1]
            *
            SOLO_SCALE
        )
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
# BUILD MATCHUP LOGO
#
# HOME TEAM IS ALWAYS ON THE LEFT.
# AWAY TEAM IS ALWAYS ON THE RIGHT.
#
# Therefore:
#
#   Arizona_Diamondbacks_vs_Athletics.png
#
# and:
#
#   Athletics_vs_Arizona_Diamondbacks.png
#
# are two separate files.
# ============================================================

def build_matchup(
    home_source,
    away_source,
    destination
):

    home_image = load_source_logo(
        home_source
    )

    away_image = load_source_logo(
        away_source
    )

    half_width = (
        MATCHUP_SIZE[0]
        //
        2
    )

    home = fit_logo(
        home_image,
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
        away_image,
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
# Every team folder receives:
#
#   Team.png
#
# PLUS:
#
#   Team_vs_Opponent1.png
#   Team_vs_Opponent2.png
#   ...
#
# Every other team in the SAME league is included.
# ============================================================

def build_team_folder(
    league,
    home_team,
    all_teams,
    destination_league
):

    home_name = home_team[
        "name"
    ]

    home_source = home_team[
        "source"
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
    # SOLO LOGO
    # --------------------------------------------------------

    solo_path = (
        home_folder
        /
        f"{filesystem_name(home_name)}.png"
    )

    build_solo(
        home_source,
        solo_path
    )

    generated = 1

    # --------------------------------------------------------
    # EVERY POSSIBLE OPPONENT
    #
    # Do NOT skip based on schedule.
    # Do NOT skip based on existing files.
    # Do NOT skip divisions/conferences.
    #
    # Every team in the league is included except itself.
    # --------------------------------------------------------

    for away_team in all_teams:

        away_name = away_team[
            "name"
        ]

        if clean_name(
            away_name
        ) == clean_name(
            home_name
        ):

            continue

        away_source = away_team[
            "source"
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
            home_source,
            away_source,
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
    # VERIFY LEAGUE COUNT
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
    # VERIFY EVERY TEAM FOLDER
    # --------------------------------------------------------

    for team in sorted_teams:

        team_name = team[
            "name"
        ]

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
                f"Missing solo logo: "
                f"{solo}"
            )

        # Every other team must have a matchup file.
        for opponent in sorted_teams:

            opponent_name = opponent[
                "name"
            ]

            if clean_name(
                opponent_name
            ) == clean_name(
                team_name
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
# VERIFY EVERY GENERATED IMAGE
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
                f"{expected} PNG files but found "
                f"{len(files)}"
            )

        for path in files:

            try:

                with Image.open(
                    path
                ) as image:

                    image.verify()

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
# REPLACE OLD LIBRARY
#
# This happens ONLY after the complete build has succeeded.
# ============================================================

def install_new_library():

    backup_root = (
        ROOT.parent
        /
        "_sports_logos_old"
    )

    if backup_root.exists():

        shutil.rmtree(
            backup_root
        )

    if ROOT.exists():

        print()
        print(
            f"Removing old library: {ROOT}"
        )

        ROOT.rename(
            backup_root
        )

    try:

        BUILD_ROOT.rename(
            ROOT
        )

    except Exception:

        if backup_root.exists() and not ROOT.exists():

            backup_root.rename(
                ROOT
            )

        raise

    if backup_root.exists():

        shutil.rmtree(
            backup_root
        )


# ============================================================
# FINAL LIBRARY VERIFICATION
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
                f"expected {expected}"
            )

        for team in teams.values():

            team_name = team[
                "name"
            ]

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

            team_files = list(
                team_folder.glob(
                    "*.png"
                )
            )

            if len(team_files) != expected_per_team:

                raise RuntimeError(
                    f"{team_folder}: "
                    f"{len(team_files)} files, "
                    f"expected {expected_per_team}"
                )

        total_expected += expected
        total_found += len(files)

        print(
            f"{league}: "
            f"{len(files)}/{expected} verified"
        )

    print()
    print(
        f"Installed library verified: "
        f"{total_found}/{total_expected} files."
    )


# ============================================================
# CLEAN FAILED BUILD
# ============================================================

def cleanup_build_directory():

    if BUILD_ROOT.exists():

        shutil.rmtree(
            BUILD_ROOT
        )


# ============================================================
# MAIN
# ============================================================

def main():

    print()
    print("=" * 70)
    print("COMPLETE SPORTS LOGO LIBRARY REBUILDER")
    print("=" * 70)

    print()
    print(
        "SOURCE:"
    )

    print(
        f"  {SOURCE_ROOT}"
    )

    print()
    print(
        "OUTPUT:"
    )

    print(
        f"  {ROOT}"
    )

    print()
    print(
        "The existing sports-logos library is NOT "
        "used to determine teams or matchups."
    )

    print(
        "Every team found in _temp_espn_logos is used."
    )

    print(
        "Every team receives every other team in "
        "its league as a matchup."
    )

    print(
        "Both home/away directions are generated."
    )

    print(
        f"Build workers: {BUILD_WORKERS}"
    )

    # --------------------------------------------------------
    # VERIFY SOURCE FIRST.
    # --------------------------------------------------------

    try:

        teams_by_league = (
            discover_source_teams()
        )

        total_teams = (
            verify_source_library(
                teams_by_league
            )
        )

    except Exception as exc:

        print()
        print("=" * 70)
        print("ABORTED DURING SOURCE VERIFICATION")
        print("=" * 70)

        print()
        print(
            f"Reason: {exc}"
        )

        sys.exit(1)

    # --------------------------------------------------------
    # CALCULATE TOTAL OUTPUT.
    #
    # Each league with N teams produces:
    #
    #   N folders
    #   N files per folder
    #   N * N total PNGs
    #
    # The diagonal entry is the solo logo.
    # Every off-diagonal entry is a matchup.
    # --------------------------------------------------------

    total_expected_files = 0

    print()
    print("=" * 70)
    print("EXPECTED COMPLETE LIBRARY")
    print("=" * 70)

    for league in sorted(
        LEAGUES
    ):

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

        total_expected_files += expected

        print(
            f"{league}: "
            f"{count} teams -> "
            f"{count} folders -> "
            f"{expected} files"
        )

    print()
    print(
        f"TOTAL TEAMS: {total_teams}"
    )

    print(
        f"TOTAL PNG FILES: "
        f"{total_expected_files}"
    )

    # --------------------------------------------------------
    # START FROM A COMPLETELY EMPTY BUILD DIRECTORY.
    # --------------------------------------------------------

    cleanup_build_directory()

    BUILD_ROOT.mkdir(
        parents=True,
        exist_ok=True
    )

    # --------------------------------------------------------
    # BUILD EVERYTHING.
    # --------------------------------------------------------

    total_generated = 0

    try:

        for league in sorted(
            LEAGUES
        ):

            generated = build_league(
                league,
                teams_by_league[
                    league
                ],
                BUILD_ROOT
            )

            total_generated += generated

        # ----------------------------------------------------
        # VERIFY BEFORE TOUCHING sports-logos.
        # ----------------------------------------------------

        verify_generated_library(
            BUILD_ROOT,
            teams_by_league
        )

    except Exception as exc:

        print()
        print("=" * 70)
        print("BUILD FAILED")
        print("=" * 70)

        print()
        print(
            f"Reason: {exc}"
        )

        print()
        print(
            "The existing sports-logos library "
            "was NOT modified."
        )

        print(
            f"Failed build directory: "
            f"{BUILD_ROOT}"
        )

        sys.exit(1)

    # --------------------------------------------------------
    # EVERYTHING IS VERIFIED.
    #
    # NOW replace the old library.
    # --------------------------------------------------------

    print()
    print("=" * 70)
    print("INSTALLING COMPLETE REBUILT LIBRARY")
    print("=" * 70)

    try:

        install_new_library()

    except Exception as exc:

        print()
        print("=" * 70)
        print("INSTALLATION FAILED")
        print("=" * 70)

        print()
        print(
            f"Reason: {exc}"
        )

        if BUILD_ROOT.exists():

            print()
            print(
                f"Uninstalled build remains at: "
                f"{BUILD_ROOT}"
            )

        sys.exit(1)

    # --------------------------------------------------------
    # VERIFY THE ACTUAL INSTALLED LIBRARY.
    # --------------------------------------------------------

    try:

        verify_installed_library(
            teams_by_league
        )

    except Exception as exc:

        print()
        print("=" * 70)
        print("FINAL VERIFICATION FAILED")
        print("=" * 70)

        print()
        print(
            f"Reason: {exc}"
        )

        sys.exit(1)

    # --------------------------------------------------------
    # FINISHED.
    # --------------------------------------------------------

    print()
    print("=" * 70)
    print("FINISHED")
    print("=" * 70)

    print()
    print(
        f"Source teams: {total_teams}"
    )

    print(
        f"PNG files generated: "
        f"{total_generated}"
    )

    print(
        f"PNG files expected:  "
        f"{total_expected_files}"
    )

    print(
        "All team folders were rebuilt from "
        "_temp_espn_logos."
    )

    print(
        "Every team has a solo logo."
    )

    print(
        "Every team has a matchup against "
        "every other team in its league."
    )

    print(
        "Both home/away matchup directions "
        "were generated."
    )

    print(
        "The existing sports-logos library was "
        "replaced only after complete verification."
    )

    print(
        "_temp_espn_logos was preserved."
    )

    print()


if __name__ == "__main__":

    main()
