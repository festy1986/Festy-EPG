import os
import json
import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
import html
import re
from concurrent.futures import ThreadPoolExecutor, as_completed


INPUT_FILE = "channels.txt"
OUTPUT_FILE = "guides/24-7.xml"
CACHE_FILE = "metadata_cache.json"

TMDB_API_KEY = os.environ.get("TMDB_API_KEY", "")

MAX_WORKERS = 10

os.makedirs("guides", exist_ok=True)


# -----------------------------
# Load saved metadata
# -----------------------------

if os.path.exists(CACHE_FILE):

    with open(
        CACHE_FILE,
        "r",
        encoding="utf-8"
    ) as f:
        metadata_cache = json.load(f)

else:

    metadata_cache = {}


print(
    f"Saved metadata entries: {len(metadata_cache)}"
)



# -----------------------------
# Read Channels
# -----------------------------

channels = []

with open(
    INPUT_FILE,
    "r",
    encoding="utf-8"
) as f:

    for line in f:

        line = line.strip()

        if not line:
            continue


        if "|" in line:
            line = line.split("|", 1)[1].strip()


        if line.upper().startswith("MC:"):
            line = line[3:].strip()


        if line not in channels:
            channels.append(line)


print(
    f"Loaded {len(channels)} channels"
)



# -----------------------------
# Clean text
# -----------------------------

def clean(text):

    if not text:
        return None

    text = html.unescape(text)
    text = re.sub("<.*?>", "", text)

    return text.strip()



# -----------------------------
# TVMaze
# -----------------------------

def tvmaze_lookup(name):

    try:

        r = requests.get(
            "https://api.tvmaze.com/singlesearch/shows",
            params={
                "q": name
            },
            timeout=10
        )

        if r.status_code == 200:

            data = r.json()

            return clean(
                data.get("summary")
            )


    except Exception:
        pass


    return None



# -----------------------------
# TMDB
# -----------------------------

def tmdb_lookup(name):

    if not TMDB_API_KEY:
        return None


    try:

        r = requests.get(
            "https://api.themoviedb.org/3/search/multi",
            params={
                "api_key": TMDB_API_KEY,
                "query": name
            },
            timeout=10
        )


        if r.status_code == 200:

            results = r.json().get(
                "results",
                []
            )


            if results:

                return results[0].get(
                    "overview"
                )


    except Exception:
        pass


    return None



# -----------------------------
# Logic fallback
# -----------------------------

def logic_description(name):

    n = name.lower()


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


    if any(
        word in n
        for word in music_words
    ):

        return (
            f"{name} is a 24/7 music channel "
            f"featuring related songs and programming."
        )


    horror_words = [
        "horror",
        "friday",
        "halloween",
        "nightmare",
        "fear",
        "monster"
    ]


    if any(
        word in n
        for word in horror_words
    ):

        return (
            f"{name} is a 24/7 channel featuring "
            f"horror movies and related content."
        )


    return None



# -----------------------------
# Lookup channel
# -----------------------------

def lookup_channel(channel):


    # Already saved
    if channel in metadata_cache:

        return (
            channel,
            metadata_cache[channel],
            False
        )


    print(
        f"Searching: {channel}"
    )


    desc = tvmaze_lookup(channel)


    if not desc:

        desc = tmdb_lookup(channel)


    if not desc:

        desc = logic_description(channel)



    # Save ONLY real metadata/logic results
    if desc:

        metadata_cache[channel] = desc

        return (
            channel,
            desc,
            True
        )


    # Do NOT save fallback
    return (
        channel,
        f"{channel} is a 24/7 channel.",
        False
    )



# -----------------------------
# Parallel metadata lookup
# -----------------------------

updated = 0


with ThreadPoolExecutor(
    max_workers=MAX_WORKERS
) as executor:


    futures = [

        executor.submit(
            lookup_channel,
            channel
        )

        for channel in channels
    ]


    descriptions = {}


    for future in as_completed(futures):

        channel, desc, saved = future.result()

        descriptions[channel] = desc


        if saved:
            updated += 1


        print(
            f"{channel}: {desc[:80]}"
        )



# -----------------------------
# Save metadata cache
# -----------------------------

with open(
    CACHE_FILE,
    "w",
    encoding="utf-8"
) as f:

    json.dump(
        metadata_cache,
        f,
        indent=2,
        ensure_ascii=False
    )


print(
    f"Metadata saved: {updated}"
)



# -----------------------------
# Create XML
# -----------------------------

tv = ET.Element(
    "tv",
    {
        "generator-info-name": "24/7"
    }
)



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



start_date = datetime.now(
    timezone.utc
).replace(
    hour=0,
    minute=0,
    second=0,
    microsecond=0
)



for channel in channels:


    for day in range(7):

        start = (
            start_date +
            timedelta(days=day)
        )

        stop = (
            start +
            timedelta(days=1)
        )


        programme = ET.SubElement(
            tv,
            "programme",
            {
                "start": start.strftime(
                    "%Y%m%d%H%M%S +0000"
                ),

                "stop": stop.strftime(
                    "%Y%m%d%H%M%S +0000"
                ),

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

        desc.text = descriptions[channel]



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
print(
    f"Channels: {len(channels)}"
)
