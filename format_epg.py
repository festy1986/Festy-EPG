import xml.etree.ElementTree as ET
import re

tree = ET.parse("epg.xml")
root = tree.getroot()

for programme in root.findall("programme"):

    title = programme.find("title")
    desc = programme.find("desc")
    episode = programme.find("episode-num")

    if desc is None:
        continue

    desc_text = desc.text or ""

    # --- STEP 1: Extract SXXEXX ---
    season_episode = ""
    if episode is not None and episode.text:
        match = re.search(r"\.(\d+)\.(\d+)\.", episode.text)
        if match:
            s = int(match.group(1)) + 1
            e = int(match.group(2)) + 1
            season_episode = f"S{s:02d}E{e:02d}"

    # --- STEP 2: Remove SHOW NAME if it's at the start ---
    if title is not None and title.text:
        show_name = title.text.strip()
        if desc_text.startswith(show_name):
            desc_text = desc_text[len(show_name):].strip(". ").strip()

    # --- STEP 3: Extract EPISODE TITLE (first sentence part) ---
    parts = desc_text.split(". ", 1)

    if len(parts) > 1:
        episode_title = parts[0].strip()
        plot = parts[1].strip()
    else:
        episode_title = ""
        plot = desc_text.strip()

    # --- STEP 4: Build FINAL FORMAT ---
    if season_episode and episode_title:
        new_desc = f"{episode_title} - {season_episode}. {plot}"
    elif season_episode:
        new_desc = f"{season_episode}. {plot}"
    else:
        new_desc = plot

    desc.text = new_desc

tree.write("epg.xml", encoding="utf-8", xml_declaration=True)
