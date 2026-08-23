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
# CDNLOGO COLLECTIONS
#
# CDNLogo's normal search page is not reliable for automated
# scraping. These collection pages provide another way to
# discover the actual CDNLogo team pages.
# ============================================================

COLLECTION_URLS = {
    "MLB": [
        "https://cdnlogo.com/logos-collection/mlb-teams",
        "https://cdnlogo.com/logos-vector/mlb",
        "https://cdnlogo.com/logos-vector/baseball",
        "https://cdnlogo.com/logos-vector/sports",
    ],

    "NBA": [
        "https://cdnlogo.com/logos-collection/nba-teams",
        "https://cdnlogo.com/logos-vector/nba",
        "https://cdnlogo.com/logos-vector/basketball",
        "https://cdnlogo.com/logos-vector/sports",
    ],

    "NFL": [
        "https://cdnlogo.com/logos-collection/nfl-teams",
        "https://cdnlogo.com/logos-vector/nfl",
        "https://cdnlogo.com/logos-vector/football",
        "https://cdnlogo.com/logos-vector/sports",
    ],

    "NHL": [
        "https://cdnlogo.com/logos-collection/nhl-teams",
        "https://cdnlogo.com/logos-vector/nhl",
        "https://cdnlogo.com/logos-vector/hockey",
        "https://cdnlogo.com/logos-vector/sports",
    ],
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
    "Arizona_Coyotes": "Arizona Coyotes",

    "Atlanta_Thrashers": "Winnipeg Jets",

    "Anaheim_Mighty_Ducks": "Anaheim Ducks",

    "New_York_Giants": "New York Giants",

    "Oakland_Raiders": "Las Vegas Raiders",
    "Las_Vegas_Raiders": "Las Vegas Raiders",

    "San_Diego_Chargers": "Los Angeles Chargers",
    "Los_Angeles_Chargers": "Los Angeles Chargers",

    "St_Louis_Rams": "Los Angeles Rams",
    "Los_Angeles_Rams": "Los Angeles Rams",

    "Tampa_Bay_Devil_Rays": "Tampa Bay Rays",

    "Florida_Marlins": "Miami Marlins",

    "Montreal_Expos": "Washington Nationals",

    "Seattle_Supersonics": "Oklahoma City Thunder",

    "New_Orleans_Hornets": "New Orleans Pelicans",

    "New_Orleans_Oklahoma_City_Hornets":
        "New Orleans Pelicans",

    "Vancouver_Grizzlies": "Memphis Grizzlies",

    "Minnesota_North_Stars": "Minnesota Wild",

    "Hartford_Whalers": "Carolina Hurricanes",

    "Quebec_Nordiques": "Colorado Avalanche",

    "Colorado_Rockies": "Colorado Avalanche",

    "Winnipeg_Thrashers": "Winnipeg Jets",

    "Atlanta_Hawks": "Atlanta Hawks",
}


# Additional textual aliases used when matching CDNLogo
# search/collection names to our canonical team names.

SEARCH_ALIASES = {
    "los angeles angels": [
        "los angeles angels",
        "los angeles angels of anaheim",
        "angels",
    ],

    "anaheim ducks": [
        "anaheim ducks",
        "ducks",
    ],

    "arizona diamondbacks": [
        "arizona diamondbacks",
        "arizona diamondbacks",
        "diamondbacks",
    ],

    "atlanta braves": [
        "atlanta braves",
        "braves",
    ],

    "baltimore orioles": [
        "baltimore orioles",
        "orioles",
    ],

    "boston red sox": [
        "boston red sox",
        "red sox",
    ],

    "chicago cubs": [
        "chicago cubs",
        "cubs",
    ],

    "chicago white sox": [
        "chicago white sox",
        "white sox",
    ],

    "cincinnati reds": [
        "cincinnati reds",
        "reds",
    ],

    "cleveland guardians": [
        "cleveland guardians",
        "guardians",
    ],

    "colorado rockies": [
        "colorado rockies",
        "rockies",
    ],

    "detroit tigers": [
        "detroit tigers",
        "tigers",
    ],

    "houston astros": [
        "houston astros",
        "astros",
    ],

    "kansas city royals": [
        "kansas city royals",
        "royals",
    ],

    "los angeles dodgers": [
        "los angeles dodgers",
        "dodgers",
    ],

    "miami marlins": [
        "miami marlins",
        "florida marlins",
        "marlins",
    ],

    "milwaukee brewers": [
        "milwaukee brewers",
        "brewers",
    ],

    "minnesota twins": [
        "minnesota twins",
        "twins",
    ],

    "new york mets": [
        "new york mets",
        "mets",
    ],

    "new york yankees": [
        "new york yankees",
        "yankees",
    ],

    "oakland athletics": [
        "oakland athletics",
        "oakland as",
        "athletics",
        "as",
    ],

    "philadelphia phillies": [
        "philadelphia phillies",
        "phillies",
    ],

    "pittsburgh pirates": [
        "pittsburgh pirates",
        "pirates",
    ],

    "san diego padres": [
        "san diego padres",
        "padres",
    ],

    "san francisco giants": [
        "san francisco giants",
        "giants",
    ],

    "seattle mariners": [
        "seattle mariners",
        "mariners",
    ],

    "st louis cardinals": [
        "st louis cardinals",
        "st. louis cardinals",
        "cardinals",
    ],

    "tampa bay rays": [
        "tampa bay rays",
        "tampa bay devil rays",
        "devil rays",
        "rays",
    ],

    "texas rangers": [
        "texas rangers",
        "rangers",
    ],

    "toronto blue jays": [
        "toronto blue jays",
        "blue jays",
    ],

    "washington nationals": [
        "washington nationals",
        "montreal expos",
        "nationals",
    ],

    "las vegas raiders": [
        "las vegas raiders",
        "oakland raiders",
        "raiders",
    ],

    "los angeles chargers": [
        "los angeles chargers",
        "san diego chargers",
        "chargers",
    ],

    "los angeles rams": [
        "los angeles rams",
        "st louis rams",
        "st. louis rams",
        "rams",
    ],

    "los angeles lakers": [
        "los angeles lakers",
        "lakers",
    ],

    "los angeles clippers": [
        "los angeles clippers",
        "clippers",
    ],

    "new orleans pelicans": [
        "new orleans pelicans",
        "new orleans hornets",
        "pelicans",
    ],

    "oklahoma city thunder": [
        "oklahoma city thunder",
        "seattle supersonics",
        "seattle supersonics",
        "thunder",
    ],

    "brooklyn nets": [
        "brooklyn nets",
        "new jersey nets",
        "nets",
    ],

    "memphis grizzlies": [
        "memphis grizzlies",
        "vancouver grizzlies",
        "grizzlies",
    ],

    "carolina hurricanes": [
        "carolina hurricanes",
        "hartford whalers",
        "hurricanes",
    ],

    "colorado avalanche": [
        "colorado avalanche",
        "quebec nordiques",
        "avalanche",
    ],

    "minnesota wild": [
        "minnesota wild",
        "minnesota north stars",
        "wild",
    ],

    "winnipeg jets": [
        "winnipeg jets",
        "atlanta thrashers",
        "jets",
    ],
}


def clean_name(value):
    """
    Convert filenames/team names into a normalized searchable name.
    """

    value = os.path.splitext(
        str(value)
    )[0]

    value = value.replace(
        "_",
        " "
    )

    value = value.replace(
        "-",
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

    value = value.strip().lower()

    return value


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


def normalized_search_name(raw):

    name = display_team_name(
        raw
    )

    return clean_name(
        name
    )


# ============================================================
# SIMPLE HTML PARSER
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

        attributes = dict(
            attrs
        )

        if tag.lower() == "a":

            self.current_link = {
                "href":
                    attributes.get(
                        "href"
                    ),

                "text": []
            }

            self.current_link_text = []

        elif tag.lower() == "img":

            self.images.append(
                attributes
            )

    def handle_data(
        self,
        data
    ):

        if self.current_link is not None:

            self.current_link_text.append(
                data
            )

    def handle_endtag(
        self,
        tag
    ):

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


def parse_html(
    response_text
):

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
# COLLECTION DISCOVERY
# ============================================================

COLLECTION_CACHE = {}


def collection_candidates(
    league
):
    """
    Crawl CDNLogo collection/vector pages and extract every
    CDNLogo logo page found there.

    This is used because CDNLogo's search page is not dependable
    for automated requests.
    """

    if league in COLLECTION_CACHE:

        return COLLECTION_CACHE[
            league
        ]

    candidates = []

    seen = set()

    urls = COLLECTION_URLS.get(
        league,
        []
    )

    for collection_url in urls:

        try:

            response = get(
                collection_url
            )

        except Exception as exc:

            print(
                f"  Collection unavailable: "
                f"{collection_url}"
            )

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
                collection_url,
                href
            )

            if (
                "cdnlogo.com" not in
                href.lower()
            ):

                continue

            if "/logo/" not in href:

                continue

            title = link.get(
                "text",
                ""
            ).strip()

            key = (
                title,
                href
            )

            if key in seen:

                continue

            seen.add(
                key
            )

            candidates.append(
                (
                    title,
                    href
                )
            )

        time.sleep(
            REQUEST_DELAY
        )

    COLLECTION_CACHE[
        league
    ] = candidates

    return candidates


# ============================================================
# CDNLOGO SEARCH
# ============================================================

def search_cdnlogo(
    team_name,
    league=None
):
    """
    Discover CDNLogo pages.

    First use CDNLogo's collection pages. Then try the normal
    search page as a secondary fallback.
    """

    candidates = []

    seen = set()

    # --------------------------------------------------------
    # COLLECTION SEARCH
    # --------------------------------------------------------

    if league:

        for title, href in collection_candidates(
            league
        ):

            key = (
                title,
                href
            )

            if key not in seen:

                seen.add(
                    key
                )

                candidates.append(
                    (
                        title,
                        href
                    )
                )

    # --------------------------------------------------------
    # NORMAL CDNLOGO SEARCH
    # --------------------------------------------------------

    query = quote(
        team_name
    )

    urls = [
        f"{CDNLOGO_BASE}/search?q={query}",
        f"{CDNLOGO_BASE}/?q={query}",
    ]

    for url in urls:

        try:

            response = get(
                url
            )

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

            title = link.get(
                "text",
                ""
            ).strip()

            key = (
                title,
                href
            )

            if key not in seen:

                seen.add(
                    key
                )

                candidates.append(
                    (
                        title,
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
# DIRECT CDNLOGO PAGE DISCOVERY
# ============================================================

def search_engine_fallback(
    team_name
):
    """
    Try likely CDNLogo slugs.

    CDNLogo assigns numeric IDs to pages, so the exact numeric
    ID cannot be reliably guessed. These attempts are therefore
    only a final fallback.
    """

    normalized = clean_name(
        team_name
    )

    slugs = [
        normalized.replace(
            " ",
            "-"
        ),

        normalized.replace(
            " ",
            "_"
        ),
    ]

    results = []

    for slug in slugs:

        urls = [
            f"{CDNLOGO_BASE}/logo/{slug}.html",
            f"{CDNLOGO_BASE}/logos/{slug}",
        ]

        for url in urls:

            try:

                response = get(
                    url
                )

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

def aliases_for_team(
    team_name
):

    wanted = clean_name(
        team_name
    )

    aliases = SEARCH_ALIASES.get(
        wanted
    )

    if aliases:

        return [
            clean_name(x)
            for x in aliases
        ]

    return [
        wanted
    ]


def score_candidate(
    team_name,
    candidate_name
):
    """
    Score a CDNLogo result against the requested team.

    Exact canonical and known aliases receive the strongest
    scores. This prevents "Anaheim Ducks" from accidentally
    becoming "Anaheim Mighty Ducks" simply because it contains
    similar words.
    """

    wanted = clean_name(
        team_name
    )

    candidate = clean_name(
        candidate_name
    )

    if not candidate:

        return 0.0

    aliases = aliases_for_team(
        team_name
    )

    # --------------------------------------------------------
    # Exact canonical/alias match
    # --------------------------------------------------------

    if candidate in aliases:

        return 1.0

    # --------------------------------------------------------
    # Candidate contains a canonical alias
    # --------------------------------------------------------

    for alias in aliases:

        if (
            len(alias) >= 6
            and alias in candidate
        ):

            return 0.96

    # --------------------------------------------------------
    # Candidate is contained by an alias
    # --------------------------------------------------------

    for alias in aliases:

        if (
            len(candidate) >= 6
            and candidate in alias
        ):

            return 0.94

    # --------------------------------------------------------
    # Token overlap
    # --------------------------------------------------------

    wanted_tokens = set(
        wanted.split()
    )

    candidate_tokens = set(
        candidate.split()
    )

    if wanted_tokens:

        overlap = (
            len(
                wanted_tokens &
                candidate_tokens
            )
            /
            len(
                wanted_tokens
            )
        )

        if overlap == 1.0:

            return 0.93

    # --------------------------------------------------------
    # Fuzzy match
    # --------------------------------------------------------

    best_ratio = SequenceMatcher(
        None,
        wanted,
        candidate
    ).ratio()

    for alias in aliases:

        best_ratio = max(
            best_ratio,
            SequenceMatcher(
                None,
                alias,
                candidate
            ).ratio()
        )

    return best_ratio


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

    # --------------------------------------------------------
    # Prefer exact/very strong matches.
    # --------------------------------------------------------

    for item in scored:

        if item[0] >= 0.95:

            return item

    best = scored[0]

    # Do not accept wildly unrelated results.
    if best[0] < 0.72:

        return None

    return best


# ============================================================
# EXTRACT CDN IMAGE FROM LOGO PAGE
# ============================================================

def extract_image_from_page(
    page_url,
    team_name
):
    """
    Extract the CDNLogo-hosted image.

    PNG is preferred, but SVG is accepted and Pillow will
    convert it if the installed Pillow build supports SVG
    through the available decoder. If not, the raw SVG is
    converted using the embedded XML/vector fallback below.
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

            if (
                "static.cdnlogo.com"
                in value
            ):

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
    # RELATIVE REFERENCES
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

            decoded = html.unescape(
                match
            )

            absolute = urljoin(
                page_url,
                decoded
            )

            if (
                "static.cdnlogo.com"
                in absolute
            ):

                if absolute not in candidates:

                    candidates.append(
                        absolute
                    )

    # --------------------------------------------------------
    # PREFER PNG
    # --------------------------------------------------------

    pngs = [
        x
        for x in candidates
        if ".png" in x.lower()
        and "thumb" not in x.lower()
    ]

    if pngs:

        return pngs[0]

    pngs = [
        x
        for x in candidates
        if ".png" in x.lower()
    ]

    if pngs:

        return pngs[0]

    # --------------------------------------------------------
    # SVG
    # --------------------------------------------------------

    svgs = [
        x
        for x in candidates
        if ".svg" in x.lower()
        and "thumb" not in x.lower()
    ]

    if svgs:

        return svgs[0]

    svgs = [
        x
        for x in candidates
        if ".svg" in x.lower()
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


def find_team_source(
    team_name,
    league
):

    cache_key = (
        league,
        clean_name(
            team_name
        )
    )

    if cache_key in SOURCE_CACHE:

        return SOURCE_CACHE[
            cache_key
        ]

    print()

    print(
        f"Finding CDNLogo source: "
        f"{team_name}"
    )

    # --------------------------------------------------------
    # Search collection pages + normal search.
    # --------------------------------------------------------

    candidates = search_cdnlogo(
        team_name,
        league
    )

    best = choose_candidate(
        team_name,
        candidates
    )

    # --------------------------------------------------------
    # Direct slug fallback.
    # --------------------------------------------------------

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

    image_url = extract_image_from_page(
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


def download_logo(
    team_name,
    league
):

    key = (
        league,
        clean_name(
            team_name
        )
    )

    if key in IMAGE_CACHE:

        return IMAGE_CACHE[
            key
        ].copy()

    image_url, page_url = find_team_source(
        team_name,
        league
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
    # First attempt: Pillow.
    #
    # This works for PNG and other raster formats.
    # --------------------------------------------------------

    try:

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

    except Exception:
        pass

    # --------------------------------------------------------
    # SVG fallback.
    #
    # CDNLogo commonly serves SVG as the source. If Pillow
    # cannot decode it directly, try an optional cairosvg
    # installation if present.
    # --------------------------------------------------------

    if (
        "svg" in content_type
        or image_url.lower().endswith(
            ".svg"
        )
        or b"<svg" in response.content[:1000].lower()
    ):

        try:

            import cairosvg

            png_bytes = cairosvg.svg2png(
                bytestring=response.content
            )

            image = Image.open(
                io.BytesIO(
                    png_bytes
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

        except ImportError:

            raise RuntimeError(
                "CDNLogo returned an SVG and "
                "Pillow cannot decode SVG directly. "
                "Install cairosvg or allow the workflow "
                "to install it."
            )

        except Exception as exc:

            raise RuntimeError(
                f"Could not convert CDNLogo SVG "
                f"for {team_name}: {exc}"
            )

    raise RuntimeError(
        f"Could not decode CDNLogo image for "
        f"{team_name}: {image_url}"
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
        (
            width,
            height
        ),
        Image.Resampling.LANCZOS
    )


# ============================================================
# EXISTING IMAGE DIMENSIONS
# ============================================================

def existing_dimensions(
    path
):

    with Image.open(
        path
    ) as image:

        return image.size


# ============================================================
# SOLO LOGO
# ============================================================

def rebuild_solo(
    path,
    team,
    league
):

    width, height = existing_dimensions(
        path
    )

    source = download_logo(
        team,
        league
    )

    logo = fit_logo(
        source,
        int(
            width * 0.90
        ),
        int(
            height * 0.90
        )
    )

    canvas = Image.new(
        "RGBA",
        (
            width,
            height
        ),
        (
            0,
            0,
            0,
            0
        )
    )

    x = (
        width -
        logo.width
    ) // 2

    y = (
        height -
        logo.height
    ) // 2

    canvas.alpha_composite(
        logo,
        (
            x,
            y
        )
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
    away_team,
    league
):

    width, height = existing_dimensions(
        path
    )

    # --------------------------------------------------------
    # The first team in the filename is treated as HOME.
    # The second team is treated as AWAY.
    #
    # Example:
    #
    # Arizona_Cardinals_vs_Tennessee_Titans.png
    #
    # Arizona Cardinals = LEFT / HOME
    # Tennessee Titans   = RIGHT / AWAY
    # --------------------------------------------------------

    home_source = download_logo(
        home_team,
        league
    )

    away_source = download_logo(
        away_team,
        league
    )

    half_width = width // 2

    home = fit_logo(
        home_source,
        int(
            half_width * 0.88
        ),
        int(
            height * 0.88
        )
    )

    away = fit_logo(
        away_source,
        int(
            half_width * 0.88
        ),
        int(
            height * 0.88
        )
    )

    canvas = Image.new(
        "RGBA",
        (
            width,
            height
        ),
        (
            0,
            0,
            0,
            0
        )
    )

    # --------------------------------------------------------
    # HOME / LEFT
    # --------------------------------------------------------

    home_x = (
        half_width -
        home.width
    ) // 2

    home_y = (
        height -
        home.height
    ) // 2

    # --------------------------------------------------------
    # AWAY / RIGHT
    # --------------------------------------------------------

    away_x = (
        half_width +
        (
            (
                half_width -
                away.width
            )
            // 2
        )
    )

    away_y = (
        height -
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

        league_dir = (
            ROOT /
            league
        )

        if not league_dir.is_dir():

            continue

        for path in sorted(
            league_dir.rglob(
                "*.png"
            )
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

        home, away = filename.split(
            "_vs_",
            1
        )

        return [
            display_team_name(
                home
            ),
            display_team_name(
                away
            )
        ]

    return [
        display_team_name(
            filename
        )
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

            key = (
                league,
                clean_name(
                    team
                )
            )

            teams[key] = team

    return sorted(
        teams.items(),
        key=lambda item: (
            item[0][0],
            clean_name(
                item[1]
            )
        )
    )


# ============================================================
# VERIFY ALL SOURCES FIRST
#
# IMPORTANT:
# We do NOT overwrite the library until every team has a
# successfully discovered CDNLogo source.
# ============================================================

def verify_sources(
    teams
):

    print()

    print("=" * 70)
    print(
        "VERIFYING CDNLOGO SOURCES"
    )
    print("=" * 70)

    for number, item in enumerate(
        teams,
        start=1
    ):

        (
            league,
            team
        ) = item

        print()

        print(
            f"[{number}/{len(teams)}] "
            f"{league}: {team}"
        )

        find_team_source(
            team,
            league
        )

    print()

    print(
        f"Verified {len(teams)} "
        f"team sources."
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

                print(
                    f"  TEAM: {teams[0]}"
                )

                rebuild_solo(
                    path,
                    teams[0],
                    league
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
                    teams[1],
                    league
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
    print(
        "CDNLOGO SPORTS LOGO LIBRARY REBUILDER"
    )
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
        f"Discovered {len(teams)} "
        f"unique league/team combinations."
    )

    print()

    print(
        "Leagues:"
    )

    for league in sorted(
        LEAGUES
    ):

        directory = (
            ROOT /
            league
        )

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
        print(
            "ABORTED"
        )
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
    print(
        "REBUILDING EXISTING LOGO LIBRARY"
    )
    print("=" * 70)

    total, replaced, failed = rebuild_library()

    print()

    print("=" * 70)
    print(
        "FINISHED"
    )
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
