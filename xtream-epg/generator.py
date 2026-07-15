import json
import os
import time
import requests
import xml.etree.ElementTree as ET

BASE_URL = os.environ["XTREAM_URL"].rstrip("/")
USERNAME = os.environ["XTREAM_USERNAME"]
PASSWORD = os.environ["XTREAM_PASSWORD"]

OUTPUT = "xtream-epg/xtream.xml"
MAP_OUTPUT = "xtream-epg/channel-map.txt"
JSON_OUTPUT = "xtream-epg/channels.json"

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
    "1876",
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
    "2207"
}


def xtream_request(action):

    url = f"{BASE_URL}/player_api.php"

    params = {
        "username": USERNAME,
        "password": PASSWORD,
        "action": action
    }

    for attempt in range(1, 6):

        try:
            print(f"Connecting attempt {attempt}/5")

            response = requests.get(
                url,
                params=params,
                timeout=180,
                headers={
                    "User-Agent": "Mozilla/5.0"
                }
            )

            print("Request URL:", response.url)
            print("HTTP Status:", response.status_code)

            response.raise_for_status()

            return response.json()

        except Exception as e:

            print("Connection failed:", e)

            if attempt < 5:
                print("Waiting 15 seconds...")
                time.sleep(15)

    raise Exception("Unable to connect to Xtream server after 5 attempts")


def main():

    print("Downloading channels...")

    channels = xtream_request("get_live_streams")

    print(f"Provider channels: {len(channels)}")


    filtered = [
        channel
        for channel in channels
        if str(channel.get("category_id")) in ALLOWED_CATEGORIES
    ]

    print(f"Filtered channels: {len(filtered)}")


    os.makedirs(
        "xtream-epg",
        exist_ok=True
    )


    # Save provider data
    with open(
        JSON_OUTPUT,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            filtered,
            f,
            indent=2,
            ensure_ascii=False
        )


    # Create channel map
    with open(
        MAP_OUTPUT,
        "w",
        encoding="utf-8"
    ) as f:

        for channel in filtered:

            f.write(
                f"{channel.get('stream_id')} | "
                f"{channel.get('category_id')} | "
                f"{channel.get('epg_channel_id','')} | "
                f"{channel.get('name')}\n"
            )


    # Create XMLTV channel list
    tv = ET.Element("tv")


    for channel in filtered:

        xml_channel = ET.SubElement(
            tv,
            "channel",
            id=str(channel.get("stream_id"))
        )

        display = ET.SubElement(
            xml_channel,
            "display-name"
        )

        display.text = channel.get(
            "name",
            ""
        )


    ET.ElementTree(tv).write(
        OUTPUT,
        encoding="utf-8",
        xml_declaration=True
    )


    print("Created:", OUTPUT)
    print("Created:", MAP_OUTPUT)
    print("Created:", JSON_OUTPUT)



if __name__ == "__main__":
    main()
