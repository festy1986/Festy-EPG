#!/usr/bin/env python3

from __future__ import annotations

import gzip
import json
import os
import re
import sys
import unicodedata
from pathlib import Path
from typing import Any, Callable
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

CONFIG_DIRECTORY = REPOSITORY_ROOT / "config/provider"
OUTPUT_DIRECTORY = REPOSITORY_ROOT / "filtered-provider"
CATEGORY_DIRECTORY = OUTPUT_DIRECTORY / "categories"
REPORT_DIRECTORY = OUTPUT_DIRECTORY / "reports"
STREAM_DIRECTORY = OUTPUT_DIRECTORY / "streams"

LIVE_ALLOWLIST_FILE = CONFIG_DIRECTORY / "live_allowlist.txt"
MOVIE_ALLOWLIST_FILE = CONFIG_DIRECTORY / "movie_allowlist.txt"
SERIES_ALLOWLIST_FILE = CONFIG_DIRECTORY / "series_allowlist.txt"

RAW_LIVE_CATEGORY_FILE = CATEGORY_DIRECTORY / "live-categories.raw.json"
RAW_VOD_CATEGORY_FILE = CATEGORY_DIRECTORY / "vod-categories.raw.json"
RAW_SERIES_CATEGORY_FILE = CATEGORY_DIRECTORY / "series-categories.raw.json"

FILTERED_LIVE_CATEGORY_FILE = CATEGORY_DIRECTORY / "live-categories.json"
FILTERED_VOD_CATEGORY_FILE = CATEGORY_DIRECTORY / "vod-categories.json"
FILTERED_SERIES_CATEGORY_FILE = CATEGORY_DIRECTORY / "series-categories.json"

CATEGORY_SUMMARY_FILE = OUTPUT_DIRECTORY / "category-summary.json"
STREAM_SUMMARY_FILE = OUTPUT_DIRECTORY / "stream-summary.json"

FILTERED_LIVE_STREAM_FILE = STREAM_DIRECTORY / "live-streams.json.gz"
FILTERED_VOD_STREAM_FILE = STREAM_DIRECTORY / "vod-streams.json.gz"
FILTERED_SERIES_FILE = STREAM_DIRECTORY / "series.json.gz"

KEPT_LIVE_REPORT = REPORT_DIRECTORY / "kept-live.txt"
KEPT_MOVIE_REPORT = REPORT_DIRECTORY / "kept-movies.txt"
KEPT_SERIES_REPORT = REPORT_DIRECTORY / "kept-series.txt"

EXCLUDED_LIVE_REPORT = REPORT_DIRECTORY / "excluded-live.txt"
EXCLUDED_MOVIE_REPORT = REPORT_DIRECTORY / "excluded-movies.txt"
EXCLUDED_SERIES_REPORT = REPORT_DIRECTORY / "excluded-series.txt"


# ---------------------------------------------------------------------------
# Foreign-language and foreign-region detection
# ---------------------------------------------------------------------------

FOREIGN_TERMS = (
    "AFRICA",
    "ALBANIA",
    "ALBANIAN",
    "ARAB",
    "ARABIA",
    "ARABIC",
    "ASIA",
    "BANGLA",
    "BELGIUM",
    "BOSNIA",
    "BRAZIL",
    "BULGARIA",
    "BULGARIAN",
    "CHINA",
    "CHINESE",
    "CROATIA",
    "CROATIAN",
    "CZECH",
    "DANISH",
    "DENMARK",
    "DUTCH",
    "ESPANOL",
    "FINLAND",
    "FINNISH",
    "FRANCE",
    "FRENCH",
    "GERMAN",
    "GERMANY",
    "GREECE",
    "GREEK",
    "HEBREW",
    "HINDI",
    "HUNGARY",
    "HUNGARIAN",
    "ICELAND",
    "ICELANDIC",
    "INDIA",
    "INDIAN",
    "INDONESIA",
    "INDONESIAN",
    "IRAN",
    "IRANIAN",
    "ISRAEL",
    "ITALIAN",
    "ITALY",
    "JAPAN",
    "JAPANESE",
    "KOREA",
    "KOREAN",
    "KURDISH",
    "LATIN",
    "LATINO",
    "MALAY",
    "MALAYSIA",
    "MENA",
    "MEXICO",
    "NETHERLANDS",
    "NORDIC",
    "NORWAY",
    "NORWEGIAN",
    "PAKISTAN",
    "PERSIAN",
    "PHILIPPINES",
    "POLAND",
    "POLISH",
    "POLSKA",
    "PORTUGAL",
    "PORTUGUESE",
    "QUEBEC",
    "ROMANIA",
    "ROMANIAN",
    "RUSSIA",
    "RUSSIAN",
    "SERBIA",
    "SERBIAN",
    "SOMALIA",
    "SOMALI",
    "SOUTH AFRICA",
    "SPANISH",
    "SWEDEN",
    "SWEDISH",
    "THAI",
    "THAILAND",
    "TURKEY",
    "TURKISH",
    "UKRAINE",
    "UKRAINIAN",
    "VIETNAM",
    "VIETNAMESE",
)

FOREIGN_SHORT_TOKENS = (
    "AR",
    "BG",
    "BR",
    "CN",
    "CZ",
    "DE",
    "DK",
    "ES",
    "FI",
    "FR",
    "GR",
    "HU",
    "IL",
    "IN",
    "IR",
    "IT",
    "JP",
    "KR",
    "NL",
    "NO",
    "PK",
    "PL",
    "PT",
    "RO",
    "RU",
    "SE",
    "TR",
)

FOREIGN_SCRIPT_RANGES = (
    ("\u0370", "\u03ff"),
    ("\u0400", "\u052f"),
    ("\u0590", "\u05ff"),
    ("\u0600", "\u06ff"),
    ("\u0750", "\u077f"),
    ("\u08a0", "\u08ff"),
    ("\u0900", "\u097f"),
    ("\u0980", "\u09ff"),
    ("\u0e00", "\u0e7f"),
    ("\u3040", "\u30ff"),
    ("\u3400", "\u4dbf"),
    ("\u4e00", "\u9fff"),
    ("\uac00", "\ud7af"),
)


# ---------------------------------------------------------------------------
# Basic helpers
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

    for endpoint in (
        "/player_api.php",
        "/get.php",
        "/xmltv.php",
    ):
        if path.casefold().endswith(endpoint):
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


def category_name(category: dict[str, Any]) -> str:
    return str(
        category.get("category_name", "")
    ).strip()


def category_id(category: dict[str, Any]) -> str:
    return str(
        category.get("category_id", "")
    ).strip()


def normalize_text(value: str) -> str:
    value = unicodedata.normalize("NFKD", value)

    cleaned_characters: list[str] = []

    for character in value:
        character_category = unicodedata.category(character)

        if character_category.startswith("M"):
            continue

        if character.isascii():
            cleaned_characters.append(character)
            continue

        if character.isalnum():
            cleaned_characters.append(character)
            continue

        cleaned_characters.append(" ")

    normalized = "".join(cleaned_characters).upper()
    normalized = re.sub(r"[^A-Z0-9+|&/-]+", " ", normalized)
    normalized = re.sub(r"\s+", " ", normalized)

    return normalized.strip()


def normalized_tokens(value: str) -> set[str]:
    return set(
        re.findall(
            r"[A-Z0-9]+",
            normalize_text(value),
        )
    )


def contains_foreign_script(value: str) -> bool:
    for character in value:
        for start, end in FOREIGN_SCRIPT_RANGES:
            if start <= character <= end:
                return True

    return False


def is_foreign_category(value: str) -> bool:
    if contains_foreign_script(value):
        return True

    normalized = normalize_text(value)
    tokens = normalized_tokens(value)

    for term in FOREIGN_TERMS:
        if normalize_text(term) in normalized:
            return True

    for token in FOREIGN_SHORT_TOKENS:
        if token in tokens:
            return True

    return False


def load_allowlist(path: Path) -> list[str]:
    if not path.exists():
        raise FileNotFoundError(
            f"Missing allowlist file: "
            f"{path.relative_to(REPOSITORY_ROOT)}"
        )

    values: list[str] = []

    for raw_line in path.read_text(
        encoding="utf-8"
    ).splitlines():
        line = raw_line.strip()

        if not line or line.startswith("#"):
            continue

        normalized = normalize_text(line)

        if normalized:
            values.append(normalized)

    if not values:
        raise RuntimeError(
            f"Allowlist is empty: "
            f"{path.relative_to(REPOSITORY_ROOT)}"
        )

    return values


# ---------------------------------------------------------------------------
# Category matching
# ---------------------------------------------------------------------------

def matches_live_allowlist(
    name: str,
    allowlist: list[str],
) -> bool:
    normalized_name = normalize_text(name)

    return any(
        normalized_name.startswith(prefix)
        for prefix in allowlist
    )


def matches_content_allowlist(
    name: str,
    allowlist: list[str],
) -> bool:
    if is_foreign_category(name):
        return False

    normalized_name = normalize_text(name)

    return any(
        phrase in normalized_name
        for phrase in allowlist
    )


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


def request_xtream_list(
    session: requests.Session,
    base_url: str,
    username: str,
    password: str,
    action: str,
    timeout_seconds: int = 900,
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
        timeout=(30, timeout_seconds),
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
            "instead of a list."
        )

    cleaned_result = [
        item
        for item in result
        if isinstance(item, dict)
    ]

    print(
        f"  Valid items: {len(cleaned_result):,}"
    )

    return cleaned_result


# ---------------------------------------------------------------------------
# Filtering
# ---------------------------------------------------------------------------

def split_categories(
    categories: list[dict[str, Any]],
    predicate: Callable[[str], bool],
) -> tuple[
    list[dict[str, Any]],
    list[dict[str, Any]],
]:
    kept: list[dict[str, Any]] = []
    excluded: list[dict[str, Any]] = []

    for category in categories:
        if predicate(category_name(category)):
            kept.append(category)
        else:
            excluded.append(category)

    return kept, excluded


def category_id_set(
    categories: list[dict[str, Any]],
) -> set[str]:
    return {
        category_id(category)
        for category in categories
        if category_id(category)
    }


def filter_streams_by_category(
    items: list[dict[str, Any]],
    allowed_category_ids: set[str],
) -> list[dict[str, Any]]:
    return [
        item
        for item in items
        if str(item.get("category_id", "")).strip()
        in allowed_category_ids
    ]


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------

def write_json(path: Path, value: Any) -> None:
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


def write_json_gzip(path: Path, value: Any) -> None:
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    temporary_path = path.with_suffix(
        path.suffix + ".tmp"
    )

    with gzip.open(
        temporary_path,
        "wt",
        encoding="utf-8",
        newline="\n",
        compresslevel=9,
    ) as output_file:
        json.dump(
            value,
            output_file,
            ensure_ascii=False,
            separators=(",", ":"),
        )
        output_file.write("\n")

    temporary_path.replace(path)


def write_category_report(
    path: Path,
    categories: list[dict[str, Any]],
) -> None:
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    sorted_categories = sorted(
        categories,
        key=lambda item: (
            normalize_text(category_name(item)),
            category_id(item),
        ),
    )

    lines = [
        f"{category_id(item)} | {category_name(item)}"
        for item in sorted_categories
    ]

    text = "\n".join(lines)

    if text:
        text += "\n"

    path.write_text(
        text,
        encoding="utf-8",
        newline="\n",
    )


def file_size(path: Path) -> int:
    if not path.exists():
        return 0

    return path.stat().st_size


# ---------------------------------------------------------------------------
# Main build
# ---------------------------------------------------------------------------

def build_filtered_provider() -> None:
    # Create every output directory before downloading anything.
    # This also makes the expected repository layout explicit in GitHub Actions.
    for directory in (
        OUTPUT_DIRECTORY,
        CATEGORY_DIRECTORY,
        REPORT_DIRECTORY,
        STREAM_DIRECTORY,
    ):
        directory.mkdir(parents=True, exist_ok=True)

    xtream_url = required_environment_variable(
        "XTREAM_URL"
    )
    username = required_environment_variable(
        "XTREAM_USERNAME"
    )
    password = required_environment_variable(
        "XTREAM_PASSWORD"
    )

    live_allowlist = load_allowlist(
        LIVE_ALLOWLIST_FILE
    )
    movie_allowlist = load_allowlist(
        MOVIE_ALLOWLIST_FILE
    )
    series_allowlist = load_allowlist(
        SERIES_ALLOWLIST_FILE
    )

    base_url = normalize_provider_base_url(
        xtream_url
    )

    print(
        f"Provider base URL: {base_url}"
    )
    print(
        f"Live allowlist entries: {len(live_allowlist):,}"
    )
    print(
        f"Movie allowlist entries: {len(movie_allowlist):,}"
    )
    print(
        f"Series allowlist entries: {len(series_allowlist):,}"
    )
    print()

    session = create_session()

    live_categories = request_xtream_list(
        session,
        base_url,
        username,
        password,
        "get_live_categories",
    )

    vod_categories = request_xtream_list(
        session,
        base_url,
        username,
        password,
        "get_vod_categories",
    )

    series_categories = request_xtream_list(
        session,
        base_url,
        username,
        password,
        "get_series_categories",
    )

    kept_live_categories, excluded_live_categories = split_categories(
        live_categories,
        lambda name: matches_live_allowlist(
            name,
            live_allowlist,
        ),
    )

    kept_vod_categories, excluded_vod_categories = split_categories(
        vod_categories,
        lambda name: matches_content_allowlist(
            name,
            movie_allowlist,
        ),
    )

    kept_series_categories, excluded_series_categories = split_categories(
        series_categories,
        lambda name: matches_content_allowlist(
            name,
            series_allowlist,
        ),
    )

    live_category_ids = category_id_set(
        kept_live_categories
    )
    vod_category_ids = category_id_set(
        kept_vod_categories
    )
    series_category_ids = category_id_set(
        kept_series_categories
    )

    print()
    print("Downloading provider content lists...")

    all_live_streams = request_xtream_list(
        session,
        base_url,
        username,
        password,
        "get_live_streams",
    )

    all_vod_streams = request_xtream_list(
        session,
        base_url,
        username,
        password,
        "get_vod_streams",
    )

    all_series = request_xtream_list(
        session,
        base_url,
        username,
        password,
        "get_series",
    )

    filtered_live_streams = filter_streams_by_category(
        all_live_streams,
        live_category_ids,
    )

    filtered_vod_streams = filter_streams_by_category(
        all_vod_streams,
        vod_category_ids,
    )

    filtered_series = filter_streams_by_category(
        all_series,
        series_category_ids,
    )

    write_json(
        RAW_LIVE_CATEGORY_FILE,
        live_categories,
    )
    write_json(
        RAW_VOD_CATEGORY_FILE,
        vod_categories,
    )
    write_json(
        RAW_SERIES_CATEGORY_FILE,
        series_categories,
    )

    write_json(
        FILTERED_LIVE_CATEGORY_FILE,
        kept_live_categories,
    )
    write_json(
        FILTERED_VOD_CATEGORY_FILE,
        kept_vod_categories,
    )
    write_json(
        FILTERED_SERIES_CATEGORY_FILE,
        kept_series_categories,
    )

    write_category_report(
        KEPT_LIVE_REPORT,
        kept_live_categories,
    )
    write_category_report(
        KEPT_MOVIE_REPORT,
        kept_vod_categories,
    )
    write_category_report(
        KEPT_SERIES_REPORT,
        kept_series_categories,
    )

    write_category_report(
        EXCLUDED_LIVE_REPORT,
        excluded_live_categories,
    )
    write_category_report(
        EXCLUDED_MOVIE_REPORT,
        excluded_vod_categories,
    )
    write_category_report(
        EXCLUDED_SERIES_REPORT,
        excluded_series_categories,
    )

    write_json_gzip(
        FILTERED_LIVE_STREAM_FILE,
        filtered_live_streams,
    )
    write_json_gzip(
        FILTERED_VOD_STREAM_FILE,
        filtered_vod_streams,
    )
    write_json_gzip(
        FILTERED_SERIES_FILE,
        filtered_series,
    )

    category_summary = {
        "live": {
            "provider_categories": len(live_categories),
            "kept_categories": len(kept_live_categories),
            "excluded_categories": len(excluded_live_categories),
        },
        "movies": {
            "provider_categories": len(vod_categories),
            "kept_categories": len(kept_vod_categories),
            "excluded_categories": len(excluded_vod_categories),
        },
        "series": {
            "provider_categories": len(series_categories),
            "kept_categories": len(kept_series_categories),
            "excluded_categories": len(excluded_series_categories),
        },
        "allowlists": {
            "live_entries": len(live_allowlist),
            "movie_entries": len(movie_allowlist),
            "series_entries": len(series_allowlist),
        },
    }

    stream_summary = {
        "live": {
            "provider_items": len(all_live_streams),
            "kept_items": len(filtered_live_streams),
            "excluded_items": (
                len(all_live_streams)
                - len(filtered_live_streams)
            ),
            "output_file": str(
                FILTERED_LIVE_STREAM_FILE.relative_to(
                    REPOSITORY_ROOT
                )
            ),
            "compressed_bytes": file_size(
                FILTERED_LIVE_STREAM_FILE
            ),
        },
        "movies": {
            "provider_items": len(all_vod_streams),
            "kept_items": len(filtered_vod_streams),
            "excluded_items": (
                len(all_vod_streams)
                - len(filtered_vod_streams)
            ),
            "output_file": str(
                FILTERED_VOD_STREAM_FILE.relative_to(
                    REPOSITORY_ROOT
                )
            ),
            "compressed_bytes": file_size(
                FILTERED_VOD_STREAM_FILE
            ),
        },
        "series": {
            "provider_items": len(all_series),
            "kept_items": len(filtered_series),
            "excluded_items": (
                len(all_series)
                - len(filtered_series)
            ),
            "output_file": str(
                FILTERED_SERIES_FILE.relative_to(
                    REPOSITORY_ROOT
                )
            ),
            "compressed_bytes": file_size(
                FILTERED_SERIES_FILE
            ),
        },
        "security": {
            "provider_credentials_written_to_output": False,
            "direct_stream_urls_written_to_output": False,
        },
    }

    write_json(
        CATEGORY_SUMMARY_FILE,
        category_summary,
    )
    write_json(
        STREAM_SUMMARY_FILE,
        stream_summary,
    )

    print()
    print("Category results:")
    print(
        f"  Live:   {len(kept_live_categories):,} kept "
        f"of {len(live_categories):,}"
    )
    print(
        f"  Movies: {len(kept_vod_categories):,} kept "
        f"of {len(vod_categories):,}"
    )
    print(
        f"  Series: {len(kept_series_categories):,} kept "
        f"of {len(series_categories):,}"
    )

    print()
    print("Stream results:")
    print(
        f"  Live:   {len(filtered_live_streams):,} kept "
        f"of {len(all_live_streams):,}"
    )
    print(
        f"  Movies: {len(filtered_vod_streams):,} kept "
        f"of {len(all_vod_streams):,}"
    )
    print(
        f"  Series: {len(filtered_series):,} kept "
        f"of {len(all_series):,}"
    )

    print()
    print("Compressed output sizes:")
    print(
        f"  Live:   {file_size(FILTERED_LIVE_STREAM_FILE):,} bytes"
    )
    print(
        f"  Movies: {file_size(FILTERED_VOD_STREAM_FILE):,} bytes"
    )
    print(
        f"  Series: {file_size(FILTERED_SERIES_FILE):,} bytes"
    )

    expected_output_files = (
        FILTERED_LIVE_CATEGORY_FILE,
        FILTERED_VOD_CATEGORY_FILE,
        FILTERED_SERIES_CATEGORY_FILE,
        FILTERED_LIVE_STREAM_FILE,
        FILTERED_VOD_STREAM_FILE,
        FILTERED_SERIES_FILE,
        CATEGORY_SUMMARY_FILE,
        STREAM_SUMMARY_FILE,
    )

    missing_output_files = [
        str(path.relative_to(REPOSITORY_ROOT))
        for path in expected_output_files
        if not path.is_file()
    ]

    if missing_output_files:
        raise RuntimeError(
            "Build completed but required output files are missing: "
            + ", ".join(missing_output_files)
        )

    print()
    print("Verified output files:")
    for path in expected_output_files:
        print(
            f"  {path.relative_to(REPOSITORY_ROOT)} "
            f"({file_size(path):,} bytes)"
        )

    print()
    print(
        "Filtered provider stream data created successfully."
    )
    print(
        "Provider credentials and direct stream URLs were not "
        "written to the repository."
    )


def main() -> int:
    try:
        build_filtered_provider()
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
            f"Filtered provider build failed: {error}",
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())