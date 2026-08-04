import csv
import html
import os
import re
from pathlib import Path

import requests


OUTPUT_TXT = Path("major-league-channel-names.txt")
OUTPUT_CSV = Path("major-league-channel-names.csv")
LEAGUES = ("MLB", "NFL", "NBA", "NHL")


def clean_text(value):
    if value is None:
        return ""

    text = html.unescape(str(value))
    text = re.sub(r"<[^>]+>", "", text)
    text = text.replace("\r", " ").replace("\n", " ")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def normalize_xtream_url(value):
    url = value.strip().rstrip("/")

    if url.startswith("https://"):
        url = url.replace("https://", "http://", 1)

    if ":80" not in url and ":443" not in url:
        url += ":80"

    return url


def api_get(session, base_url, username, password, action=None):
    params = {
        "username": username,
        "password": password,
    }

    if action:
        params["action"] = action

    response = session.get(
        f"{base_url}/player_api.php",
        params=params,
        timeout=(30, 600),
    )

    if response.status_code == 401:
        raise RuntimeError(
            "Provider returned 401 Unauthorized. "
            "Check XTREAM_URL, XTREAM_USERNAME, and XTREAM_PASSWORD."
        )

    response.raise_for_status()
    return response.json()


def detect_leagues(text):
    found = []

    for league in LEAGUES:
        if re.search(rf"\b{league}\b", text, flags=re.IGNORECASE):
            found.append(league)

    return found


def main():
    required = (
        "XTREAM_URL",
        "XTREAM_USERNAME",
        "XTREAM_PASSWORD",
    )

    missing = [
        name
        for name in required
        if not os.environ.get(name)
    ]

    if missing:
        raise RuntimeError(
            "Missing required GitHub secrets: "
            + ", ".join(missing)
        )

    base_url = normalize_xtream_url(
        os.environ["XTREAM_URL"]
    )

    username = os.environ["XTREAM_USERNAME"]
    password = os.environ["XTREAM_PASSWORD"]

    session = requests.Session()

    session.headers.update(
        {
            "User-Agent": "Mozilla/5.0",
        }
    )

    print("Testing provider authentication...")

    account = api_get(
        session,
        base_url,
        username,
        password,
    )

    user_info = (
        account.get("user_info", {})
        if isinstance(account, dict)
        else {}
    )

    auth_value = str(
        user_info.get("auth", "")
    )

    if auth_value and auth_value != "1":
        raise RuntimeError(
            f"Provider API answered, but user_info.auth was {auth_value!r}."
        )

    print("Authentication succeeded.")
    print("Downloading live categories...")

    categories_data = api_get(
        session,
        base_url,
        username,
        password,
        action="get_live_categories",
    )

    category_names = {}

    if isinstance(categories_data, list):
        for category in categories_data:
            category_id = str(
                category.get("category_id", "")
            )

            category_name = clean_text(
                category.get("category_name", "")
            )

            if category_id:
                category_names[category_id] = category_name

    print(
        f"Live categories downloaded: {len(category_names)}"
    )

    print("Downloading live streams...")

    streams = api_get(
        session,
        base_url,
        username,
        password,
        action="get_live_streams",
    )

    if not isinstance(streams, list):
        raise RuntimeError(
            "get_live_streams did not return a list."
        )

    print(
        f"Live streams downloaded: {len(streams)}"
    )

    rows = []

    for stream in streams:
        stream_id = str(
            stream.get("stream_id", "")
        )

        stream_name = clean_text(
            stream.get("name", "")
        )

        category_id = str(
            stream.get("category_id", "")
        )

        category_name = category_names.get(
            category_id,
            "",
        )

        detection_text = (
            f"{category_name} {stream_name}"
        )

        leagues = detect_leagues(
            detection_text
        )

        if not leagues:
            continue

        rows.append(
            {
                "league": ",".join(leagues),
                "stream_id": stream_id,
                "category_id": category_id,
                "category_name": category_name,
                "provider_name": stream_name,
                "epg_channel_id": clean_text(
                    stream.get("epg_channel_id", "")
                ),
                "tv_archive": str(
                    stream.get("tv_archive", "")
                ),
                "added": str(
                    stream.get("added", "")
                ),
            }
        )

    league_order = {
        league: index
        for index, league in enumerate(LEAGUES)
    }

    def row_sort_key(row):
        leagues = row["league"].split(",")

        league_index = min(
            league_order.get(league, 99)
            for league in leagues
        )

        stream_id = row["stream_id"]

        if stream_id.isdigit():
            stream_sort = (
                0,
                int(stream_id),
            )
        else:
            stream_sort = (
                1,
                stream_id,
            )

        return (
            league_index,
            row["category_name"].lower(),
            row["provider_name"].lower(),
            stream_sort,
        )

    rows.sort(
        key=row_sort_key
    )

    counts = {
        league: sum(
            1
            for row in rows
            if league in row["league"].split(",")
        )
        for league in LEAGUES
    }

    with OUTPUT_CSV.open(
        "w",
        encoding="utf-8",
        newline="",
    ) as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "league",
                "stream_id",
                "category_id",
                "category_name",
                "provider_name",
                "epg_channel_id",
                "tv_archive",
                "added",
            ],
        )

        writer.writeheader()
        writer.writerows(rows)

    with OUTPUT_TXT.open(
        "w",
        encoding="utf-8",
    ) as handle:
        handle.write(
            "CURRENT PROVIDER MLB / NFL / NBA / NHL CHANNEL NAMES\n"
        )

        handle.write(
            "=" * 72 + "\n"
        )

        handle.write(
            f"Total matching streams: {len(rows)}\n"
        )

        for league in LEAGUES:
            handle.write(
                f"{league}: {counts[league]}\n"
            )

        handle.write("\n")

        current_league = None

        for row in rows:
            primary_league = row["league"].split(",")[0]

            if primary_league != current_league:
                current_league = primary_league

                handle.write("\n")
                handle.write(
                    f"[{current_league}]\n"
                )
                handle.write(
                    "-" * 72 + "\n"
                )

            handle.write(
                f"ID={row['stream_id']} | "
                f"CATEGORY={row['category_name']} | "
                f"NAME={row['provider_name']}\n"
            )

    print()
    print("Current provider names")
    print("=" * 72)

    current_league = None

    for row in rows:
        primary_league = row["league"].split(",")[0]

        if primary_league != current_league:
            current_league = primary_league
            print()
            print(f"[{current_league}]")

        print(
            f"ID={row['stream_id']} | "
            f"CATEGORY={row['category_name']} | "
            f"NAME={row['provider_name']}"
        )

    print()
    print("Summary")
    print("=" * 72)
    print(
        f"Total matching streams: {len(rows)}"
    )

    for league in LEAGUES:
        print(
            f"{league}: {counts[league]}"
        )

    print()
    print(f"Wrote {OUTPUT_TXT}")
    print(f"Wrote {OUTPUT_CSV}")

    print(
        "These are raw names returned by the provider's "
        "get_live_streams API. No matchup cleanup or renaming was applied."
    )


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print()
        print("TEST FAILED")
        print(str(exc))
        raise
