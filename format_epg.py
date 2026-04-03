import xml.etree.ElementTree as ET
import re
from datetime import datetime

def normalize_episode(text):
    if not text:
        return ""

    patterns = [
        r'[Ss](\d+)[Ee](\d+)',
        r'(\d+)[xX](\d+)',
        r'Season\s*(\d+).*Episode\s*(\d+)'
    ]

    for p in patterns:
        m = re.search(p, text, re.I)
        if m:
            s, e = m.groups()
            return f"S{int(s):02d}E{int(e):02d}"

    return ""

def format_date(date_str):
    try:
        d = datetime.strptime(date_str[:8], "%Y%m%d")
        return d.strftime("%m/%d/%Y")
    except:
        return ""

tree = ET.parse("epg.xml")
root = tree.getroot()

for prog in root.findall("programme"):
    title = prog.findtext("title", "")
    desc = prog.findtext("desc", "")
    subtitle = prog.findtext("sub-title", "")
    date = prog.findtext("date", "")

    category = prog.findtext("category", "").lower()

    # Try to extract episode
    ep = normalize_episode(desc + " " + subtitle)

    # Detect movie
    is_movie = "movie" in category

    if is_movie:
        year = date[:4] if date else ""
        new_desc = f"{desc.strip()} ({year})"
        prog.find("desc").text = new_desc
    else:
        airdate = format_date(date)

        first_line = subtitle if subtitle else title
        if ep:
            first_line += f" - {ep}."

        new_desc = f"{first_line} {desc.strip()}. ({airdate})"
        prog.find("desc").text = new_desc

tree.write("epg.xml", encoding="utf-8")
