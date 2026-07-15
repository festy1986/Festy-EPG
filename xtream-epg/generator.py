import os
import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone

XTREAM_URL = os.environ["XTREAM_URL"].rstrip("/")
USERNAME = os.environ["XTREAM_USERNAME"]
PASSWORD = os.environ["XTREAM_PASSWORD"]

OUTPUT = "xtream-epg/xtream.xml"


def get_channels():

    url = (
        f"{XTREAM_URL}/player_api.php"
        f"?username={USERNAME}"
        f"&password={PASSWORD}"
        f"&action=get_live_streams"
    )

    response = requests.get(
        url,
        headers={
            "User-Agent": "TiviMate"
        },
        timeout=60
    )

    response.raise_for_status()

    return response.json()


def clean_name(name):

    remove = [
        "HD",
        "FHD",
        "UHD",
        "4K",
        "LIVE"
    ]

    for item in remove:
        name = name.replace(item, "")

    return " ".join(name.split()).strip()


def main():

    print("Downloading channels...")

    channels = get_channels()

    print(f"Found {len(channels)} channels")

    tv = ET.Element(
        "tv",
        {
            "generator-info-name": "Xtream Placeholder EPG"
        }
    )

    now = datetime.now(timezone.utc)

    start = now.strftime("%Y%m%d%H%M%S") + " +0000"
    stop = (
        now + timedelta(hours=24)
    ).strftime("%Y%m%d%H%M%S") + " +0000"


    for channel in channels:

        channel_id = str(channel["stream_id"])

        name = clean_name(
            channel.get("name", "Unknown")
        )


        ch = ET.SubElement(
            tv,
            "channel",
            {
                "id": channel_id
            }
        )

        display = ET.SubElement(
            ch,
            "display-name"
        )

        display.text = name


        program = ET.SubElement(
            tv,
            "programme",
            {
                "start": start,
                "stop": stop,
                "channel": channel_id
            }
        )

        title = ET.SubElement(
            program,
            "title"
        )

        title.text = name


    ET.ElementTree(tv).write(
        OUTPUT,
        encoding="utf-8",
        xml_declaration=True
    )

    print("Created:", OUTPUT)


if __name__ == "__main__":
    main()
