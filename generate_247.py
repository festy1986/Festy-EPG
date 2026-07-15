import os
from datetime import datetime, timedelta, timezone
import xml.etree.ElementTree as ET

INPUT_FILE = "channels.txt"
OUTPUT_FILE = "guides/24-7.xml"

os.makedirs("guides", exist_ok=True)


def get_description(channel):
    """
    Generate a description based on channel name.
    Falls back to channel name 24/7.
    """

    name = channel.upper()

    # Music channels
    music_keywords = [
        "MUSIC",
        "ROCK",
        "POP",
        "HIP-HOP",
        "HIP HOP",
        "RAP",
        "R&B",
        "SOUL",
        "JAZZ",
        "COUNTRY",
        "CLASSIC HITS",
        "OLDIES",
        "80S",
        "90S",
        "2000S",
        "2010S",
        "ALTERNATIVE",
        "METAL",
        "PUNK",
        "DANCE",
        "EDM",
        "REGGAE",
        "BLUES"
    ]

    if any(keyword in name for keyword in music_keywords):
        return f"24/7 {channel} music channel."

    # Movie channels
    movie_keywords = [
        "MOVIE",
        "MOVIES",
        "FILM",
        "HORROR",
        "ACTION",
        "THRILLER",
        "COMEDY",
        "WESTERN"
    ]

    if any(keyword in name for keyword in movie_keywords):
        return f"24/7 {channel} movie channel."

    # Sports channels
    sports_keywords = [
        "SPORT",
        "NFL",
        "NBA",
        "MLB",
        "NHL",
        "FOOTBALL",
        "BASEBALL",
        "HOCKEY",
        "SOCCER",
        "WRESTLING"
    ]

    if any(keyword in name for keyword in sports_keywords):
        return f"24/7 {channel} sports channel."

    # TV show / series channels
    show_keywords = [
        "SHOW",
        "SERIES",
        "TV",
        "ADULT",
        "ANIME",
        "CARTOON"
    ]

    if any(keyword in name for keyword in show_keywords):
        return f"24/7 channel featuring {channel}."

    # Known entertainment titles
    entertainment_keywords = [
        "STAR",
        "CALL",
        "SAUL",
        "BATMAN",
        "STAR TREK",
        "STAR WARS",
        "WALKING DEAD",
        "SIMPSON",
        "FRIENDS",
        "OFFICE"
    ]

    if any(keyword in name for keyword in entertainment_keywords):
        return f"24/7 channel featuring episodes of {channel}."

    # Default fallback
    return f"{channel} 24/7"


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

        # Remove MC prefix
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


# Generate 7 days
start_date = datetime.now(timezone.utc).replace(
    hour=0,
    minute=0,
    second=0,
    microsecond=0
)


for channel in channels:

    description = get_description(channel)

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
        desc.text = description


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
