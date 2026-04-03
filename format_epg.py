from lxml import etree
import re
from datetime import datetime

def extract_episode_and_title(text):
    if not text:
        return "", ""

    # Match S06 E14 or S06E14
    match = re.search(r'[Ss](\d+)\s*[Ee](\d+)', text)
    if match:
        s, e = match.groups()
        ep = f"S{int(s):02d}E{int(e):02d}"

        # remove episode part from string
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

    # MOVIE handling
    if "movie" in category:
        year = date[:4] if date else ""
        new_desc = f"{desc.rstrip('.')}. ({year})" if year else desc
    else:
        # Combine subtitle + desc for parsing
        combined = f"{subtitle} {desc}".strip()

        ep, ep_title = extract_episode_and_title(combined)

        airdate = format_date(date)

        # Build final string EXACTLY how you want
        first_line = ep_title if ep_title else title

        if ep:
            first_line = f"{first_line} - {ep}"

        final = f"{first_line}. {desc.rstrip('.')}"
        
        if airdate:
            final += f". ({airdate})"

        new_desc = final.strip()

    desc_node = prog.find("desc")
    if desc_node is None:
        desc_node = etree.SubElement(prog, "desc")

    desc_node.text = new_desc

tree.write("epg.xml", encoding="utf-8", xml_declaration=True)
