import os
import html
from datetime import datetime, timedelta, timezone
import xml.etree.ElementTree as ET

INPUT_FILE = "channels.txt"
OUTPUT_FILE = "guides/24-7.xml"

# Make sure guides folder exists
os.makedirs("guides", exist_ok=True)

channels = []

# Read channels.txt
with open(INPUT_FILE, "r", encoding="utf-8") as f:
    for line in f:
        line = line.strip()

        if not line:
            continue

        # Remove old format:
        # 1832693 | MC: HIP-HOP PARTY
        if "|" in line:
            line = line.split("|", 1)[1].strip()

        if line.upper().startswith("MC:"):
            line = line[3:].strip()

        line = line.strip()

        if line and line not in channels:
            channels.append(line)


# Create XML
tv = ET.Element(
    "tv",
    {
        "generator-info-name": "24/7"
    }
)

# Add channels
for channel in sorted(channels):
    ch = ET.SubElement(
        tv,
        "channel",
        {
            "id": channel
        }
    )

    name = ET.SubElement(ch, "display-name")
    name.text = channel


# Generate 7 days of programming
start_date = datetime.now(timezone.utc).replace(
    hour=0,
    minute=0,
    second=0,
    microsecond=0
)

for channel in channels:

    for day in range(7):

        start = start_date + timedelta(days=day)
        stop = start + timedelta(days=1)

        programme = ET.SubElement(
            tv,
            "programme",
            {
                "start": start.strftime("%Y%m%d%H%M%S +0000"),
                "stop": stop.strftime("%Y%m%d%H%M%S +0000"),
                "channel": channel
            }
        )

        title = ET.SubElement(programme, "title")
        title.text = channel

        desc = ET.SubElement(programme, "desc")
        desc.text = "24/7 Music Channel"


# Write XML
tree = ET.ElementTree(tv)

ET.indent(tree, space="  ")

tree.write(
    OUTPUT_FILE,
    encoding="utf-8",
    xml_declaration=True
)

print(f"Created {OUTPUT_FILE}")
print(f"Total channels: {len(channels)}")
