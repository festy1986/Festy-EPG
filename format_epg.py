from lxml import etree
import re
from datetime import datetime

def extract_episode(text):
    if not text:
        return "", text

    match = re.search(r'[Ss](\d+)\s*[Ee](\d+)', text)
    if match:
        s, e = match.groups()
        ep = f"S{int(s):02d}E{int(e):02d}"
        cleaned = re.sub(r'[Ss]\d+\s*[Ee]\d+', '', text).strip()
        cleaned = re.sub(r'^\s*[-:.]+\s*', '', cleaned).strip()
        return ep, cleaned

    return "", text.strip()

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
    category = " ".join([c.text or "" for c in prog.findall("category")]).lower()

    if "movie" in category:
        year = date[:4] if len(date) >= 4 else ""
        clean_desc = desc.rstrip(". ").strip()
        if year and clean_desc:
            new_desc = f"{clean_desc}. ({year})"
        elif year:
            new_desc = f"({year})"
        else:
            new_desc = clean_desc
    else:
        ep, clean_subtitle = extract_episode(subtitle)

        episode_title = clean_subtitle if clean_subtitle else title

        clean_desc = desc.strip()

        if subtitle:
            clean_desc = re.sub(re.escape(subtitle), '', clean_desc, flags=re.I).strip()

        if clean_subtitle:
            clean_desc = re.sub(re.escape(clean_subtitle), '', clean_desc, flags=re.I).strip()

        clean_desc = re.sub(r'[Ss]\d+\s*[Ee]\d+', '', clean_desc).strip()
        clean_desc = re.sub(r'\s+', ' ', clean_desc).strip(" .-")

        final = episode_title

        if ep:
            final += f" - {ep}"

        if clean_desc:
            final += f". {clean_desc}"

        airdate = format_date(date)
        if airdate:
            final += f". ({airdate})"

        new_desc = final.strip()

    desc_node = prog.find("desc")
    if desc_node is None:
        desc_node = etree.SubElement(prog, "desc")
    desc_node.text = new_desc

tree.write("epg.xml", encoding="utf-8", xml_declaration=True)
