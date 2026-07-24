#!/usr/bin/env python3

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit, urlunsplit

import requests


# ---------------------------------------------------------------------------
# Repository paths
# ---------------------------------------------------------------------------

REPOSITORY_ROOT = Path(
    os.environ.get(
        "GITHUB_WORKSPACE",
        str(Path(__file__).resolve().parents[2]),
    )
).resolve()

OUTPUT_DIRECTORY = REPOSITORY_ROOT / "filtered-provider"
CATEGORY_DIRECTORY = OUTPUT_DIRECTORY / "categories"

RAW_LIVE_FILE = CATEGORY_DIRECTORY / "live-categories.raw.json"
RAW_VOD_FILE = CATEGORY_DIRECTORY / "vod-categories.raw.json"
RAW_SERIES_FILE = CATEGORY_DIRECTORY / "series-categories.raw.json"

FILTERED_LIVE_FILE = CATEGORY_DIRECTORY / "live-categories.json"
FILTERED_VOD_FILE = CATEGORY_DIRECTORY / "vod-categories.json"
FILTERED_SERIES_FILE = CATEGORY_DIRECTORY / "series-categories.json"

SUMMARY_FILE = CATEGORY_DIRECTORY / "category-summary.json"


# ---------------------------------------------------------------------------
# Filtering rules
# ---------------------------------------------------------------------------

# Live categories are retained when their original provider name begins
# with one of these prefixes.
LIVE_KEEP_PREFIXES = (
    "US|",
    "CA|",
    "UK|",
    "AU|",
    "NZ|",
    "IE|",
)


# Movie categories are retained when:
# 1. Their name begins with EN -
# 2. Their name does not identify a foreign country or language.
VOD_ENGLISH_PREFIXES = (
    "EN -",
)


# Series categories are retained when:
# 1. Their name begins with ENGLISH
# 2. Their name does not identify a foreign country or language.
SERIES_ENGLISH_PREFIXES = (
    "ENGLISH",
)


# These prefixes identify categories that should be excluded from Movies
# and Series unless they match the explicit English rules above.
FOREIGN_PREFIXES = (
    "AF -",
    "AFRICA",
    "AL -",
    "ALBANIA",
    "AR -",
    "ARABIC",
    "BE -",
    "BELGIUM",
    "BG -",
    "BN -",
    "BR -",
    "BULGARIA",
    "BULGARIYA",
    "CHINA",
    "CN -",
    "DANSK",
    "DANSKE",
    "DENMARK",
    "DE -",
    "DUTCH",
    "ES -",
    "ESPAÑA",
    "EX -",
    "FI -",
    "FINLAND",
    "FR -",
    "FRANCE",
    "FRENCH",
    "GERMANY",
    "GERMAN",
    "GR -",
    "GREECE",
    "GREEK",
    "HEBREW",
    "HINDI",
    "HU -",
    "HUNGARY",
    "IL -",
    "IN -",
    "INDIA",
    "INDIAN",
    "IR -",
    "ITALY",
    "ITALIAN",
    "IT -",
    "JAPAN",
    "JAPANESE",
    "JP -",
    "KOREA",
    "KOREAN",
    "KU -",
    "KURDISH",
    "LA -",
    "LATINO",
    "MALTA",
    "MT -",
    "NETHERLANDS",
    "NL -",
    "NORDIC",
    "NORGE",
    "NORSK",
    "PAKISTAN",
    "PERSIAN",
    "PH -",
    "PHILIPPINES",
    "PK -",
    "PL -",
    "POLISH",
    "POLSKA",
    "PORTUGAL",
    "PORTUGUESE",
    "PT -",
    "PT/BR",
    "QC -",
    "QUÉBEC",
    "RO -",
    "ROMANIA",
    "ROMANIAN",
    "RU -",
    "RUSSIAN",
    "RUSSAIN",
    "SO -",
    "SOMALIA",
    "SPANISH",
    "SUOMEN",
    "SUOMI",
    "SVENSK",
    "SVENSKA",
    "SWEDEN",
    "SWEDISH",
    "TR -",
    "TURKEY",
    "TURKISH",
    "TURKSIH",
    "VIAPLAY ÍSLANDS",
    "ÍSLANDS",
)


# Detect names beginning with characters commonly used by foreign-language
# category names.
FOREIGN_SCRIPT_RANGES = (
    ("\u0370", "\u03ff"),  # Greek
    ("\u0400", "\u04ff"),  # Cyrillic
    ("\u0590", "\u05ff"),  # Hebrew
    ("\u0600", "\u06ff"),  # Arabic
    ("\u0750", "\u077f"),  # Arabic Supplement
    ("\u08a0", "\u08ff"),  # Arabic Extended
    ("\u3040", "\u30ff"),  # Japanese
    ("\u3400", "\u4dbf"),  # CJK Extension A
    ("\u4e00", "\u9fff"),  # Chinese
    ("\uac00", "\ud7af"),  # Korean Hangul
)


# ---------------------------------------------------------------------------
# General helpers
# ---------------------------------------------------------------------------

def required_environment_variable(name: str) -> str:
    value = os.environ.get(name, "").strip()

    if not value:
        raise RuntimeError(
            f"Missing required environment variable: {name}"
        )

    return value


def normalize_provider_base_url(value: str) -> str:
    value = value.strip()

    if not value.startswith(("http://", "https://")):
        value = f"http://{value}"

    parsed = urlsplit(value)

    if not parsed.netloc:
        raise ValueError(
            f"Invalid XTREAM_URL: {value}"
        )

    path = parsed.path.rstrip("/")

    known_endpoints = (
        "/player_api.php",
        "/get.php",
        "/xmltv.php",
    )

    lowered_path = path.casefold()

    for endpoint in known_endpoints:
        if lowered_path.endswith(endpoint):
            path = path[: -len(endpoint)]
            break

    return urlunsplit(
        (
            parsed.scheme,
            parsed.netloc,
            path.rstrip("/"),
            "",
            "",
        )
    )


def normalize_for_comparison(value: str) -> str:
    return value.strip().casefold()


def starts_with_any(
    value: str,
    prefixes: tuple[str, ...],
) -> bool:
    normalized_value = normalize_for_comparison(value)

    return any(
        normalized_value.startswith(
            normalize_for_comparison(prefix)
        )
        for prefix in prefixes
    )


def begins_with_foreign_script(value: str) -> bool:
    stripped = value.lstrip()

    if not stripped:
        return False

    first_character = stripped[0]

    return any(
        start <= first_character <= end
        for start, end in FOREIGN_SCRIPT_RANGES
    )


def category_name(category: dict[str, Any]) -> str:
    return str(
        category.get("category_name", "")
    ).strip()


def category_id(category: dict[str, Any]) -> str:
    return str(
        category.get("category_id", "")
    ).strip()


def is_foreign_category(name: str) -> bool:
    if begins_with_foreign_script(name):
        return True

    return starts_with_any(
        name,
        FOREIGN_PREFIXES,
    )


# ---------------------------------------------------------------------------
# Category rules
# ---------------------------------------------------------------------------

def keep_live_category(
    category: dict[str, Any],
) -> bool:
    name = category_name(category)

    return starts_with_any(
        name,
        LIVE_KEEP_PREFIXES,
    )


def keep_vod_category(
    category: dict[str, Any],
) -> bool:
    name = category_name(category)

    if starts_with_any(
        name,
        VOD_ENGLISH_PREFIXES,
    ):
        return True

    return not is_foreign_category(name)


def keep_series_category(
    category: dict[str, Any],
) -> bool:
    name = category_name(category)

    if starts_with_any(
        name,
        SERIES_ENGLISH_PREFIXES,
    ):
        return True

    return not is_foreign_category(name)


# ---------------------------------------------------------------------------
# Xtream API
# ---------------------------------------------------------------------------

def create_session() -> requests.Session:
    session = requests.Session()

    session.headers.update(
        {
            "User-Agent": (
                "Mozilla/5.0 "
                "(Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 "
                "(KHTML, like Gecko) "
                "Chrome/150.0.0.0 Safari/537.36"
            ),
            "Accept": "application/json,text/plain,*/*",
            "Connection": "close",
        }
    )

    return session


def request_xtream_action(
    session: requests.Session,
    base_url: str,
    username: str,
    password: str,
    action: str,
) -> list[dict[str, Any]]:
    endpoint = f"{base_url}/player_api.php"

    print(f"Downloading {action}...")

    response = session.get(
        endpoint,
        params={
            "username": username,
            "password": password,
            "action": action,
        },
        timeout=(30, 300),
    )

    print(
        f"  HTTP status: {response.status_code}"
    )
    print(
        f"  Downloaded bytes: {len(response.content):,}"
    )

    response.raise_for_status()

    if not response.content:
        raise RuntimeError(
            f"{action} returned an empty response."
        )

    try:
        result = response.json()
    except ValueError as error:
        preview = response.text[:500]

        raise RuntimeError(
            f"{action} did not return valid JSON. "
            f"Response preview: {preview!r}"
        ) from error

    if not isinstance(result, list):
        raise RuntimeError(
            f"{action} returned {type(result).__name__} "
            "instead of a category list."
        )

    cleaned_result: list[dict[str, Any]] = []

    for item in result:
        if not isinstance(item, dict):
            continue

        if not category_id(item):
            continue

        if not category_name(item):
            continue

        cleaned_result.append(item)

    print(
        f"  Valid categories: {len(cleaned_result):,}"
    )

    return cleaned_result


# ---------------------------------------------------------------------------
# File output
# ---------------------------------------------------------------------------

def write_json(
    path: Path,
    value: Any,
) -> None:
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    temporary_path = path.with_suffix(
        path.suffix + ".tmp"
    )

    with temporary_path.open(
        "w",
        encoding="utf-8",
        newline="\n",
    ) as output_file:
        json.dump(
            value,
            output_file,
            ensure_ascii=False,
            indent=2,
        )

        output_file.write("\n")

    temporary_path.replace(path)


def print_category_results(
    label: str,
    raw_categories: list[dict[str, Any]],
    filtered_categories: list[dict[str, Any]],
) -> None:
    print()
    print(f"{label} results:")
    print(
        f"  Provider categories: {len(raw_categories):,}"
    )
    print(
        f"  Kept categories:     {len(filtered_categories):,}"
    )
    print(
        f"  Excluded categories: "
        f"{len(raw_categories) - len(filtered_categories):,}"
    )

    print("  Kept names:")

    for category in filtered_categories:
        print(
            f"    [{category_id(category)}] "
            f"{category_name(category)}"
        )


# ---------------------------------------------------------------------------
# Main build
# ---------------------------------------------------------------------------

def build_filtered_categories() -> None:
    xtream_url = required_environment_variable(
        "XTREAM_URL"
    )
    username = required_environment_variable(
        "XTREAM_USERNAME"
    )
    password = required_environment_variable(
        "XTREAM_PASSWORD"
    )

    base_url = normalize_provider_base_url(
        xtream_url
    )

    print(
        f"Provider base URL: {base_url}"
    )
    print()

    session = create_session()

    live_categories = request_xtream_action(
        session=session,
        base_url=base_url,
        username=username,
        password=password,
        action="get_live_categories",
    )

    vod_categories = request_xtream_action(
        session=session,
        base_url=base_url,
        username=username,
        password=password,
        action="get_vod_categories",
    )

    series_categories = request_xtream_action(
        session=session,
        base_url=base_url,
        username=username,
        password=password,
        action="get_series_categories",
    )

    filtered_live_categories = [
        category
        for category in live_categories
        if keep_live_category(category)
    ]

    filtered_vod_categories = [
        category
        for category in vod_categories
        if keep_vod_category(category)
    ]

    filtered_series_categories = [
        category
        for category in series_categories
        if keep_series_category(category)
    ]

    write_json(
        RAW_LIVE_FILE,
        live_categories,
    )

    write_json(
        RAW_VOD_FILE,
        vod_categories,
    )

    write_json(
        RAW_SERIES_FILE,
        series_categories,
    )

    write_json(
        FILTERED_LIVE_FILE,
        filtered_live_categories,
    )

    write_json(
        FILTERED_VOD_FILE,
        filtered_vod_categories,
    )

    write_json(
        FILTERED_SERIES_FILE,
        filtered_series_categories,
    )

    summary = {
        "live": {
            "provider_categories": len(
                live_categories
            ),
            "kept_categories": len(
                filtered_live_categories
            ),
            "excluded_categories": (
                len(live_categories)
                - len(filtered_live_categories)
            ),
        },
        "vod": {
            "provider_categories": len(
                vod_categories
            ),
            "kept_categories": len(
                filtered_vod_categories
            ),
            "excluded_categories": (
                len(vod_categories)
                - len(filtered_vod_categories)
            ),
        },
        "series": {
            "provider_categories": len(
                series_categories
            ),
            "kept_categories": len(
                filtered_series_categories
            ),
            "excluded_categories": (
                len(series_categories)
                - len(filtered_series_categories)
            ),
        },
    }

    write_json(
        SUMMARY_FILE,
        summary,
    )

    print_category_results(
        "Live",
        live_categories,
        filtered_live_categories,
    )

    print_category_results(
        "Movies",
        vod_categories,
        filtered_vod_categories,
    )

    print_category_results(
        "Series",
        series_categories,
        filtered_series_categories,
    )

    print()
    print(
        "Filtered category files created successfully."
    )
    print(
        f"Output directory: "
        f"{CATEGORY_DIRECTORY.relative_to(REPOSITORY_ROOT)}"
    )


def main() -> int:
    try:
        build_filtered_categories()
        return 0

    except requests.HTTPError as error:
        status_code = (
            error.response.status_code
            if error.response is not None
            else "unknown"
        )

        print(
            f"Provider HTTP error: {status_code}",
            file=sys.stderr,
        )
        return 1

    except requests.RequestException as error:
        print(
            f"Provider connection failed: {error}",
            file=sys.stderr,
        )
        return 1

    except Exception as error:
        print(
            f"Filtered category build failed: {error}",
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
