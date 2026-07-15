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
    url = (
        f"{BASE_URL}/player_api.php"
        f"?username={USERNAME}"
        f"&password={PASSWORD}"
        f"&action={action}"
    )

    for attempt in range(1, 6):
        try:
            print(f"Connecting attempt {attempt}/5")

            response = requests.get(
                url,
                timeout=120
            )

            print("HTTP Status:", response.status_code)

            response.raise_for_status()

            return response.json()

        except Exception as e:
            print("Connection failed:", e)

            if attempt < 5:
                print("Waiting 10 seconds...")
                time.sleep(10)

    raise Exception("Unable to connect to Xtream server after 5 attempts")


def main():

    print("Downloading channels...")

    channels = xtream_request("get_live_streams")

    print(f"Provider channels: {len(channels)}")

    filtered = [
        c for c in channels
        if str(c.get("category_id")) in ALLOWED_CATEGORIES
    ]

    print(f"Filtered channels: {len(filtered)}")

    os.makedirs("xtream-epg", exist_ok=True)


    # Save full provider data
    with open(JSON_OUTPUT, "w", encoding="utf-8") as f:
        json.dump(
            filtered,
            f,
            indent=2,
            ensure_ascii=False
        )


    # Create channel map
    with open(MAP_OUTPUT, "w", encoding="utf-8") as f:
        for c in filtered:

            f.write(
                f"{c.get('stream_id')} | "
                f"{c.get('category_id')} | "
                f"{c.get('epg_channel_id','')} | "
                f"{c.get('name')}\n"
            )


    # Create XMLTV skeleton
    tv = ET.Element("tv")

    for c in filtered:

        channel = ET.SubElement(
            tv,
            "channel",
            id=str(c["stream_id"])
        )

        display = ET.SubElement(
            channel,
            "display-name"
        )

        display.text = c.get("name", "")


    tree = ET.ElementTree(tv)

    tree.write(
        OUTPUT,
        encoding="utf-8",
        xml_declaration=True
    )


    print("Created:", OUTPUT)
    print("Created:", MAP_OUTPUT)
    print("Created:", JSON_OUTPUT)


if __name__ == "__main__":
    main()
