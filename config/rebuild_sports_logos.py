import io
import os
import re
import sys
import time
import html
import unicodedata
from pathlib import Path
from urllib.parse import quote

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

LEAGUES = (
    "MLB",
    "NBA",
    "NFL",
    "NHL",
)

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
# EXPLICIT CURRENT TEAM SLUG OVERRIDES
#
# These are used instead of scraping a broken league index.
# ============================================================

SLUG_OVERRIDES = {

    # --------------------------------------------------------
    # MLB
    # --------------------------------------------------------

    "arizona diamondbacks":
        "arizona-diamondbacks",

    "atlanta braves":
        "atlanta-braves",

    "baltimore orioles":
        "baltimore-orioles",

    "boston red sox":
        "boston-red-sox",

    "chicago cubs":
        "chicago-cubs",

    "chicago white sox":
        "chicago-white-sox",

    "cincinnati reds":
        "cincinnati-reds",

    "cleveland guardians":
        "cleveland-guardians",

    "colorado rockies":
        "colorado-rockies",

    "detroit tigers":
        "detroit-tigers",

    "houston astros":
        "houston-astros",

    "kansas city royals":
        "kansas-city-royals",

    "los angeles angels":
        "los-angeles-angels",

    "los angeles dodgers":
        "los-angeles-dodgers",

    "miami marlins":
        "miami-marlins",

    "milwaukee brewers":
        "milwaukee-brewers",

    "minnesota twins":
        "minnesota-twins",

    "new york mets":
        "new-york-mets",

    "new york yankees":
        "new-york-yankees",

    "oakland athletics":
        "oakland-athletics",

    "athletics":
        "athletics",

    "philadelphia phillies":
        "philadelphia-phillies",

    "pittsburgh pirates":
        "pittsburgh-pirates",

    "san diego padres":
        "san-diego-padres",

    "san francisco giants":
        "san-francisco-giants",

    "seattle mariners":
        "seattle-mariners",

    "st louis cardinals":
        "st-louis-cardinals",

    "tampa bay rays":
        "tampa-bay-rays",

    "texas rangers":
        "texas-rangers",

    "toronto blue jays":
        "toronto-blue-jays",

    "washington nationals":
        "washington-nationals",


    # --------------------------------------------------------
    # NBA
    # --------------------------------------------------------

    "atlanta hawks":
        "atlanta-hawks",

    "boston celtics":
        "boston-celtics",

    "brooklyn nets":
        "brooklyn-nets",

    "charlotte hornets":
        "charlotte-hornets",

    "chicago bulls":
        "chicago-bulls",

    "cleveland cavaliers":
        "cleveland-cavaliers",

    "dallas mavericks":
        "dallas-mavericks",

    "denver nuggets":
        "denver-nuggets",

    "detroit pistons":
        "detroit-pistons",

    "golden state warriors":
        "golden-state-warriors",

    "houston rockets":
        "houston-rockets",

    "indiana pacers":
        "indiana-pacers",

    "la clippers":
        "la-clippers",

    "los angeles clippers":
        "los-angeles-clippers",

    "los angeles lakers":
        "los-angeles-lakers",

    "memphis grizzlies":
        "memphis-grizzlies",

    "miami heat":
        "miami-heat",

    "milwaukee bucks":
        "milwaukee-bucks",

    "minnesota timberwolves":
        "minnesota-timberwolves",

    "new orleans pelicans":
        "new-orleans-pelicans",

    "new york knicks":
        "new-york-knicks",

    "oklahoma city thunder":
        "oklahoma-city-thunder",

    "orlando magic":
        "orlando-magic",

    "philadelphia 76ers":
        "philadelphia-76ers",

    "phoenix suns":
        "phoenix-suns",

    "portland trail blazers":
        "portland-trail-blazers",

    "sacramento kings":
        "sacramento-kings",

    "san antonio spurs":
        "san-antonio-spurs",

    "toronto raptors":
        "toronto-raptors",

    "utah jazz":
        "utah-jazz",

    "washington wizards":
        "washington-wizards",


    # --------------------------------------------------------
    # NFL
    # --------------------------------------------------------

    "arizona cardinals":
        "arizona-cardinals",

    "atlanta falcons":
        "atlanta-falcons",

    "baltimore ravens":
        "baltimore-ravens",

    "buffalo bills":
        "buffalo-bills",

    "carolina panthers":
        "carolina-panthers",

    "chicago bears":
        "chicago-bears",

    "cincinnati bengals":
        "cincinnati-bengals",

    "cleveland browns":
        "cleveland-browns",

    "dallas cowboys":
        "dallas-cowboys",

    "denver broncos":
        "denver-broncos",

    "detroit lions":
        "detroit-lions",

    "green bay packers":
        "green-bay-packers",

    "houston texans":
        "houston-texans",

    "indianapolis colts":
        "indianapolis-colts",

    "jacksonville jaguars":
        "jacksonville-jaguars",

    "kansas city chiefs":
        "kansas-city-chiefs",

    "las vegas raiders":
        "las-vegas-raiders",

    "los angeles chargers":
        "los-angeles-chargers",

    "los angeles rams":
        "los-angeles-rams",

    "miami dolphins":
        "miami-dolphins",

    "minnesota vikings":
        "minnesota-vikings",

    "new england patriots":
        "new-england-patriots",

    "new orleans saints":
        "new-orleans-saints",

    "new york giants":
        "new-york-giants",

    "new york jets":
        "new-york-jets",

    "philadelphia eagles":
        "philadelphia-eagles",

    "pittsburgh steelers":
        "pittsburgh-steelers",

    "san francisco 49ers":
        "san-francisco-49ers",

    "seattle seahawks":
        "seattle-seahawks",

    "tampa bay buccaneers":
        "tampa-bay-buccaneers",

    "tennessee titans":
        "tennessee-titans",

    "washington commanders":
        "washington-commanders",


    # --------------------------------------------------------
    # NHL
    # --------------------------------------------------------

    "anaheim ducks":
        "anaheim-ducks",

    "arizona coyotes":
        "arizona-coyotes",

    "boston bruins":
        "boston-bruins",

    "buffalo sabres":
        "buffalo-sabres",

    "calgary flames":
        "calgary-flames",

    "carolina hurricanes":
        "carolina-hurricanes",

    "chicago blackhawks":
        "chicago-blackhawks",

    "colorado avalanche":
        "colorado-avalanche",

    "columbus blue jackets":
        "columbus-blue-jackets",

    "dallas stars":
        "dallas-stars",

    "detroit red wings":
        "detroit-red-wings",

    "edmonton oilers":
        "edmonton-oilers",

    "florida panthers":
        "florida-panthers",

    "los angeles kings":
        "los-angeles-kings",

    "minnesota wild":
        "minnesota-wild",

    "montreal canadiens":
        "montreal-canadiens",

    "nashville predators":
        "nashville-predators",

    "new jersey devils":
        "new-jersey-devils",

    "new york islanders":
        "new-york-islanders",

    "new york rangers":
        "new-york-rangers",

    "ottawa senators":
        "ottawa-senators",

    "philadelphia flyers":
        "philadelphia-flyers",

    "pittsburgh penguins":
        "pittsburgh-penguins",

    "san jose sharks":
        "san-jose-sharks",

    "seattle kraken":
        "seattle-kraken",

    "st louis blues":
        "st-louis-blues",

    "tampa bay lightning":
        "tampa-bay-lightning",

    "toronto maple leafs":
        "toronto-maple-leafs",

    "utah mammoth":
        "utah-mammoth",

    "vancouver canucks":
        "vancouver-canucks",

    "vegas golden knights":
        "vegas-golden-knights",

    "winnipeg jets":
        "winnipeg-jets",
}


# ============================================================
# CURRENT LOGO CDN
#
# logocdn.com uses year-based logo paths.
# We try several years because the current logo can live under
# a different historical year.
# ============================================================

LOGO_YEARS = {
    "MLB": (
        2026, 2025, 2024, 2023, 2022,
        2021, 2020, 2019, 2018, 2017,
        2016, 2015, 2014, 2013, 2012,
    ),

    "NBA": (
        2025, 2024, 2023, 2022, 2021,
        2020, 2019, 2018, 2017, 2016,
    ),

    "NFL": (
        2025, 2024, 2023, 2022, 2021,
        2020, 2019, 2018, 2017, 2016,
        2015, 2014, 2013, 2012,
    ),

    "NHL": (
        2025, 2024, 2023, 2022, 2021,
        2020, 2019, 2018, 2017, 2016,
        2015, 2014, 2013, 2012,
    ),
}


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
        timeout=REQUEST_TIMEOUT,
        allow_redirects=True
    )

    response.raise_for_status()

    return response


# ============================================================
# NORMALIZATION
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
        c for c in value
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

        return ALIASES[
            raw
        ]

    return raw.replace(
        "_",
        " "
    )


# ============================================================
# DISCOVER EXISTING LIBRARY
# ============================================================

def discover_files():

    for league in LEAGUES:

        league_dir = (
            ROOT / league
        )

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

            teams[league][
                key
            ] = team

    return teams


# ============================================================
# SLUG
# ============================================================

def team_slug(team):

    key = clean_name(
        team
    )

    if key in SLUG_OVERRIDES:

        return SLUG_OVERRIDES[
            key
        ]

    return key.replace(
        " ",
        "-"
    )


# ============================================================
# SOURCE URL GENERATION
# ============================================================

def possible_logo_urls(
    league,
    team
):

    slug = team_slug(
        team
    )

    urls = []

    # --------------------------------------------------------
    # Current year / historical year paths.
    # --------------------------------------------------------

    for year in LOGO_YEARS[
        league
    ]:

        urls.append(
            f"https://i.logocdn.com/"
            f"{league.lower()}/"
            f"{year}/"
            f"{slug}.svg"
        )

        urls.append(
            f"https://i.logocdn.com/"
            f"{league.lower()}/"
            f"{year}/"
            f"{slug}.png"
        )

    # --------------------------------------------------------
    # Non-year fallback.
    # --------------------------------------------------------

    urls.append(
        f"https://i.logocdn.com/"
        f"{league.lower()}/"
        f"{slug}.svg"
    )

    urls.append(
        f"https://i.logocdn.com/"
        f"{league.lower()}/"
        f"{slug}.png"
    )

    return urls


# ============================================================
# IMAGE CONVERSION
# ============================================================

def response_to_image(
    response,
    team
):

    content = response.content

    content_type = (
        response.headers.get(
            "Content-Type",
            ""
        ).lower()
    )

    is_svg = (
        "svg" in content_type
        or content.lstrip().startswith(
            b"<svg"
        )
        or b"<svg" in content[:1000].lower()
    )

    if is_svg:

        if cairosvg is None:

            raise RuntimeError(
                "CairoSVG is required for SVG logos."
            )

        png_bytes = cairosvg.svg2png(
            bytestring=content
        )

        image = Image.open(
            io.BytesIO(
                png_bytes
            )
        )

    else:

        image = Image.open(
            io.BytesIO(
                content
            )
        )

    image.load()

    return image.convert(
        "RGBA"
    )


# ============================================================
# DOWNLOAD ONE LOGO
# ============================================================

def download_team_logo(
    league,
    team,
    destination
):

    urls = possible_logo_urls(
        league,
        team
    )

    last_error = None

    for number, url in enumerate(
        urls,
        start=1
    ):

        try:

            response = get(
                url
            )

            image = response_to_image(
                response,
                team
            )

            if (
                image.width < 2
                or image.height < 2
            ):

                raise RuntimeError(
                    "Image is too small."
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

            print(
                f"  Source: {url}"
            )

            print(
                f"  Saved:  {destination}"
            )

            time.sleep(
                REQUEST_DELAY
            )

            return url

        except Exception as exc:

            last_error = exc

            continue

    raise RuntimeError(
        f"Could not download logo for "
        f"{league}: {team}. "
        f"Last error: {last_error}"
    )


# ============================================================
# DOWNLOAD ALL LOGOS
# ============================================================

def download_all_logos(
    teams_by_league
):

    if TEMP_ROOT.exists():

        # Remove stale files so the verification really means
        # everything in this run was successfully downloaded.
        for path in sorted(
            TEMP_ROOT.rglob("*"),
            reverse=True
        ):

            if path.is_file():

                path.unlink()

            elif path.is_dir():

                try:
                    path.rmdir()
                except OSError:
                    pass

    TEMP_ROOT.mkdir(
        parents=True,
        exist_ok=True
    )

    downloaded = 0

    total = sum(
        len(teams)
        for teams in teams_by_league.values()
    )

    print()

    print("=" * 70)
    print("DOWNLOADING CURRENT BIG-4 LOGOS")
    print("=" * 70)

    for league in LEAGUES:

        teams = teams_by_league[
            league
        ]

        print()

        print(
            f"{league}: expected {len(teams)}"
        )

        for number, team in enumerate(
            sorted(
                teams.values(),
                key=lambda x: clean_name(x)
            ),
            start=1
        ):

            print()

            print(
                f"[{league} {number}/{len(teams)}] "
                f"{team}"
            )

            destination = (
                TEMP_ROOT
                / league
                / f"{team}.png"
            )

            download_team_logo(
                league,
                team,
                destination
            )

            downloaded += 1

    print()

    print(
        f"Successfully downloaded "
        f"{downloaded}/{total} logos."
    )

    return downloaded


# ============================================================
# VERIFY TEMP LIBRARY
# ============================================================

def verify_temp_library(
    teams_by_league
):

    print()

    print("=" * 70)
    print("VERIFYING TEMPORARY LOGO LIBRARY")
    print("=" * 70)

    missing = []

    expected = 0
    found = 0

    for league in LEAGUES:

        teams = teams_by_league[
            league
        ]

        for team in teams.values():

            expected += 1

            path = (
                TEMP_ROOT
                / league
                / f"{team}.png"
            )

            if not path.is_file():

                missing.append(
                    f"{league}: {team}"
                )

                continue

            try:

                with Image.open(
                    path
                ) as image:

                    image.verify()

                found += 1

            except Exception as exc:

                missing.append(
                    f"{league}: {team} "
                    f"(invalid image: {exc})"
                )

    print(
        f"Expected: {expected}"
    )

    print(
        f"Found:    {found}"
    )

    if missing:

        print()

        print(
            "Missing/invalid logos:"
        )

        for item in missing:

            print(
                f"  {item}"
            )

        raise RuntimeError(
            f"{len(missing)} logos are missing "
            f"or invalid."
        )

    print()

    print(
        "All 124 required logos verified."
    )


# ============================================================
# IMAGE PROCESSING
# ============================================================

def existing_dimensions(path):

    with Image.open(
        path
    ) as image:

        return image.size


def trim_transparency(image):

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


# ============================================================
# TEMP IMAGE CACHE
# ============================================================

TEMP_IMAGE_CACHE = {}


def load_temp_logo(
    league,
    team
):

    key = (
        league,
        clean_name(team)
    )

    if key in TEMP_IMAGE_CACHE:

        return TEMP_IMAGE_CACHE[
            key
        ].copy()

    path = (
        TEMP_ROOT
        / league
        / f"{team}.png"
    )

    if not path.is_file():

        raise RuntimeError(
            f"Temporary logo missing: {path}"
        )

    with Image.open(
        path
    ) as image:

        image = image.convert(
            "RGBA"
        )

        image.load()

        cached = image.copy()

    TEMP_IMAGE_CACHE[
        key
    ] = cached

    return cached.copy()


# ============================================================
# REBUILD SOLO
# ============================================================

def rebuild_solo(
    league,
    path,
    team
):

    width, height = existing_dimensions(
        path
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
    league,
    path,
    home_team,
    away_team
):

    width, height = existing_dimensions(
        path
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
# No filenames or directory paths are changed.
# ============================================================

def rebuild_library():

    total = 0
    replaced = 0
    failed = 0

    print()

    print("=" * 70)
    print("REBUILDING EXISTING SPORTS LOGO LIBRARY")
    print("=" * 70)

    for league, path in discover_files():

        total += 1

        teams = teams_from_file(
            path
        )

        try:

            if len(teams) == 1:

                print(
                    f"[{league}] SOLO  {path}"
                )

                rebuild_solo(
                    league,
                    path,
                    teams[0]
                )

            else:

                print(
                    f"[{league}] MATCHUP {path}"
                )

                rebuild_matchup(
                    league,
                    path,
                    teams[0],
                    teams[1]
                )

            replaced += 1

        except Exception as exc:

            failed += 1

            print()

            print(
                f"ERROR: {path}"
            )

            print(
                f"  {exc}"
            )

    return (
        total,
        replaced,
        failed
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

    if cairosvg is None:

        print()

        print(
            "ERROR: CairoSVG is required."
        )

        sys.exit(1)

    teams_by_league = discover_all_teams()

    total_teams = sum(
        len(teams)
        for teams in teams_by_league.values()
    )

    print()

    print(
        f"Existing library contains "
        f"{total_teams} unique teams."
    )

    for league in LEAGUES:

        print(
            f"  {league}: "
            f"{len(teams_by_league[league])} "
            f"unique teams used by existing library"
        )

    if total_teams != 124:

        print()

        print(
            "WARNING: Existing library does not contain "
            "exactly 124 teams."
        )

        print(
            "The script will use exactly the teams found "
            "in the existing library."
        )

    # --------------------------------------------------------
    # DOWNLOAD EVERYTHING FIRST.
    # --------------------------------------------------------

    try:

        downloaded = download_all_logos(
            teams_by_league
        )

        verify_temp_library(
            teams_by_league
        )

    except Exception as exc:

        print()

        print("=" * 70)
        print("ABORTED DURING DOWNLOAD")
        print("=" * 70)

        print()

        print(
            "Existing sports-logos library was NOT modified."
        )

        print()

        print(
            f"Reason: {exc}"
        )

        sys.exit(1)

    # --------------------------------------------------------
    # ONLY NOW MODIFY EXISTING FILES.
    # --------------------------------------------------------

    total, replaced, failed = (
        rebuild_library()
    )

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
        f"Files failed:   {failed}"
    )

    print()

    print(
        "Temporary source logos:"
    )

    print(
        f"  {TEMP_ROOT}"
    )

    print()

    print(
        "No filenames or directory paths were changed."
    )

    if failed:

        sys.exit(1)


if __name__ == "__main__":

    main()
