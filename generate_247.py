import os
import json
import requests
import html
import re
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from concurrent.futures import ThreadPoolExecutor, as_completed

INPUT_FILE = "channels.txt"
OUTPUT_FILE = "guides/24-7.xml"
CACHE_FILE = "metadata_cache.json"

TMDB_API_KEY = os.environ.get("TMDB_API_KEY", "")

os.makedirs("guides", exist_ok=True)


# -----------------------------
# Load Metadata Cache
# -----------------------------

if os.path.exists(CACHE_FILE):

    with open(CACHE_FILE, "r", encoding="utf-8") as f:
        metadata_cache = json.load(f)

else:
    metadata_cache = {}


# -----------------------------
# Load Channels
# -----------------------------

channels = []

with open(INPUT_FILE, "r", encoding="utf-8") as f:

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


print(f"Loaded {len(channels)} channels")


# -----------------------------
# Helpers
# -----------------------------

def clean(text):

    if not text:
        return None

    text = html.unescape(text)
    text = re.sub("<.*?>", "", text)

    return text.strip()



# -----------------------------
# Metadata Search
# -----------------------------

def tvmaze_lookup(name):

    try:

        r = requests.get(
            "https://api.tvmaze.com/singlesearch/shows",
            params={"q": name},
            timeout=5
        )

        if r.status_code == 200:

            data = r.json()

            desc = clean(
                data.get("summary")
            )

            if desc:
                return desc

    except:

        pass

    return None



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
            timeout=5
        )

        if r.status_code == 200:

            results = r.json().get(
                "results",
                []
            )

            if results:

                desc = results[0].get(
                    "overview"
                )

                if desc:
                    return desc

    except:

        pass

    return None



# -----------------------------
# Smart Fallback Generator
# -----------------------------

def smart_description(name):

    n = name.lower()


    decades = {
        "50s": "the 1950s",
        "60s": "the 1960s",
        "70s": "the 1970s",
        "80s": "the 1980s",
        "90s": "the 1990s",
        "2000s": "the 2000s",
        "2010s": "the 2010s"
    }


    for key, era in decades.items():

        if key in n:

            if "movie" in n or "film" in n:

                return (
                    f"{name} is a 24/7 movie channel "
                    f"featuring popular films from {era}, "
                    f"including classic favorites and memorable performances."
                )


            if any(x in n for x in [
                "music",
                "hits",
                "rock",
                "rap",
                "hip",
                "r&b"
            ]):

                return (
                    f"{name} is a 24/7 music channel featuring "
                    f"popular songs and artists from {era}."
                )


            return (
                f"{name} is a 24/7 entertainment channel "
                f"featuring programming from {era}."
            )



    if "movie" in n or "movies" in n:

        return (
            f"{name} is a 24/7 movie channel featuring "
            f"related films, entertainment, and programming."
        )



    if any(x in n for x in [
        "elvis",
        "presley",
        "pacino",
        "sandler",
        "wayne",
        "stallone"
    ]):

        return (
            f"{name} is a 24/7 channel featuring "
            f"movies, performances, and related programming."
        )



    if any(x in n for x in [
        "horror",
        "friday",
        "halloween",
        "nightmare",
        "ghost",
        "monster",
        "zombie",
        "fear"
    ]):

        return (
            f"{name} is a 24/7 horror channel featuring "
            f"horror movies, thrillers, and related content."
        )



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
        "vibes"
    ]):

        return (
            f"{name} is a 24/7 music channel featuring "
            f"related songs, artists, and programming."
        )



    if any(x in n for x in [
        "family",
        "kids",
        "cartoon",
        "anime",
        "animation"
    ]):

        return (
            f"{name} is a 24/7 family entertainment channel "
            f"featuring related shows, movies, and programming."
        )



    if any(x in n for x in [
        "yoga",
        "fitness",
        "wellness",
        "meditation",
        "relax"
    ]):

        return (
            f"{name} is a 24/7 wellness channel featuring "
            f"health, fitness, relaxation, and lifestyle programming."
        )


    return None



# -----------------------------
# Process One Channel
# -----------------------------

def process_channel(channel):

    existing = metadata_cache.get(channel)


    # Keep good metadata
    if existing and not existing.endswith(
        "is a 24/7 channel."
    ):

        return channel, existing, False



    desc = tvmaze_lookup(channel)

    if desc:
        return channel, desc, True



    desc = tmdb_lookup(channel)

    if desc:
        return channel, desc, True



    desc = smart_description(channel)

    if desc:
        return channel, desc, True



    return (
        channel,
        f"{channel} is a 24/7 channel.",
        False
    )



# -----------------------------
# Run Parallel Metadata Search
# -----------------------------

new_saved = 0
missing = 0


with ThreadPoolExecutor(max_workers=10) as executor:

    jobs = [
        executor.submit(
            process_channel,
            c
        )
        for c in channels
    ]


    for job in as_completed(jobs):

        channel, desc, saved = job.result()

        if metadata_cache.get(channel) != desc:

            metadata_cache[channel] = desc

            if saved:
                new_saved += 1


        if desc.endswith(
            "is a 24/7 channel."
        ):
            missing += 1



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


print(f"New metadata saved: {new_saved}")
print(f"Missing metadata: {missing}")



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

        start = start_date + timedelta(days=day)

        stop = start + timedelta(days=1)


        p = ET.SubElement(
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
            p,
            "title"
        )

        title.text = channel


        desc = ET.SubElement(
            p,
            "desc"
        )

        desc.text = metadata_cache[channel]



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
