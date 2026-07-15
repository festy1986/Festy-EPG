import os
import json
import html
import re
import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from concurrent.futures import ThreadPoolExecutor, as_completed


INPUT_FILE = "channels.txt"
OUTPUT_FILE = "guides/24-7.xml"
CACHE_FILE = "metadata_cache.json"

TMDB_API_KEY = os.environ.get("TMDB_API_KEY", "")

MAX_THREADS = 10


os.makedirs("guides", exist_ok=True)


# -----------------------------
# Load metadata cache
# -----------------------------

if os.path.exists(CACHE_FILE):
    with open(CACHE_FILE, "r", encoding="utf-8") as f:
        metadata_cache = json.load(f)
else:
    metadata_cache = {}


# -----------------------------
# Read channels
# -----------------------------

channels = []

with open(INPUT_FILE, "r", encoding="utf-8") as f:
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


print(f"Channels loaded: {len(channels)}")


# -----------------------------
# Cleaning
# -----------------------------

def clean(text):

    if not text:
        return None

    text = html.unescape(text)
    text = re.sub("<.*?>", "", text)

    return text.strip()



# -----------------------------
# Metadata lookups
# -----------------------------

def tvmaze(channel):

    try:

        r = requests.get(
            "https://api.tvmaze.com/singlesearch/shows",
            params={"q": channel},
            timeout=5
        )

        if r.status_code == 200:

            data = r.json()

            return clean(
                data.get("summary")
            )

    except:
        pass

    return None



def tmdb(channel):

    if not TMDB_API_KEY:
        return None

    try:

        r = requests.get(
            "https://api.themoviedb.org/3/search/multi",
            params={
                "api_key": TMDB_API_KEY,
                "query": channel
            },
            timeout=5
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



def lookup(channel):

    # use cache first
    if channel in metadata_cache:
        return channel, metadata_cache[channel], False


    desc = tvmaze(channel)

    if not desc:
        desc = tmdb(channel)


    if desc:

        return channel, desc, True


    # fallback only
    return (
        channel,
        f"{channel} is a 24/7 channel.",
        False
    )



# -----------------------------
# Run lookups simultaneously
# -----------------------------

new_metadata = 0
missing = 0


with ThreadPoolExecutor(
    max_workers=MAX_THREADS
) as executor:


    futures = [
        executor.submit(
            lookup,
            channel
        )
        for channel in channels
    ]


    for future in as_completed(futures):

        channel, desc, new = future.result()


        if new:

            metadata_cache[channel] = desc
            new_metadata += 1


        if desc.endswith(
            "is a 24/7 channel."
        ):

            missing += 1


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


print("")
print(
    f"New metadata saved: {new_metadata}"
)

print(
    f"Missing metadata: {missing}"
)



# -----------------------------
# Build XML
# -----------------------------

tv = ET.Element(
    "tv",
    {
        "generator-info-name":
        "24/7"
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


    description = metadata_cache.get(
        channel,
        f"{channel} is a 24/7 channel."
    )


    for day in range(7):

        start = (
            start_date
            +
            timedelta(days=day)
        )

        stop = start + timedelta(
            days=1
        )


        programme = ET.SubElement(
            tv,
            "programme",
            {
                "start":
                start.strftime(
                    "%Y%m%d%H%M%S +0000"
                ),

                "stop":
                stop.strftime(
                    "%Y%m%d%H%M%S +0000"
                ),

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
print(
    f"Channels: {len(channels)}"
)
