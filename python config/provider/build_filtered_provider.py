#!/usr/bin/env python3

from __future__ import annotations

import os
import re
import sys
import tempfile
from pathlib import Path
from typing import Iterable
from urllib.parse import urlsplit, urlunsplit

import requests


# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
OUTPUT_DIRECTORY = REPOSITORY_ROOT / "filtered-provider"
OUTPUT_FILE = OUTPUT_DIRECTORY / "filtered-provider.m3u"


# ---------------------------------------------------------------------------
# Filtering rules
# ---------------------------------------------------------------------------

# Live TV:
# Keep every current and future category beginning with one of these prefixes.
LIVE_KEEP_PREFIXES = (
    "US|",
    "CA|",
    "UK|",
    "AU|",
    "NZ|",
    "IE|",
)

# Movies:
# Keep every current and future English category.
VOD_ENGLISH_PREFIXES = (
    "EN -",
)

# Series:
# Keep every current and future English category.
SERIES_ENGLISH_PREFIXES = (
    "ENGLISH",
)


# Country- or language-specific category prefixes.
#
# For Movies and Series:
# - An English category is kept.
# - A category beginning with one of these foreign identifiers is skipped.
# - Any category without a country/language designation is kept automatically.
#
# This means future global categories such as:
# SHOWTIME MOVIES
# HULU SERIES
# STARZ SERIES
# MAX ORIGINALS
# will automatically populate.
FOREIGN_PREFIXES = (
    "AF -",
    "AFRICA",
    "AL -",
    "ALBANIA",
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
    "ES -",
    "ESPAÑA",
    "EX -",
    "FR -",
    "FRANCE",
    "GERMANY",
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
    "IT -",
    "JAPAN",
    "JP -",
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
    "POLSKA",
    "PORTUGAL",
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
    "SUOMEN",
    "SUOMI",
    "SVENSK",
    "SVENSKA",
    "TR -",
    "TURKISH",
    "TURKSIH",
    "VIAPLAY ÍSLANDS",
    "ÍSLANDS",
)


# Detect category names beginning with Arabic, Hebrew, Cyrillic, Greek,
# Chinese, Japanese, or Korean characters.
FOREIGN_SCRIPT_RANGES = (
    ("\u0370", "\u03ff"),  # Greek
    ("\u0400", "\u04ff"),  # Cyrillic
    ("\u0590", "\u05ff"),  # Hebrew
    ("\u0600", "\u06ff"),  # Arabic
    ("\u0750", "\u077f"),  # Arabic Supplement
    ("\u08a0", "\u08ff"),  # Arabic Extended
    ("\u3040", "\u30ff"),  # Japanese
    ("\u3400", "\u4dbf"),  # CJK Extension A
    ("\u4e00", "\u9fff"),  # CJK Unified Ideographs
    ("\uac00", "\ud7af"),  # Korean Hangul
)


GROUP_TITLE_PATTERN = re.compile(
    r"""group-title\s*=\s*(?:"([^"]*)"|'([^']*)')""",
    re.IGNORECASE,
)


# ---------------------------------------------------------------------------
# General helpers
# ---------------------------------------------------------------------------

def required_environment_variable(name: str) -> str:
    value = os.environ.get(name, "").strip()

    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")

    return value


def normalize_provider_base_url(value: str) -> str:
    value = value.strip()

    if not value.startswith(("http://", "https://")):
        value = f"http://{value}"

    parsed = urlsplit(value)

    if not parsed.netloc:
        raise ValueError(f"Invalid XTREAM_URL: {value}")

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


def starts_with_any(value: str, prefixes: Iterable[str]) -> bool:
    normalized_value = value.strip().casefold()

    return any(
        normalized_value.startswith(prefix.strip().casefold())
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


def is_foreign_category(category_name: str) -> bool:
    if begins_with_foreign_script(category_name):
        return True

    return starts_with_any(category_name, FOREIGN_PREFIXES)


# ---------------------------------------------------------------------------
# Category filtering
# ---------------------------------------------------------------------------

def keep_live_category(category_name: str) -> bool:
    return starts_with_any(category_name, LIVE_KEEP_PREFIXES)


def keep_vod_category(category_name: str) -> bool:
    if starts_with_any(category_name, VOD_ENGLISH_PREFIXES):
        return True

    return not is_foreign_category(category_name)


def keep_series_category(category_name: str) -> bool:
    if starts_with_any(category_name, SERIES_ENGLISH_PREFIXES):
        return True

    return not is_foreign_category(category_name)


# ---------------------------------------------------------------------------
# M3U parsing
# ---------------------------------------------------------------------------

def extract_group_title(extinf_line: str) -> str:
    match = GROUP_TITLE_PATTERN.search(extinf_line)

    if not match:
        return ""

    return (match.group(1) or match.group(2) or "").strip()


def find_stream_url(record_lines: list[str]) -> str:
    for line in reversed(record_lines):
        stripped = line.strip()

        if not stripped:
            continue

        if stripped.startswith("#"):
            continue

        return stripped

    return ""


def classify_stream(stream_url: str) -> str:
    normalized_url = stream_url.casefold()

    if "/series/" in normalized_url:
        return "series"

    if "/movie/" in normalized_url:
        return "vod"

    return "live"


def should_keep_record(record_lines: list[str]) -> tuple[bool, str, str]:
    if not record_lines:
        return False, "unknown", ""

    extinf_line = record_lines[0]
    category_name = extract_group_title(extinf_line)
    stream_url = find_stream_url(record_lines)
    stream_type = classify_stream(stream_url)

    if not category_name:
        return False, stream_type, category_name

    if stream_type == "live":
        return keep_live_category(category_name), stream_type, category_name

    if stream_type == "vod":
        return keep_vod_category(category_name), stream_type, category_name

    if stream_type == "series":
        return keep_series_category(category_name), stream_type, category_name

    return False, stream_type, category_name


# ---------------------------------------------------------------------------
# Provider download and output
# ---------------------------------------------------------------------------

def build_playlist_url(
    base_url: str,
    username: str,
    password: str,
) -> str:
    return (
        f"{base_url}/get.php"
        f"?username={username}"
        f"&password={password}"
        f"&type=m3u_plus"
        f"&output=ts"
    )


def validate_response_start(response: requests.Response) -> None:
    content_type = response.headers.get("content-type", "").casefold()

    if "application/json" in content_type:
        preview = response.raw.read(500, decode_content=True)
        raise RuntimeError(
            "Provider returned JSON instead of an M3U playlist: "
            f"{preview.decode('utf-8', errors='replace')}"
        )


def write_record(output_handle, record_lines: list[str]) -> None:
    for line in record_lines:
        output_handle.write(line)

        if not line.endswith("\n"):
            output_handle.write("\n")


def build_filtered_playlist() -> None:
    xtream_url = required_environment_variable("XTREAM_URL")
    username = required_environment_variable("XTREAM_USERNAME")
    password = required_environment_variable("XTREAM_PASSWORD")

    base_url = normalize_provider_base_url(xtream_url)
    playlist_url = build_playlist_url(base_url, username, password)

    OUTPUT_DIRECTORY.mkdir(parents=True, exist_ok=True)

    stats = {
        "live_kept": 0,
        "live_skipped": 0,
        "vod_kept": 0,
        "vod_skipped": 0,
        "series_kept": 0,
        "series_skipped": 0,
        "ungrouped_skipped": 0,
    }

    seen_kept_categories: dict[str, set[str]] = {
        "live": set(),
        "vod": set(),
        "series": set(),
    }

    print("Downloading current provider playlist...")
    print(f"Provider base URL: {base_url}")

    with requests.get(
        playlist_url,
        stream=True,
        timeout=(30, 300),
        headers={
            "User-Agent": "festy-filtered-provider/1.0",
            "Accept": "*/*",
        },
    ) as response:
        response.raise_for_status()
        validate_response_start(response)

        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            newline="\n",
            delete=False,
            dir=OUTPUT_DIRECTORY,
            prefix="filtered-provider-",
            suffix=".tmp",
        ) as temporary_file:
            temporary_path = Path(temporary_file.name)

            temporary_file.write("#EXTM3U\n")

            current_record: list[str] = []
            first_nonempty_line_seen = False

            for raw_line in response.iter_lines(
                decode_unicode=True,
                chunk_size=64 * 1024,
            ):
                if raw_line is None:
                    continue

                line = raw_line.rstrip("\r\n")
                stripped = line.strip()

                if not first_nonempty_line_seen and stripped:
                    first_nonempty_line_seen = True

                    if stripped.startswith("#EXTM3U"):
                        continue

                if line.startswith("#EXTINF"):
                    if current_record:
                        process_record(
                            temporary_file,
                            current_record,
                            stats,
                            seen_kept_categories,
                        )

                    current_record = [line]
                    continue

                if current_record:
                    current_record.append(line)

            if current_record:
                process_record(
                    temporary_file,
                    current_record,
                    stats,
                    seen_kept_categories,
                )

    temporary_path.replace(OUTPUT_FILE)

    print()
    print("Filtered provider playlist created successfully.")
    print(f"Output: {OUTPUT_FILE.relative_to(REPOSITORY_ROOT)}")
    print()
    print("Results:")
    print(f"  Live kept:       {stats['live_kept']}")
    print(f"  Live skipped:    {stats['live_skipped']}")
    print(f"  Movies kept:     {stats['vod_kept']}")
    print(f"  Movies skipped:  {stats['vod_skipped']}")
    print(f"  Series kept:     {stats['series_kept']}")
    print(f"  Series skipped:  {stats['series_skipped']}")
    print(f"  Ungrouped skip:  {stats['ungrouped_skipped']}")
    print()
    print("Kept category totals:")
    print(f"  Live groups:     {len(seen_kept_categories['live'])}")
    print(f"  Movie groups:    {len(seen_kept_categories['vod'])}")
    print(f"  Series groups:   {len(seen_kept_categories['series'])}")


def process_record(
    output_handle,
    record_lines: list[str],
    stats: dict[str, int],
    seen_kept_categories: dict[str, set[str]],
) -> None:
    keep, stream_type, category_name = should_keep_record(record_lines)

    if not category_name:
        stats["ungrouped_skipped"] += 1
        return

    if keep:
        write_record(output_handle, record_lines)
        stats[f"{stream_type}_kept"] += 1
        seen_kept_categories[stream_type].add(category_name)
    else:
        stats[f"{stream_type}_skipped"] += 1


def main() -> int:
    try:
        build_filtered_playlist()
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
