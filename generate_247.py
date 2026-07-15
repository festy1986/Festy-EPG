import os
import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
import html
import re

INPUT_FILE = "channels.txt"
OUTPUT_FILE = "guides/24-7.xml"

TMDB_API_KEY = os.environ.get("TMDB_API_KEY", "")

os.makedirs("guides", exist_ok=True)


# -----------------------------
# Read Channels
# -----------------------------

channels = []

with open(INPUT_FILE, "r", encoding="utf-8") as f:
    for line in f:

        line = line.strip()

        if not line:
            continue

        # remove old ID | NAME format
        if "|" in line:
            line = line.split("|", 1)[1].strip()

        # remove MC:
        if line.upper().startswith("MC:"):
            line = line[3:].strip()

        if line not in channels:
            channels.append(line)


print(f"Loaded {len(channels)} channels")


# -----------------------------
# Metadata Functions
# -----------------------------

metadata_cache = {}


def clean(text):
    if not text:
        return None

    text = html.unescape(text)
    text = re.sub("<.*?>", "", text)

    return text.strip()



def tvmaze_lookup(name):

    if name in metadata_cache:
        return metadata_cache[name]

    try:
        url = "https://api.tvmaze.com/singlesearch/shows"

        r = requests.get(
            url,
            params={"q": name},
            timeout=10
        )

        if r.status_code == 200:

            data = r.json()

            desc = clean(data.get("summary"))

            if desc:
                metadata_cache[name] = desc
                return desc

    except Exception:
        pass

    return None



def tmdb_lookup(name):

    if not TMDB_API_KEY:
        return None

    try:

        url = "https://api.themoviedb.org/3/search/multi"

        r = requests.get(
            url,
            params={
                "api_key": TMDB_API_KEY,
                "query": name
            },
            timeout=10
        )

        if r.status_code == 200:

            results = r.json().get("results", [])

            if results:

                item = results[0]

                desc = item.get("overview")

                if desc:
                    return desc

    except Exception:
        pass

    return None



def logic_description(name):

    n = name.lower()


    # music logic
    music_words = [
        "music",
        "rock",
        "hits",
        "country",
        "hip-hop",
        "rap",
        "r&b",
        "soul",
        "jazz",
        "pop",
        "80s",
        "90s",
        "2000",
        "2010",
        "alternative"
    ]


    if any(x in n for x in music_words):

        return (
            f"{name} is a 24/7 music channel "
            f"featuring related songs and programming."
        )


    # movie / horror logic

    horror_words = [
        "horror",
        "friday",
        "halloween",
        "nightmare",
        "fear",
        "monster"
    ]

    if any(x in n for x in horror_words):

        return (
            f"{name} is a 24/7 channel featuring "
            f"horror movies and related content."
        )


    return None



def get_description(channel):

    desc = tvmaze_lookup(channel)

    if desc:
        return desc


    desc = tmdb_lookup(channel)

    if desc:
        return desc


    desc = logic_description(channel)

    if desc:
        return desc


    return f"{channel} is a 24/7 channel."


# -----------------------------
# Build XML
# -----------------------------

tv = ET.Element(
    "tv",
    {
        "generator-info-name": "24/7"
    }
)


# Channels

for channel in channels:

    ch = ET.SubElement(
        tv,
        "channel",
        {
            "id": channel
        }
    )

    name = ET.SubElement(
        ch,
        "display-name"
    )

    name.text = channel



# Programming

start_date = datetime.now(
    timezone.utc
).replace(
    hour=0,
    minute=0,
    second=0,
    microsecond=0
)


for channel in channels:

    description = get_description(channel)

    print(
        f"{channel}: {description[:80]}"
    )


    for day in range(7):

        start = start_date + timedelta(days=day)

        stop = start + timedelta(days=1)


        programme = ET.SubElement(
            tv,
            "programme",
            {
                "start":
                start.strftime("%Y%m%d%H%M%S +0000"),

                "stop":
                stop.strftime("%Y%m%d%H%M%S +0000"),

                "channel":
                channel
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

        desc.text = description



# Save

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
