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

# GitHub Actions supplies GITHUB_WORKSPACE.
# Locally, this script is expected to be inside the repository's config folder.
REPOSITORY_ROOT = Path(
    os.environ.get(
        "GITHUB_WORKSPACE",
        str(Path(__file__).resolve().parents[1]),
    )
).resolve()

OUTPUT_DIRECTORY = REPOSITORY_ROOT / "filtered-provider"
OUTPUT_FILE = OUTPUT_DIRECTORY / "filtered-provider.m3u"


# ---------------------------------------------------------------------------
# Filtering rules
# ---------------------------------------------------------------------------

LIVE_KEEP_PREFIXES = (
    "US|",
    "CA|",
    "UK|",
    "AU|",
    "NZ|",
    "IE|",
)

VOD_ENGLISH_PREFIXES = (
    "EN -",
)

SERIES_ENGLISH_PREFIXES = (
    "ENGLISH",
)


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


def starts_with_any(
    value: str,
    prefixes: Iterable[str],
) -> bool:
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

    return starts_with_any(
        category_name,
        FOREIGN_PREFIXES,
    )


# ---------------------------------------------------------------------------
# Category filtering
# ---------------------------------------------------------------------------

def keep_live_category(category_name: str) -> bool:
    return starts_with_any(
        category_name,
        LIVE_KEEP_PREFIXES,
    )


def keep_vod_category(category_name: str) -> bool:
    if starts_with_any(
        category_name,
        VOD_ENGLISH_PREFIXES,
    ):
        return True

    return not is_foreign_category(category_name)


def keep_series_category(category_name: str) -> bool:
    if starts_with_any(
        category_name,
        SERIES_ENGLISH_PREFIXES,
    ):
        return True

    return not is_foreign_category(category_name)


# ---------------------------------------------------------------------------
# M3U parsing
# ---------------------------------------------------------------------------

def extract_group_title(extinf_line: str) -> str:
    match = GROUP_TITLE_PATTERN.search(extinf_line)

    if not match:
        return ""

    return (
        match.group(1)
        or match.group(2)
        or ""
    ).strip()


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


def should_keep_record(
    record_lines: list[str],
) -> tuple[bool, str, str]:
    if not record_lines:
        return False, "unknown", ""

    extinf_line = record_lines[0]
    category_name = extract_group_title(extinf_line)
    stream_url = find_stream_url(record_lines)
    stream_type = classify_stream(stream_url)

    if not category_name:
        return False, stream_type, ""

    if stream_type == "live":
        return (
            keep_live_category(category_name),
            stream_type,
            category_name,
        )

    if stream_type == "vod":
        return (
            keep_vod_category(category_name),
            stream_type,
            category_name,
        )

    if stream_type == "series":
        return (
            keep_series_category(category_name),
            stream_type,
            category_name,
        )

    return False, stream_type, category_name


def process_record(
    output_handle,
    record_lines: list[str],
    stats: dict[str, int],
    seen_kept_categories: dict[str, set[str]],
) -> None:
    keep, stream_type, category_name = should_keep_record(
        record_lines
    )

    if not category_name:
        stats["ungrouped_skipped"] += 1
        return

    if keep:
        for line in record_lines:
            output_handle.write(line)
            output_handle.write("\n")

        stats[f"{stream_type}_kept"] += 1
        seen_kept_categories[stream_type].add(
            category_name
        )
    else:
        stats[f"{stream_type}_skipped"] += 1


# ---------------------------------------------------------------------------
# Response inspection
# ---------------------------------------------------------------------------

def printable_preview(data: bytes, limit: int = 1000) -> str:
    preview = data[:limit]

    text = preview.decode(
        "utf-8",
        errors="replace",
    )

    text = text.replace("\r", "\\r")
    text = text.replace("\n", "\\n\n")

    return text


def detect_response_type(
    content_type: str,
    content: bytes,
) -> str:
    stripped = content.lstrip()

    if not stripped:
        return "empty"

    lowered_type = content_type.casefold()

    if stripped.startswith(b"#EXTM3U"):
        return "m3u"

    if stripped.startswith(b"#EXTINF"):
        return "m3u-without-header"

    if stripped.startswith((b"{", b"[")):
        return "json"

    if stripped.startswith(
        (
            b"<!DOCTYPE html",
            b"<!doctype html",
            b"<html",
            b"<HTML",
        )
    ):
        return "html"

    if "json" in lowered_type:
        return "json"

    if "html" in lowered_type:
        return "html"

    return "unknown"


def decode_playlist(content: bytes) -> str:
    encodings = (
        "utf-8-sig",
        "utf-8",
        "latin-1",
    )

    for encoding in encodings:
        try:
            return content.decode(encoding)
        except UnicodeDecodeError:
            continue

    return content.decode(
        "utf-8",
        errors="replace",
    )


# ---------------------------------------------------------------------------
# Provider download and output
# ---------------------------------------------------------------------------

def download_provider_playlist(
    base_url: str,
    username: str,
    password: str,
) -> bytes:
    playlist_url = f"{base_url}/get.php"

    parameters = {
        "username": username,
        "password": password,
        "type": "m3u_plus",
        "output": "m3u8",
    }

    print("Downloading current provider playlist...")
    print(f"Provider base URL: {base_url}")

    response = requests.get(
        playlist_url,
        params=parameters,
        timeout=(30, 300),
        headers={
            "User-Agent": (
                "Mozilla/5.0 "
                "(Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 "
                "(KHTML, like Gecko) "
                "Chrome/150.0.0.0 Safari/537.36"
            ),
            "Accept": (
                "application/x-mpegURL,"
                "application/vnd.apple.mpegurl,"
                "text/plain,*/*"
            ),
            "Accept-Encoding": "gzip, deflate",
            "Connection": "close",
        },
    )

    print(f"HTTP status: {response.status_code}")
    print(
        "Content-Type: "
        f"{response.headers.get('content-type', 'missing')}"
    )
    print(
        "Content-Length header: "
        f"{response.headers.get('content-length', 'missing')}"
    )
    print(
        "Content-Encoding: "
        f"{response.headers.get('content-encoding', 'missing')}"
    )
    print(
        "Content-Disposition: "
        f"{response.headers.get('content-disposition', 'missing')}"
    )

    response.raise_for_status()

    content = response.content
    content_type = response.headers.get(
        "content-type",
        "",
    )

    print(f"Downloaded bytes: {len(content):,}")

    response_type = detect_response_type(
        content_type,
        content,
    )

    print(f"Detected response type: {response_type}")

    if response_type != "m3u":
        print()
        print("Response preview:")
        print(printable_preview(content))
        print()

    if response_type == "empty":
        raise RuntimeError(
            "The provider returned an empty HTTP response."
        )

    if response_type == "json":
        raise RuntimeError(
            "The provider returned JSON instead of an M3U playlist."
        )

    if response_type == "html":
        raise RuntimeError(
            "The provider returned an HTML page instead of an M3U playlist."
        )

    if response_type == "unknown":
        raise RuntimeError(
            "The provider returned data that was not recognized as M3U."
        )

    return content


def build_filtered_playlist() -> None:
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

    OUTPUT_DIRECTORY.mkdir(
        parents=True,
        exist_ok=True,
    )

    content = download_provider_playlist(
        base_url,
        username,
        password,
    )

    playlist_text = decode_playlist(content)
    playlist_lines = playlist_text.splitlines()

    total_lines_received = len(playlist_lines)

    extinf_lines_received = sum(
        1
        for line in playlist_lines
        if line.lstrip().startswith("#EXTINF")
    )

    print(
        f"Total response lines: "
        f"{total_lines_received:,}"
    )
    print(
        f"EXTINF entries received: "
        f"{extinf_lines_received:,}"
    )

    if extinf_lines_received == 0:
        print()
        print("First response lines:")

        for line in playlist_lines[:20]:
            safe_line = line

            if username:
                safe_line = safe_line.replace(
                    username,
                    "***USERNAME***",
                )

            if password:
                safe_line = safe_line.replace(
                    password,
                    "***PASSWORD***",
                )

            print(repr(safe_line))

        raise RuntimeError(
            "Provider response contained no #EXTINF entries."
        )

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

    temporary_path: Path | None = None

    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            newline="\n",
            delete=False,
            dir=OUTPUT_DIRECTORY,
            prefix="filtered-provider-",
            suffix=".tmp",
        ) as temporary_file:
            temporary_path = Path(
                temporary_file.name
            )

            temporary_file.write("#EXTM3U\n")

            current_record: list[str] = []

            for line in playlist_lines:
                stripped_line = line.lstrip()

                if stripped_line.startswith("#EXTM3U"):
                    continue

                if stripped_line.startswith("#EXTINF"):
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

        if (
            stats["live_kept"] == 0
            and stats["vod_kept"] == 0
            and stats["series_kept"] == 0
        ):
            raise RuntimeError(
                "The provider supplied M3U entries, but none matched "
                "the configured filtering rules."
            )

        temporary_path.replace(
            OUTPUT_FILE
        )

    except Exception:
        if (
            temporary_path is not None
            and temporary_path.exists()
        ):
            temporary_path.unlink()

        raise

    print()
    print(
        "Filtered provider playlist created successfully."
    )
    print(
        "Output: "
        f"{OUTPUT_FILE.relative_to(REPOSITORY_ROOT)}"
    )
    print()
    print("Results:")
    print(
        f"  Live kept:       "
        f"{stats['live_kept']:,}"
    )
    print(
        f"  Live skipped:    "
        f"{stats['live_skipped']:,}"
    )
    print(
        f"  Movies kept:     "
        f"{stats['vod_kept']:,}"
    )
    print(
        f"  Movies skipped:  "
        f"{stats['vod_skipped']:,}"
    )
    print(
        f"  Series kept:     "
        f"{stats['series_kept']:,}"
    )
    print(
        f"  Series skipped:  "
        f"{stats['series_skipped']:,}"
    )
    print(
        f"  Ungrouped skip:  "
        f"{stats['ungrouped_skipped']:,}"
    )
    print()
    print("Kept category totals:")
    print(
        f"  Live groups:     "
        f"{len(seen_kept_categories['live']):,}"
    )
    print(
        f"  Movie groups:    "
        f"{len(seen_kept_categories['vod']):,}"
    )
    print(
        f"  Series groups:   "
        f"{len(seen_kept_categories['series']):,}"
    )


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
