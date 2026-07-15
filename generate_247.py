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
MISSING_FILE = "missing_metadata.txt"

TMDB_API_KEY = os.environ.get("TMDB_API_KEY", "")

MAX_WORKERS = 10

os.makedirs("guides", exist_ok=True)


# -----------------------------
# Load cache
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
    f"Cached metadata: {len(metadata_cache)}"
)



# -----------------------------
# Load channels
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
            line = line.split("|",1)[1].strip()

        if line.upper().startswith("MC:"):
            line = line[3:].strip()

        if line not in channels:
            channels.append(line)


print(
    f"Channels loaded: {len(channels)}"
)



# -----------------------------
# Clean
# -----------------------------

def clean(text):

    if not text:
        return None

    text = html.unescape(text)
    text = re.sub(
        "<.*?>",
        "",
        text
    )

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

            return clean(
                r.json().get("summary")
            )

    except:
        pass

    return None



# -----------------------------
# TMDB
# -----------------------------

def tmdb_search(name, media):

    if not TMDB_API_KEY:
        return None


    try:

        r = requests.get(
            f"https://api.themoviedb.org/3/search/{media}",
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

                return clean(
                    results[0].get(
                        "overview"
                    )
                )


    except:
        pass


    return None



def tmdb_lookup(name):

    # TV first
    desc = tmdb_search(
        name,
        "tv"
    )

    if desc:
        return desc


    # Movies second
    desc = tmdb_search(
        name,
        "movie"
    )

    if desc:
        return desc


    return None



# -----------------------------
# Wikipedia
# -----------------------------

def wikipedia_lookup(name):

    try:

        r = requests.get(
            "https://en.wikipedia.org/api/rest_v1/page/summary/" +
            name.replace(" ","_"),
            timeout=10
        )


        if r.status_code == 200:

            data = r.json()

            return clean(
                data.get("extract")
            )


    except:
        pass


    return None



# -----------------------------
# Logic fallback
# -----------------------------

def logic_description(name):

    n = name.lower()


    if any(x in n for x in [
        "music",
        "rock",
        "hits",
        "country",
        "rap",
        "hip-hop",
        "r&b",
        "soul",
        "jazz",
        "pop",
        "80s",
        "90s",
        "2000",
        "2010"
    ]):

        return (
            f"{name} is a 24/7 music channel "
            "featuring related songs and programming."
        )


    if any(x in n for x in [
        "horror",
        "friday",
        "halloween",
        "nightmare",
        "monster"
    ]):

        return (
            f"{name} is a 24/7 channel featuring "
            "horror movies and related content."
        )


    return None



# -----------------------------
# Find metadata
# -----------------------------

def find_metadata(channel):

    if channel in metadata_cache:

        return (
            channel,
            metadata_cache[channel],
            False
        )


    print(
        "Searching:",
        channel
    )


    desc = tvmaze_lookup(channel)

    if not desc:
        desc = tmdb_lookup(channel)

    if not desc:
        desc = wikipedia_lookup(channel)

    if not desc:
        desc = logic_description(channel)


    if desc:

        metadata_cache[channel] = desc

        return (
            channel,
            desc,
            True
        )


    return (
        channel,
        f"{channel} is a 24/7 channel.",
        False
    )



# -----------------------------
# Parallel lookup
# -----------------------------

descriptions = {}
missing = []
saved = 0


with ThreadPoolExecutor(
    max_workers=MAX_WORKERS
) as executor:


    futures = [
        executor.submit(
            find_metadata,
            c
        )
        for c in channels
    ]


    for future in as_completed(futures):

        channel, desc, was_saved = future.result()

        descriptions[channel] = desc


        if was_saved:
            saved += 1


        if desc == f"{channel} is a 24/7 channel.":
            missing.append(channel)


        print(
            f"{channel}: {desc[:70]}"
        )



# -----------------------------
# Save cache
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



# -----------------------------
# Save missing report
# -----------------------------

with open(
    MISSING_FILE,
    "w",
    encoding="utf-8"
) as f:

    for item in sorted(missing):
        f.write(
            item + "\n"
        )


print(
    f"New metadata saved: {saved}"
)

print(
    f"Missing metadata: {len(missing)}"
)



# -----------------------------
# Build XML
# -----------------------------

tv = ET.Element(
    "tv",
    {
        "generator-info-name":"24/7"
    }
)


for channel in channels:

    ch = ET.SubElement(
        tv,
        "channel",
        {
            "id":channel
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

        start = start_date + timedelta(
            days=day
        )

        stop = start + timedelta(
            days=1
        )


        p = ET.SubElement(
            tv,
            "programme",
            {
                "start":start.strftime(
                    "%Y%m%d%H%M%S +0000"
                ),
                "stop":stop.strftime(
                    "%Y%m%d%H%M%S +0000"
                ),
                "channel":channel
            }
        )


        title = ET.SubElement(
            p,
            "title"
        )

        title.text = channel


        desc = ET.SubElement(
            p,
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
