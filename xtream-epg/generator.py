import os
import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone

XTREAM_URL = os.environ["XTREAM_URL"].rstrip("/")
USERNAME = os.environ["XTREAM_USERNAME"]
PASSWORD = os.environ["XTREAM_PASSWORD"]

OUTPUT = "xtream-epg/xtream.xml"


def xtream_request(action):
    url = (
        f"{XTREAM_URL}/player_api.php"
        f"?username={USERNAME}"
        f"&password={PASSWORD}"
        f"&action={action}"
    )

    response = requests.get(url, timeout=60)
    response.raise_for_status()

    return response.json()


def clean_name(name):
    remove_words = [
        "HD",
        "FHD",
        "UHD",
        "4K",
        "LIVE",
    ]

    for word in remove_words:
        name = name.replace(word, "")

    return " ".join(name.split()).strip()


def main():

    print("Downloading live channels...")

    channels = xtream_request("get_live_streams")

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
        (now + timedelta(hours=24))
        .strftime("%Y%m%d%H%M%S")
        + " +0000"
    )

    for channel in channels:

        channel_id = str(channel.get("stream_id"))

        name = clean_name(
            channel.get("name", "Unknown")
        )

        # Channel entry
        channel_element = ET.SubElement(
            tv,
            "channel",
            {
                "id": channel_id
            }
        )

        display = ET.SubElement(
            channel_element,
            "display-name"
        )

        display.text = name


        # Program entry
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

        desc = ET.SubElement(
            program,
            "desc"
        )

        desc.text = "Automatically generated from channel name."


    tree = ET.ElementTree(tv)

    tree.write(
        OUTPUT,
        encoding="utf-8",
        xml_declaration=True
    )

    print(f"Created {OUTPUT}")


if __name__ == "__main__":
    main()
