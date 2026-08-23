import os
import re
import shutil
import unicodedata

from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

from PIL import Image


# ============================================================
# CONFIG
# ============================================================

# TRUE SOURCE OF TRUTH.
#
# This directory is NEVER modified, renamed, deleted,
# or replaced by this script.
SOURCE_ROOT = Path("temp/New folder")

# FINAL SPORTS LOGO LIBRARY.
#
# This is the directory that will be completely replaced
# with the rebuilt library after successful verification.
ROOT = Path("sports-logos")

# Build into a completely separate directory first.
BUILD_ROOT = Path("_sports_logos_rebuild")

LEAGUES = {
    "MLB",
    "NBA",
    "NFL",
    "NHL",
}

# Number of team folders processed simultaneously.
BUILD_WORKERS = 8

# Matchup canvas.
MATCHUP_SIZE = (1024, 512)

# Percentage of each half available to the logo.
MATCHUP_LOGO_WIDTH_SCALE = 0.88
MATCHUP_LOGO_HEIGHT_SCALE = 0.88


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
# IMPORTANT:
#
# temp/New folder is the TRUE SOURCE OF TRUTH.
#
# The only source image used for each team is:
#
#     temp/New folder/<LEAGUE>/<TEAM>/<TEAM>.png
#
# Existing sports-logos files are NEVER used as sources.
#
# Existing matchup files are NEVER used as sources.
#
# temp/New folder is NEVER modified.
# ============================================================

def discover_source_teams():

    teams_by_league = {
        league: {}
        for league in LEAGUES
    }

    if not SOURCE_ROOT.is_dir():
        raise RuntimeError(
            f"Source library does not exist: "
            f"{SOURCE_ROOT}"
        )

    for league in sorted(LEAGUES):

        league_root = SOURCE_ROOT / league

        if not league_root.is_dir():
            raise RuntimeError(
                f"Missing source league directory: "
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

            source_logo = (
                team_folder
                /
                f"{team_folder.name}.png"
            )

            if not source_logo.is_file():
                raise RuntimeError(
                    f"Missing solo team logo: "
                    f"{source_logo}"
                )

            key = clean_name(team_name)

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

def verify_source_library(teams_by_league):

    print()
    print("=" * 70)
    print("VERIFYING TRUE SOURCE LOGO LIBRARY")
    print("=" * 70)

    print()
    print(
        f"Source: {SOURCE_ROOT}"
    )

    print()
    print(
        "SOURCE IS READ-ONLY DURING THIS RUN."
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
            key=lambda item: clean_name(item["name"])
        ):

            source = team["source"]

            if not source.is_file():
                raise RuntimeError(
                    f"Missing source logo: {source}"
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
# IMAGE PROCESSING
# ============================================================

def trim_transparency(image):

    image = image.convert("RGBA")

    alpha = image.getchannel("A")

    bbox = alpha.getbbox()

    if bbox:
        image = image.crop(bbox)

    return image


def fit_logo(
    image,
    max_width,
    max_height
):

    image = trim_transparency(image)

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
        int(image.width * scale)
    )

    height = max(
        1,
        int(image.height * scale)
    )

    return image.resize(
        (width, height),
        Image.Resampling.LANCZOS
    )


def load_source_logo(source_path):

    with Image.open(source_path) as image:

        image = image.convert("RGBA")

        image.load()

        return image.copy()


# ============================================================
# COPY SOLO LOGO
#
# The logo is copied directly from the TRUE SOURCE:
#
#     temp/New folder/<LEAGUE>/<TEAM>/<TEAM>.png
#
# It is NOT taken from sports-logos.
# ============================================================

def copy_solo_logo(
    source_path,
    destination
):

    destination.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    shutil.copy2(
        source_path,
        destination
    )


# ============================================================
# BUILD MATCHUP LOGO
#
# HOME TEAM IS ALWAYS ON THE LEFT.
# AWAY TEAM IS ALWAYS ON THE RIGHT.
#
# Example:
#
# Boston_Red_Sox_vs_Tampa_Bay_Rays.png
#
# uses ONLY:
#
# temp/New folder/MLB/Boston_Red_Sox/
#     Boston_Red_Sox.png
#
# and:
#
# temp/New folder/MLB/Tampa_Bay_Rays/
#     Tampa_Bay_Rays.png
#
# Existing matchup files are NEVER used.
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
        MATCHUP_SIZE[0] // 2
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
#
# All files are generated from the TRUE SOURCE logos.
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
    # COPY TRUE SOURCE SOLO LOGO
    # --------------------------------------------------------

    solo_path = (
        home_folder
        /
        f"{filesystem_name(home_name)}.png"
    )

    copy_solo_logo(
        home_source,
        solo_path
    )

    generated = 1

    # --------------------------------------------------------
    # REBUILD EVERY MATCHUP
    #
    # Every other team in the league is included.
    # --------------------------------------------------------

    for away_team in all_teams:

        away_name = away_team["name"]

        if clean_name(away_name) == clean_name(home_name):
            continue

        away_source = away_team["source"]

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

    expected = len(all_teams)

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
        key=lambda item: clean_name(item["name"])
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
    # VERIFY LEAGUE COUNT
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
    # VERIFY EVERY TEAM FOLDER
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

        # Every other team must have a matchup file.
        for opponent in sorted_teams:

            opponent_name = opponent["name"]

            if clean_name(opponent_name) == clean_name(team_name):
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
    print("VERIFYING COMPLETE REBUILT LIBRARY")
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
# REPLACE SPORTS-LOGOS
#
# IMPORTANT:
#
# SOURCE_ROOT = temp/New folder
#
# ROOT = sports-logos
#
# ONLY sports-logos is replaced.
#
# temp/New folder is NEVER renamed, deleted,
# or modified.
#
# The replacement happens ONLY after the complete
# rebuilt library has passed verification.
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

    print()
    print("=" * 70)
    print("INSTALLING REBUILT SPORTS LOGO LIBRARY")
    print("=" * 70)

    print()
    print(
        f"TRUE SOURCE: {SOURCE_ROOT}"
    )

    print(
        f"DESTINATION: {ROOT}"
    )

    # --------------------------------------------------------
    # BACK UP EXISTING SPORTS-LOGOS.
    #
    # This does NOT touch temp/New folder.
    # --------------------------------------------------------

    if ROOT.exists():

        print()
        print(
            f"Moving existing library to temporary backup: "
            f"{ROOT}"
        )

        ROOT.rename(
            backup_root
        )

    try:

        # ----------------------------------------------------
        # INSTALL THE VERIFIED REBUILD AS sports-logos.
        # ----------------------------------------------------

        BUILD_ROOT.rename(
            ROOT
        )

    except Exception:

        # ----------------------------------------------------
        # ROLLBACK IF INSTALLATION FAILS.
        # ----------------------------------------------------

        if (
            backup_root.exists()
            and not ROOT.exists()
        ):

            backup_root.rename(
                ROOT
            )

        raise

    # --------------------------------------------------------
    # DELETE ONLY THE OLD sports-logos BACKUP.
    #
    # temp/New folder remains completely untouched.
    # --------------------------------------------------------

    if backup_root.exists():

        shutil.rmtree(
            backup_root
        )

    print()
    print(
        "New sports-logos library installed successfully."
    )

    print(
        f"Source library preserved at: {SOURCE_ROOT}"
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

        expected_per_team = len(teams)

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

                if clean_name(opponent_name) == clean_name(team_name):
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
# VERIFY SOURCE STILL EXISTS
#
# This provides an additional safety check that the TRUE
# SOURCE was not accidentally removed or replaced.
# ============================================================

def verify_source_still_exists(
    teams_by_league
):

    print()
    print("=" * 70)
    print("VERIFYING TRUE SOURCE WAS PRESERVED")
    print("=" * 70)

    if not SOURCE_ROOT.is_dir():
        raise RuntimeError(
            f"TRUE SOURCE WAS REMOVED: "
            f"{SOURCE_ROOT}"
        )

    for league in sorted(LEAGUES):

        league_root = (
            SOURCE_ROOT
            /
            league
        )

        if not league_root.is_dir():
            raise RuntimeError(
                f"TRUE SOURCE LEAGUE WAS REMOVED: "
                f"{league_root}"
            )

        for team in teams_by_league[league].values():

            source = team["source"]

            if not source.is_file():
                raise RuntimeError(
                    f"TRUE SOURCE LOGO WAS REMOVED: "
                    f"{source}"
                )

    print()
    print(
        f"TRUE SOURCE PRESERVED: {SOURCE_ROOT}"
    )


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 70)
    print("SPORTS MATCHUP LOGO REBUILDER")
    print("=" * 70)

    print()
    print("TRUE SOURCE:")
    print(
        "  temp/New folder/<LEAGUE>/<TEAM>/<TEAM>.png"
    )

    print()
    print("FINAL DESTINATION:")
    print(
        "  sports-logos/<LEAGUE>/<TEAM>/"
    )

    print()
    print("IMPORTANT:")
    print(
        "  temp/New folder is the TRUE SOURCE OF TRUTH."
    )

    print(
        "  temp/New folder is NEVER modified."
    )

    print(
        "  Existing sports-logos logos are NOT used as sources."
    )

    print(
        "  Existing matchup logos are NOT used as sources."
    )

    print(
        "  Every solo logo comes directly from temp/New folder."
    )

    print(
        "  Every matchup is rebuilt from two TRUE SOURCE logos."
    )

    print(
        "  Both home/away matchup directions are generated."
    )

    print(
        "  No logos are downloaded."
    )

    print()
    print(
        f"Build workers: {BUILD_WORKERS}"
    )

    # --------------------------------------------------------
    # NEVER BUILD ON TOP OF THE SOURCE.
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
    # DISCOVER TEAMS FROM TRUE SOURCE.
    # --------------------------------------------------------

    teams_by_league = discover_source_teams()

    total_teams = verify_source_library(
        teams_by_league
    )

    print()
    print("=" * 70)
    print("EXPECTED REBUILT LIBRARY")
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
    # BUILD EVERY LEAGUE FROM TRUE SOURCE.
    # --------------------------------------------------------

    generated_total = 0

    for league in sorted(LEAGUES):

        generated_total += build_league(
            league,
            teams_by_league[league],
            BUILD_ROOT
        )

    # --------------------------------------------------------
    # COMPLETE BUILD VERIFICATION.
    # --------------------------------------------------------

    verify_generated_library(
        BUILD_ROOT,
        teams_by_league
    )

    # --------------------------------------------------------
    # INSTALL INTO sports-logos.
    #
    # temp/New folder is NOT touched.
    # --------------------------------------------------------

    install_new_library()

    # --------------------------------------------------------
    # VERIFY THE ACTUAL INSTALLED LIBRARY.
    # --------------------------------------------------------

    verify_installed_library(
        teams_by_league
    )

    # --------------------------------------------------------
    # VERIFY TRUE SOURCE STILL EXISTS.
    # --------------------------------------------------------

    verify_source_still_exists(
        teams_by_league
    )

    # --------------------------------------------------------
    # FINAL REPORT.
    # --------------------------------------------------------

    print()
    print("=" * 70)
    print("FINISHED")
    print("=" * 70)

    print()
    print(
        f"TRUE SOURCE: {SOURCE_ROOT}"
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
        "The sports-logos library was completely rebuilt "
        "from the logos in temp/New folder."
    )

    print(
        "Every team has a solo logo from the new source."
    )

    print(
        "Every team has a matchup against every other "
        "team in its league."
    )

    print(
        "Both home/away matchup directions were generated."
    )

    print(
        "Existing sports-logos matchup files were never "
        "used as sources."
    )

    print(
        "Existing sports-logos solo logos were never "
        "used as sources."
    )

    print(
        "temp/New folder was preserved as the permanent "
        "source library."
    )

    print(
        "No external logo downloads were performed."
    )


if __name__ == "__main__":
    main()
