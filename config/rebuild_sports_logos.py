import io
import os
import re
import sys
import time
import html
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

LEAGUES = {
    "MLB",
    "NBA",
    "NFL",
    "NHL",
}

CDNLOGO_BASE = "https://cdnlogo.com"

# CDNLogo's current sports index is paginated.
CDNLOGO_SPORTS_INDEX = (
    "https://cdnlogo.com/logos/sports?page={}"
)

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
# TEAM NAME NORMALIZATION
# ============================================================

ALIASES = {
    "Los_Angeles_Angels": "Los Angeles Angels",
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
}


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


def display_team_name(raw):

    raw = os.path.splitext(raw)[0]

    if raw in ALIASES:
        return ALIASES[raw]

    return raw.replace("_", " ")


# ============================================================
# NAME VARIATIONS
# ============================================================

def team_search_variations(team_name):

    original = display_team_name(
        team_name
    )

    variations = [
        original
    ]

    normalized = clean_name(
        original
    )

    replacements = {

        "los angeles angels":
            "los angeles angels of anaheim",

        "athletics":
            "oakland athletics",

        "arizona coyotes":
            "phoenix coyotes",

        "utah mammoth":
            "utah mammoth",

        "washington commanders":
            "washington commanders",
    }

    if normalized in replacements:

        variations.append(
            replacements[normalized]
        )

    simplified = re.sub(
        r"\b(football|basketball|hockey|baseball)\b",
        "",
        original,
        flags=re.IGNORECASE
    )

    simplified = re.sub(
        r"\s+",
        " ",
        simplified
    ).strip()

    if (
        simplified
        and simplified.lower()
        != original.lower()
    ):

        variations.append(
            simplified
        )

    output = []

    seen = set()

    for value in variations:

        key = clean_name(value)

        if key and key not in seen:

            seen.add(key)

            output.append(value)

    return output


# ============================================================
# HTML PARSER
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
                "href": attributes.get("href"),
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
# CANDIDATE SCORING
# ============================================================

def score_candidate(
    team_name,
    candidate_name
):

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

        return 0.96

    if candidate in wanted:

        return 0.94

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

    variations = team_search_variations(
        team_name
    )

    for title, url, image_url in candidates:

        best_score = 0.0

        for variation in variations:

            title_score = score_candidate(
                variation,
                title
            )

            url_name = re.sub(
                r"^https?://[^/]+/logo/",
                "",
                url,
                flags=re.IGNORECASE
            )

            url_name = re.sub(
                r"_\d+\.html.*$",
                "",
                url_name,
                flags=re.IGNORECASE
            )

            url_name = url_name.replace(
                "-",
                " "
            )

            url_score = score_candidate(
                variation,
                url_name
            )

            best_score = max(
                best_score,
                title_score,
                url_score
            )

        scored.append(
            (
                best_score,
                title,
                url,
                image_url
            )
        )

    if not scored:

        return None

    scored.sort(
        key=lambda x: x[0],
        reverse=True
    )

    best = scored[0]

    if best[0] < 0.70:

        return None

    return best


# ============================================================
# CDNLOGO SPORTS INDEX
#
# IMPORTANT:
#
# We no longer use Google/Bing.
#
# CDNLogo's sports index contains the actual logo entries and
# the corresponding CDN static image URLs.
# ============================================================

CDNLOGO_INDEX_CACHE = None


def extract_static_image_from_link(
    page_url,
    link
):

    href = link.get(
        "href"
    )

    if not href:

        return None

    href = html.unescape(
        href
    )

    href = urljoin(
        CDNLOGO_BASE,
        href
    )

    text = link.get(
        "text",
        ""
    ).strip()

    # --------------------------------------------------------
    # Find the actual static CDNLogo asset in the surrounding
    # page HTML later. For now the page URL is sufficient.
    # --------------------------------------------------------

    return href


def collect_cdnlogo_sports_index():

    global CDNLOGO_INDEX_CACHE

    if CDNLOGO_INDEX_CACHE is not None:

        return CDNLOGO_INDEX_CACHE

    print()

    print(
        "Downloading CDNLogo sports index..."
    )

    candidates = []

    # CDNLogo currently has hundreds of pages of sports logos.
    # We scan until the site stops returning new entries.
    #
    # The exact number of pages can change, so we don't hard-code
    # a page count based on the total logo count.
    #

    empty_pages = 0

    seen_urls = set()

    for page_number in range(1, 401):

        url = CDNLOGO_SPORTS_INDEX.format(
            page_number
        )

        try:

            response = get(
                url
            )

        except Exception as exc:

            print(
                f"  Page {page_number}: "
                f"download failed: {exc}"
            )

            empty_pages += 1

            if empty_pages >= 3:

                break

            continue

        parser = parse_html(
            response.text
        )

        page_count = 0

        # ----------------------------------------------------
        # CDNLogo page links
        # ----------------------------------------------------

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

            title = link.get(
                "text",
                ""
            ).strip()

            if not title:

                continue

            # ------------------------------------------------
            # Find the static.cdnlogo.com URL associated with
            # this logo in the raw HTML.
            # ------------------------------------------------

            image_url = None

            slug_match = re.search(
                r"/logo/([^/?#]+)",
                href,
                re.IGNORECASE
            )

            slug = None

            if slug_match:

                slug = slug_match.group(1)

                slug = re.sub(
                    r"_\d+\.html$",
                    "",
                    slug,
                    flags=re.IGNORECASE
                )

            if slug:

                image_pattern = re.compile(
                    r'https?:?//static\.cdnlogo\.com/'
                    r'[^"\']*'
                    + re.escape(slug)
                    + r'[^"\']*'
                    r'\.(?:svg|png)',
                    re.IGNORECASE
                )

                match = image_pattern.search(
                    response.text
                )

                if match:

                    image_url = html.unescape(
                        match.group(0)
                    )

                    if image_url.startswith(
                        "//"
                    ):

                        image_url = (
                            "https:"
                            + image_url
                        )

            # ------------------------------------------------
            # More general fallback.
            # ------------------------------------------------

            if not image_url:

                image_patterns = [
                    r'https?://static\.cdnlogo\.com/'
                    r'[^"\']+\.(?:svg|png)',

                    r'//static\.cdnlogo\.com/'
                    r'[^"\']+\.(?:svg|png)',
                ]

                for pattern in image_patterns:

                    matches = re.findall(
                        pattern,
                        response.text,
                        re.IGNORECASE
                    )

                    for match in matches:

                        match = html.unescape(
                            match
                        )

                        if match.startswith(
                            "//"
                        ):

                            match = (
                                "https:"
                                + match
                            )

                        if slug and clean_name(
                            slug
                        ) in clean_name(
                            match
                        ):

                            image_url = match

                            break

                    if image_url:

                        break

            if not image_url:

                continue

            key = (
                clean_name(title),
                href.lower()
            )

            if key in seen_urls:

                continue

            seen_urls.add(
                key
            )

            candidates.append(
                (
                    title,
                    href,
                    image_url
                )
            )

            page_count += 1

        print(
            f"  Page {page_number}: "
            f"{page_count} usable logos"
        )

        if page_count == 0:

            empty_pages += 1

        else:

            empty_pages = 0

        if empty_pages >= 3:

            break

        time.sleep(
            REQUEST_DELAY
        )

    CDNLOGO_INDEX_CACHE = candidates

    print()

    print(
        f"Collected {len(candidates)} "
        f"CDNLogo logo entries."
    )

    return candidates


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

    candidates = (
        collect_cdnlogo_sports_index()
    )

    best = choose_candidate(
        team_name,
        candidates
    )

    if not best:

        raise RuntimeError(
            "Could not find CDNLogo sports-index "
            f"result for: {team_name}"
        )

    score, title, page_url, image_url = best

    print(
        f"  Match: {title}"
    )

    print(
        f"  Score: {score:.3f}"
    )

    print(
        f"  Page: {page_url}"
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

    content_type = (
        response.headers.get(
            "Content-Type",
            ""
        ).lower()
    )

    # --------------------------------------------------------
    # SVG
    # --------------------------------------------------------

    if (
        ".svg" in image_url.lower()
        or "svg" in content_type
        or response.content.lstrip().startswith(
            b"<svg"
        )
    ):

        if cairosvg is None:

            raise RuntimeError(
                "CairoSVG is required to convert "
                f"SVG logo: {team_name}"
            )

        png_bytes = cairosvg.svg2png(
            bytestring=response.content
        )

        image = Image.open(
            io.BytesIO(
                png_bytes
            )
        )

    # --------------------------------------------------------
    # Raster
    # --------------------------------------------------------

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
# DISCOVER ALL TEAMS
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
# VERIFY SOURCES
#
# We verify that every team can be matched and downloaded
# before modifying any existing logo.
# ============================================================

def verify_sources(teams):

    print()

    print("=" * 70)
    print("VERIFYING CDNLOGO SOURCES")
    print("=" * 70)

    verified = 0

    for number, team in enumerate(
        teams,
        start=1
    ):

        print()

        print(
            f"[{number}/{len(teams)}] {team}"
        )

        image_url, page_url = find_team_source(
            team
        )

        # ----------------------------------------------------
        # Actually download the source now.
        # This means verification is not merely checking that
        # a page exists — it confirms the image can be fetched
        # and decoded.
        # ----------------------------------------------------

        image = download_logo(
            team
        )

        if (
            image.width <= 0
            or image.height <= 0
        ):

            raise RuntimeError(
                f"Downloaded invalid logo for: {team}"
            )

        verified += 1

        print(
            f"  Verified image: "
            f"{image.width}x{image.height}"
        )

    print()

    print(
        f"Verified {verified}/{len(teams)} "
        "team logos."
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
    # No existing files are touched until every team has a
    # downloadable, decodable CDNLogo image.
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
