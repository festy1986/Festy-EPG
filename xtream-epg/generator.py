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
    response = requests.get(url, timeout=30)
    response.raise_for_status()
    return response.json()


def clean_title(name):
    remove = [
        "HD",
        "FHD",
        "LIVE",
        "TV",
    ]

    for item in remove:
        name = name.replace(item, "")

    return " ".join(name.split()).strip()


def main():
    channels = xtream_request("get_live_streams")

    tv = ET.Element(
        "tv",
        {
            "generator-info-name": "Xtream EPG Generator"
        }
    )

    now = datetime.now(timezone.utc)

    for channel in channels:

        name = clean_title(
            channel.get("name", "Unknown Channel")
        )

        stream_id = str(
            channel.get("stream_id")
        )

        ET.SubElement(
            tv,
            "channel",
            {
                "id": stream_id
            }
        ).append(
            ET.Element(
                "display-name"
            )
        )

        channel_element = tv[-1]
        channel_element[-1].text = name

        start = now
        stop = now + timedelta(hours=24)

        programme = ET.SubElement(
            tv,
            "programme",
            {
                "start": start.strftime("%Y%m%d%H%M%S") + " +0000",
                "stop": stop.strftime("%Y%m%d%H%M%S") + " +0000",
                "channel": stream_id,
            },
        )

        title = ET.SubElement(programme, "title")
        title.text = name

        desc = ET.SubElement(programme, "desc")
        desc.text = "Automatically generated placeholder guide."

    tree = ET.ElementTree(tv)
    tree.write(
        OUTPUT,
        encoding="utf-8",
        xml_declaration=True
    )


if __name__ == "__main__":
    main()
