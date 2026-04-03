from lxml import etree
import re
from datetime import datetime

def extract_episode(text):
    if not text:
        return "", text

    # Find S06E14 or S06 E14
    match = re.search(r'[Ss](\d+)\s*[Ee](\d+)', text)
    if match:
        s, e = match.groups()
        ep = f"S{int(s):02d}E{int(e):02d}"

        # Remove episode code from text
        cleaned = re.sub(r'[Ss]\d+\s*[Ee]\d+', '', text).strip()
        return ep, cleaned

    return "", text

def format_date(date_str):
    if not date_str:
        return ""
    try:
        d = datetime.strptime(date_str[:8], "%Y%m%d")
        return d.strftime("%m/%d/%Y")
    except:
        return ""

parser = etree.XMLParser(recover=True)
tree = etree.parse("epg.xml", parser)
root = tree.getroot()

for prog in root.findall("programme"):
    title = (prog.findtext("title") or "").strip()
    desc = (prog.findtext("desc") or "").strip()
    subtitle = (prog.findtext("sub-title") or "").strip()
    date = (prog.findtext("date") or "").strip()
    category = (prog.findtext("category") or "").lower()

    # MOVIES
    if "movie" in category:
        year = date[:4] if date else ""
        new_desc = f"{title}. ({year})" if year else title

    else:
        # STEP 1: Extract episode + clean subtitle
        ep, clean_sub = extract_episode(subtitle)

        # STEP 2: Pick best episode title
        episode_title = clean_sub if clean_sub else title

        # STEP 3: Clean description (remove duplicates)
        desc_clean = desc

        # Remove subtitle if duplicated inside description
        if episode_title.lower() in desc_clean.lower():
            desc_clean = desc_clean.replace(episode_title, "").strip()

        # Remove episode pattern from desc
        desc_clean = re.sub(r'[Ss]\d+\s*[Ee]\d+', '', desc_clean).strip()

        # STEP 4: Build final line
        line = episode_title

        if ep:
            line += f" - {ep}"

        if desc_clean:
            line += f". {desc_clean}"

        airdate = format_date(date)
        if airdate:
            line += f". ({airdate})"

        new_desc = line.strip()

    # Replace description completely
    desc_node = prog.find("desc")
    if desc_node is None:
        desc_node = etree.SubElement(prog, "desc")

    desc_node.text = new_desc

tree.write("epg.xml", encoding="utf-8", xml_declaration=True)
