import os
import re
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone


INPUT_FILE = "channels2.txt"
OUTPUT_FILE = "guides/24-7part2.xml"

DAYS = 1
BLOCK_HOURS = 2


# --------------------------------
# Manual Display Name Overrides
# --------------------------------
#
# Use this only when a channel needs
# to be manually assigned or corrected.
#
# The key is the CLEAN DISPLAY NAME.
#
# Example:
#
# MANUAL_ID_OVERRIDES = {
#     "CHAPPELLE'S SHOW": "485167",
# }
#
# Normally, this can remain empty because
# the ID is automatically read from channels2.txt.

MANUAL_ID_OVERRIDES = {
}


# --------------------------------
# Make sure guides folder exists
# --------------------------------

os.makedirs("guides", exist_ok=True)


# --------------------------------
# Clean Channel Name
# --------------------------------

def clean_channel_name(name):

    name = name.strip()

    # Remove common country prefixes
    name = re.sub(
        r"^(US|UK|CA|AU):\s*",
        "",
        name,
        flags=re.IGNORECASE
    )

    # Remove 24/7 prefix
    name = re.sub(
        r"^24/7\s*[:\-]?\s*",
        "",
        name,
        flags=re.IGNORECASE
    )

    # Remove RAW / FPS markers
    name = re.sub(
        r"\s+ᴿᴬᵂ\b",
        "",
        name,
        flags=re.IGNORECASE
    )

    name = re.sub(
        r"\s+⁶⁰ᶠᵖˢ\b",
        "",
        name,
        flags=re.IGNORECASE
    )

    # Remove leading/trailing whitespace
    name = name.strip()

    return name


# --------------------------------
# Load Channels
# --------------------------------

channels = []

seen_ids = set()


with open(INPUT_FILE, "r", encoding="utf-8") as f:

    for line in f:

        line = line.strip()

        if not line:
            continue

        if "|" not in line:
            continue

        # Example:
        #
        # 485167 | 619 |  | US: 24/7 CHAPPELLE'S SHOW
        #
        parts = [
            part.strip()
            for part in line.split("|")
        ]

        if len(parts) < 4:
            continue

        provider_channel_id = parts[0]
        raw_name = parts[3]

        if not provider_channel_id or not raw_name:
            continue

        display_name = clean_channel_name(raw_name)

        if not display_name:
            continue

        # --------------------------------
        # Manual ID Override
        # --------------------------------

        channel_id = MANUAL_ID_OVERRIDES.get(
            display_name,
            provider_channel_id
        )

        # Prevent duplicate channel IDs
        if channel_id in seen_ids:
            continue

        seen_ids.add(channel_id)

        channels.append(
            {
                "id": channel_id,
                "name": display_name
            }
        )


print(f"Loaded {len(channels)} channels")


# --------------------------------
# Create XML
# --------------------------------

tv = ET.Element(
    "tv",
    {
        "generator-info-name": "24/7 Part 2"
    }
)


# --------------------------------
# Add Channels
# --------------------------------

for channel in channels:

    ch = ET.SubElement(
        tv,
        "channel",
        {
            "id": channel["id"]
        }
    )

    display = ET.SubElement(
        ch,
        "display-name"
    )

    display.text = channel["name"]


# --------------------------------
# Generate Programming
# 1 Day / 2 Hour Blocks
# --------------------------------

start_date = datetime.now(
    timezone.utc
).replace(
    hour=0,
    minute=0,
    second=0,
    microsecond=0
)


end_date = start_date + timedelta(
    days=DAYS
)


for channel in channels:

    current = start_date

    while current < end_date:

        stop = current + timedelta(
            hours=BLOCK_HOURS
        )

        programme = ET.SubElement(
            tv,
            "programme",
            {
                "start": current.strftime(
                    "%Y%m%d%H%M%S +0000"
                ),

                "stop": stop.strftime(
                    "%Y%m%d%H%M%S +0000"
                ),

                "channel": channel["id"]
            }
        )

        title = ET.SubElement(
            programme,
            "title"
        )

        title.text = channel["name"]

        desc = ET.SubElement(
            programme,
            "desc"
        )

        desc.text = channel["name"]

        current = stop


# --------------------------------
# Write XML
# --------------------------------

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
