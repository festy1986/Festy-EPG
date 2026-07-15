import os
import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone


XTREAM_URL = os.environ["XTREAM_URL"].rstrip("/")
USERNAME = os.environ["XTREAM_USERNAME"]
PASSWORD = os.environ["XTREAM_PASSWORD"]

OUTPUT = "xtream-epg/xtream.xml"


# Categories to keep
ALLOWED_CATEGORIES = {
    "188",
    "305",
    "1732",
    "575",
    "1811",
    "380",
    "2221",
    "929",
    "1083",
    "1930",
    "1966",
    "574",
    "1920",
    "1091",
    "1594",
    "1940",
    "1109",
    "1110",
    "2213",
    "2214",
    "619",
    "2057",
    "2058",
    "2059",
    "2060",
    "2061",
    "2062",
    "2063",
    "2064",
    "903",
    "2222",
    "1139",
    "573",
    "597",
    "1501",
    "604",
    "1021",
    "1503",
    "606",
    "1185",
    "2094",
    "605",
    "1016",
    "1960",
    "911",
    "2207",
    "661"
}


def xtream_request(action):

    url = (
        f"{XTREAM_URL}/player_api.php"
        f"?username={USERNAME}"
        f"&password={PASSWORD}"
        f"&action={action}"
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
        "LIVE",
        "ᴴᴰ",
        "ᴿᴬᵂ"
    ]

    for item in remove:
        name = name.replace(item, "")

    return " ".join(name.split()).strip()



def main():

    print("Downloading channels...")

    channels = xtream_request(
        "get_live_streams"
    )

    print(
        f"Provider channels: {len(channels)}"
    )


    filtered = []

    for channel in channels:

        category = str(
            channel.get("category_id")
        )

        if category in ALLOWED_CATEGORIES:
            filtered.append(channel)


    print(
        f"Filtered channels: {len(filtered)}"
    )


    tv = ET.Element(
        "tv",
        {
            "generator-info-name":
            "Xtream Filtered EPG"
        }
    )


    now = datetime.now(
        timezone.utc
    )

    start = (
        now.strftime("%Y%m%d%H%M%S")
        + " +0000"
    )

    stop = (
        (now + timedelta(hours=24))
        .strftime("%Y%m%d%H%M%S")
        + " +0000"
    )


    for channel in filtered:

        channel_id = str(
            channel["stream_id"]
        )

        name = clean_name(
            channel.get(
                "name",
                "Unknown"
            )
        )


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


        programme = ET.SubElement(
            tv,
            "programme",
            {
                "start": start,
                "stop": stop,
                "channel": channel_id
            }
        )


        title = ET.SubElement(
            programme,
            "title"
        )

        title.text = name


        desc = ET.SubElement(
            programme,
            "desc"
        )

        desc.text = (
            "Generated from provider channel name."
        )


    ET.ElementTree(tv).write(
        OUTPUT,
        encoding="utf-8",
        xml_declaration=True
    )


    print(
        f"Created {OUTPUT}"
    )


if __name__ == "__main__":
    main()
