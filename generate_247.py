from datetime import datetime, timedelta, timezone
from pathlib import Path
import xml.etree.ElementTree as ET

CHANNEL_FILE = "channels.txt"
OUTPUT_FILE = "guide/24-7.xml"

DAYS = 7


def load_channels():
    with open(CHANNEL_FILE, "r", encoding="utf-8") as f:
        return [
            line.strip()
            for line in f
            if line.strip()
        ]


def create_program(title, start, end):
    program = ET.Element("programme", {
        "start": start.strftime("%Y%m%d%H%M%S +0000"),
        "stop": end.strftime("%Y%m%d%H%M%S +0000"),
    })

    ET.SubElement(program, "title").text = title
    ET.SubElement(program, "desc").text = "24/7 channel"

    return program


def main():

    channels = load_channels()

    tv = ET.Element("tv", {
        "generator-info-name": "24/7"
    })


    # Create channels
    for channel in channels:
        ch = ET.SubElement(tv, "channel", {
            "id": channel
        })

        ET.SubElement(ch, "display-name").text = channel


    # Create 24-hour programming for 7 days
    now = datetime.now(timezone.utc)

    start_day = now.replace(
        hour=0,
        minute=0,
        second=0,
        microsecond=0
    )


    for channel in channels:

        current = start_day

        for _ in range(DAYS):

            end = current + timedelta(hours=24)

            tv.append(
                create_program(
                    channel,
                    current,
                    end
                )
            )

            current = end


    Path("guide").mkdir(exist_ok=True)

    tree = ET.ElementTree(tv)
    tree.write(
        OUTPUT_FILE,
        encoding="utf-8",
        xml_declaration=True
    )


    print(f"Created {OUTPUT_FILE}")
    print(f"Channels: {len(channels)}")


if __name__ == "__main__":
    main()
