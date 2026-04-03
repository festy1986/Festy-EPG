from lxml import etree
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
    if not date_str:
        return ""
    try:
        d = datetime.strptime(date_str[:8], "%Y%m%d")
        return d.strftime("%m/%d/%Y")
    except:
        return ""

parser = etree.XMLParser(recover=True, encoding="utf-8")
tree = etree.parse("epg.xml", parser)
root = tree.getroot()

for prog in root.findall("programme"):
    title = prog.findtext("title", default="") or ""
    desc = prog.findtext("desc", default="") or ""
    subtitle = prog.findtext("sub-title", default="") or ""
    date = prog.findtext("date", default="") or ""
    category = prog.findtext("category", default="") or ""

    ep = normalize_episode(f"{subtitle} {desc}")
    is_movie = "movie" in category.lower()

    desc = desc.strip().rstrip(".")
    subtitle = subtitle.strip()
    title = title.strip()

    if is_movie:
        year = date[:4] if len(date) >= 4 else ""
        if year:
            new_desc = f"{desc}. ({year})" if desc else f"({year})"
        else:
            new_desc = desc
    else:
        airdate = format_date(date)
        first_part = subtitle if subtitle else title

        if ep:
            first_part = f"{first_part} - {ep}"

        if desc:
            new_desc = f"{first_part}. {desc}. "
        else:
            new_desc = f"{first_part}. "

        if airdate:
            new_desc += f"({airdate})"

        new_desc = new_desc.strip()

    desc_node = prog.find("desc")
    if desc_node is None:
        desc_node = etree.SubElement(prog, "desc")
    desc_node.text = new_desc

tree.write("epg.xml", encoding="utf-8", xml_declaration=True)
