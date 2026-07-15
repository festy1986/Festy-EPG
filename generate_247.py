import os
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone


INPUT_FILE = "channels.txt"
OUTPUT_FILE = "guides/24-7.xml"

DAYS = 1
BLOCK_HOURS = 2


# Make sure guides folder exists
os.makedirs("guides", exist_ok=True)


# -----------------------------
# Load Channels
# -----------------------------

channels = []

with open(INPUT_FILE, "r", encoding="utf-8") as f:
    for line in f:

        line = line.strip()

        if not line:
            continue

        # Remove old format:
        # 123456 | CHANNEL NAME
        if "|" in line:
            line = line.split("|", 1)[1].strip()

        # Remove MC:
        if line.upper().startswith("MC:"):
            line = line[3:].strip()

        if line and line not in channels:
            channels.append(line)


print(f"Loaded {len(channels)} channels")


# -----------------------------
# Create XML
# -----------------------------

tv = ET.Element(
    "tv",
    {
        "generator-info-name": "24/7"
    }
)


# -----------------------------
# Add Channels
# -----------------------------

for channel in channels:

    ch = ET.SubElement(
        tv,
        "channel",
        {
            "id": channel
        }
    )

    display = ET.SubElement(
        ch,
        "display-name"
    )

    display.text = channel



# -----------------------------
# Generate Programming
# 1 Day / 2 Hour Blocks
# -----------------------------

start_date = datetime.now(
    timezone.utc
).replace(
    hour=0,
    minute=0,
    second=0,
    microsecond=0
)


end_date = start_date + timedelta(days=DAYS)


for channel in channels:

    current = start_date

    while current < end_date:

        stop = current + timedelta(hours=BLOCK_HOURS)

        programme = ET.SubElement(
            tv,
            "programme",
            {
                "start": current.strftime("%Y%m%d%H%M%S +0000"),
                "stop": stop.strftime("%Y%m%d%H%M%S +0000"),
                "channel": channel
            }
        )


        title = ET.SubElement(
            programme,
            "title"
        )

        title.text = channel


        desc = ET.SubElement(
            programme,
            "desc"
        )

        desc.text = channel


        current = stop



# -----------------------------
# Write XML
# -----------------------------

tree = ET.ElementTree(tv)

ET.indent(
    tree,
    space="  "
)

tree.write(
    OUTPUT_FILE,
    encoding="utf-8",
    xml_declaration=True
)


print("")
print("Created:")
print(OUTPUT_FILE)
print(f"Channels: {len(channels)}")
print(f"Days: {DAYS}")
print(f"Block size: {BLOCK_HOURS} hours")
