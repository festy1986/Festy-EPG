import io
import os
import re
import sys
import time
import html
import unicodedata
from pathlib import Path
from difflib import SequenceMatcher
from urllib.parse import quote, urljoin
from html.parser import HTMLParser

import requests
from PIL import Image


# ============================================================
# CONFIG
# ============================================================

ROOT = Path("sports-logos")

LEAGUES = {
    "MLB",
    "NBA",
    "NFL",
    "NHL",
}

CDNLOGO_BASE = "https://cdnlogo.com"

REQUEST_TIMEOUT = 30

REQUEST_DELAY = 0.25

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/151.0 Safari/537.36"
    )
}


# ============================================================
# TEAM NAME NORMALIZATION
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
}


def clean_name(value):
    """
    Convert filenames/folder names into a normalized searchable name.
    """

    value = os.path.splitext(value)[0]

    value = value.replace("_", " ")

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

    value = value.strip().lower()

    return value


def display_team_name(raw):
    raw = os.path.splitext(raw)[0]

    if raw in ALIASES:
        return ALIASES[raw]

    return raw.replace("_", " ")


def normalized_search_name(raw):
    name = display_team_name(raw)

    return clean_name(name)


# ============================================================
# SIMPLE HTML PARSER
# Replaces BeautifulSoup so no bs4 dependency is required.
# ============================================================

class CDNLogoHTMLParser(HTMLParser):

    def __init__(self):
        super().__init__(
            convert_charrefs=True
        )

        self.links = []

        self.images = []

        self.current_link = None

        self.current_link_text = []

    def handle_starttag(
        self,
        tag,
        attrs
    ):

        attributes = dict(attrs)

        if tag.lower() == "a":

            self.current_link = {
                "href": attributes.get(
                    "href"
                ),
                "text": []
            }

            self.current_link_text = []

        elif tag.lower() == "img":

            self.images.append(
                attributes
            )

    def handle_data(self, data):

        if self.current_link is not None:

            self.current_link_text.append(
                data
            )

    def handle_endtag(self, tag):

        if tag.lower() == "a":

            if self.current_link is not None:

                self.current_link[
                    "text"
                ] = " ".join(
                    self.current_link_text
                ).strip()

                self.links.append(
                    self.current_link
                )

            self.current_link = None

            self.current_link_text = []


def parse_html(response_text):

    parser = CDNLogoHTMLParser()

    parser.feed(
        response_text
    )

    return parser


# ============================================================
# HTTP
# ============================================================

session = requests.Session()
session.headers.update(HEADERS)


def get(url):

    response = session.get(
        url,
        timeout=REQUEST_TIMEOUT
    )

    response.raise_for_status()

    return response


# ============================================================
# CDNLOGO SEARCH
# ============================================================

def search_cdnlogo(team_name):
    """
    Search CDNLogo's own site for the team.

    We deliberately search CDNLogo itself rather than using
    a hard-coded list of image URLs.
    """

    query = quote(team_name)

    urls = [
        f"{CDNLOGO_BASE}/search?q={query}",
        f"{CDNLOGO_BASE}/?q={query}",
    ]

    candidates = []

    for url in urls:

        try:

            response = get(url)

        except Exception:

            continue

        parser = parse_html(
            response.text
        )

        for link in parser.links:

            href = link.get(
                "href"
            )

            if not href:
                continue

            href = html.unescape(
                href
            )

            href = urljoin(
                CDNLOGO_BASE,
                href
            )

            if "/logo/" not in href:
                continue

            text = link.get(
                "text",
                ""
            ).strip()

            candidates.append(
                (
                    text,
                    href
                )
            )

        if candidates:
            break

        time.sleep(
            REQUEST_DELAY
        )

    return candidates


# ============================================================
# DIRECT LOGO PAGE DISCOVERY
# ============================================================

def search_engine_fallback(team_name):
    """
    CDNLogo search pages have changed over time.

    If their search page doesn't expose a usable result,
    try CDNLogo's searchable URL directly.
    """

    slug = clean_name(
        team_name
    ).replace(
        " ",
        "-"
    )

    urls = [
        f"{CDNLOGO_BASE}/logo/{slug}.html",
        f"{CDNLOGO_BASE}/logos/{slug}",
    ]

    results = []

    for url in urls:

        try:

            response = get(url)

            if response.status_code == 200:

                results.append(
                    (
                        team_name,
                        response.url
                    )
                )

        except Exception:

            pass

    return results


# ============================================================
# MATCH RESULT
# ============================================================

def score_candidate(
    team_name,
    candidate_name
):
    """
    Score a CDNLogo result against our team name.

    Exact and near-exact matches win.
    """

    wanted = clean_name(
        team_name
    )

    candidate = clean_name(
        candidate_name
    )

    if not candidate:
        return 0.0

    if candidate == wanted:
        return 1.0

    if wanted in candidate:
        return 0.95

    if candidate in wanted:
        return 0.90

    return SequenceMatcher(
        None,
        wanted,
        candidate
    ).ratio()


def choose_candidate(
    team_name,
    candidates
):

    scored = []

    for title, url in candidates:

        score = score_candidate(
            team_name,
            title
        )

        scored.append(
            (
                score,
                title,
                url
            )
        )

    scored.sort(
        key=lambda x: x[0],
        reverse=True
    )

    if not scored:
        return None

    best = scored[0]

    # Do not accept wildly unrelated results.
    if best[0] < 0.70:
        return None

    return best


# ============================================================
# EXTRACT CDN IMAGE FROM LOGO PAGE
# ============================================================

def extract_png_from_page(
    page_url,
    team_name
):
    """
    CDNLogo logo pages expose their CDN image URL in the page.

    Prefer PNG over SVG because the output library is PNG.
    """

    response = get(
        page_url
    )

    parser = parse_html(
        response.text
    )

    candidates = []

    # --------------------------------------------------------
    # IMG TAGS
    # --------------------------------------------------------

    for img in parser.images:

        for attr in (
            "src",
            "data-src",
            "data-original",
            "data-lazy-src",
        ):

            value = img.get(
                attr
            )

            if not value:
                continue

            value = html.unescape(
                value
            )

            value = urljoin(
                page_url,
                value
            )

            if "static.cdnlogo.com" in value:

                if value not in candidates:

                    candidates.append(
                        value
                    )

    # --------------------------------------------------------
    # RAW HTML
    # --------------------------------------------------------

    patterns = [
        r'https?://static\.cdnlogo\.com/[^"\']+\.png',
        r'https?://static\.cdnlogo\.com/[^"\']+\.svg',
    ]

    for pattern in patterns:

        for match in re.findall(
            pattern,
            response.text,
            re.IGNORECASE
        ):

            match = html.unescape(
                match
            )

            if match not in candidates:

                candidates.append(
                    match
                )

    # --------------------------------------------------------
    # RELATIVE CDN IMAGE REFERENCES
    # --------------------------------------------------------

    relative_patterns = [
        r'["\']([^"\']+\.png)["\']',
        r'["\']([^"\']+\.svg)["\']',
    ]

    for pattern in relative_patterns:

        for match in re.findall(
            pattern,
            response.text,
            re.IGNORECASE
        ):

            if (
                "cdnlogo" not in match.lower()
                and not match.startswith("/")
            ):
                continue

            absolute = urljoin(
                page_url,
                html.unescape(match)
            )

            if "static.cdnlogo.com" in absolute:

                if absolute not in candidates:

                    candidates.append(
                        absolute
                    )

    # --------------------------------------------------------
    # PREFER FULL-SIZE PNG
    # --------------------------------------------------------

    pngs = [
        x for x in candidates
        if ".png" in x.lower()
        and "thumb" not in x.lower()
    ]

    if pngs:
        return pngs[0]

    pngs = [
        x for x in candidates
        if ".png" in x.lower()
    ]

    if pngs:
        return pngs[0]

    # --------------------------------------------------------
    # SVG FALLBACK
    # --------------------------------------------------------

    svgs = [
        x for x in candidates
        if ".svg" in x.lower()
        and "thumb" not in x.lower()
    ]

    if svgs:
        return svgs[0]

    raise RuntimeError(
        f"Could not find CDNLogo image on "
        f"{page_url} for {team_name}"
    )


# ============================================================
# FIND TEAM SOURCE
# ============================================================

SOURCE_CACHE = {}


def find_team_source(team_name):

    cache_key = clean_name(
        team_name
    )

    if cache_key in SOURCE_CACHE:

        return SOURCE_CACHE[
            cache_key
        ]

    print()

    print(
        f"Finding CDNLogo source: {team_name}"
    )

    candidates = search_cdnlogo(
        team_name
    )

    best = choose_candidate(
        team_name,
        candidates
    )

    if not best:

        candidates = search_engine_fallback(
            team_name
        )

        best = choose_candidate(
            team_name,
            candidates
        )

    if not best:

        raise RuntimeError(
            f"Could not find a sufficiently "
            f"close CDNLogo result for: "
            f"{team_name}"
        )

    score, title, page_url = best

    print(
        f"  Match: {title}"
    )

    print(
        f"  Score: {score:.3f}"
    )

    print(
        f"  Page: {page_url}"
    )

    image_url = extract_png_from_page(
        page_url,
        team_name
    )

    print(
        f"  Image: {image_url}"
    )

    SOURCE_CACHE[
        cache_key
    ] = (
        image_url,
        page_url
    )

    time.sleep(
        REQUEST_DELAY
    )

    return (
        image_url,
        page_url
    )


# ============================================================
# DOWNLOAD IMAGE
# ============================================================

IMAGE_CACHE = {}


def download_logo(team_name):

    key = clean_name(
        team_name
    )

    if key in IMAGE_CACHE:

        return IMAGE_CACHE[
            key
        ].copy()

    image_url, page_url = find_team_source(
        team_name
    )

    response = get(
        image_url
    )

    image = Image.open(
        io.BytesIO(
            response.content
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
# IMAGE PROCESSING
# ============================================================

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

    if image.width <= 0 or image.height <= 0:

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
# EXISTING IMAGE DIMENSIONS
# ============================================================

def existing_dimensions(path):

    with Image.open(path) as image:

        return image.size


# ============================================================
# SOLO LOGO
# ============================================================

def rebuild_solo(
    path,
    team
):

    width, height = existing_dimensions(
        path
    )

    source = download_logo(
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
# MATCHUP LOGO
# ============================================================

def rebuild_matchup(
    path,
    home_team,
    away_team
):

    width, height = existing_dimensions(
        path
    )

    home_source = download_logo(
        home_team
    )

    away_source = download_logo(
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
        half_width +
        (
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
# DISCOVER EXISTING TEAMS
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
            display_team_name(away)
        ]

    return [
        display_team_name(filename)
    ]


# ============================================================
# FIRST PASS:
# DISCOVER EVERY TEAM BEFORE MODIFYING ANY FILE.
# ============================================================

def discover_all_teams():

    teams = {}

    for league, path in discover_files():

        for team in teams_from_file(
            path
        ):

            key = clean_name(
                team
            )

            teams[key] = team

    return sorted(
        teams.values(),
        key=lambda x: clean_name(x)
    )


# ============================================================
# VERIFY ALL SOURCES FIRST
#
# IMPORTANT:
# We do NOT overwrite the library until every team has a
# successfully discovered CDNLogo source.
# ============================================================

def verify_sources(teams):

    print()

    print("=" * 70)
    print("VERIFYING CDNLOGO SOURCES")
    print("=" * 70)

    for number, team in enumerate(
        teams,
        start=1
    ):

        print()

        print(
            f"[{number}/{len(teams)}] {team}"
        )

        find_team_source(
            team
        )

    print()

    print(
        f"Verified {len(teams)} team sources."
    )


# ============================================================
# REBUILD EXISTING LIBRARY
# ============================================================

def rebuild_library():

    total = 0

    replaced = 0

    failed = 0

    for league, path in discover_files():

        total += 1

        teams = teams_from_file(
            path
        )

        try:

            if len(teams) == 1:

                print()

                print(
                    f"[{league}] SOLO"
                )

                print(
                    f"  {path}"
                )

                rebuild_solo(
                    path,
                    teams[0]
                )

            else:

                print()

                print(
                    f"[{league}] MATCHUP"
                )

                print(
                    f"  {path}"
                )

                print(
                    f"  HOME: {teams[0]}"
                )

                print(
                    f"  AWAY: {teams[1]}"
                )

                rebuild_matchup(
                    path,
                    teams[0],
                    teams[1]
                )

            replaced += 1

        except Exception as exc:

            failed += 1

            print()

            print(
                "ERROR:"
            )

            print(
                f"  {path}"
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
    print("CDNLOGO SPORTS LOGO LIBRARY REBUILDER")
    print("=" * 70)

    if not ROOT.is_dir():

        print()

        print(
            f"ERROR: {ROOT} does not exist."
        )

        sys.exit(1)

    teams = discover_all_teams()

    if not teams:

        print()

        print(
            "ERROR: No PNG logos found."
        )

        sys.exit(1)

    print()

    print(
        f"Discovered {len(teams)} unique teams."
    )

    print()

    print(
        "Leagues:"
    )

    for league in sorted(
        LEAGUES
    ):

        directory = ROOT / league

        if directory.is_dir():

            print(
                f"  {league}"
            )

    # --------------------------------------------------------
    # VERIFY EVERYTHING FIRST.
    #
    # If even one team cannot be found, nothing gets changed.
    # --------------------------------------------------------

    try:

        verify_sources(
            teams
        )

    except Exception as exc:

        print()

        print("=" * 70)
        print("ABORTED")
        print("=" * 70)

        print()

        print(
            "No existing logo files were modified."
        )

        print()

        print(
            f"Reason: {exc}"
        )

        sys.exit(1)

    # --------------------------------------------------------
    # ALL SOURCES VERIFIED.
    # NOW modify the existing library.
    # --------------------------------------------------------

    print()

    print("=" * 70)
    print("REBUILDING EXISTING LOGO LIBRARY")
    print("=" * 70)

    total, replaced, failed = rebuild_library()

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
        "No filenames or directory paths were changed."
    )

    print()

    if failed:

        sys.exit(1)


if __name__ == "__main__":

    main()
