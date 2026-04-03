from lxml import etree
import re
from datetime import datetime

def clean(text):
    if not text:
        return ""
    text = re.sub(r"\s+", " ", text)
    return text.strip(" .-")

def format_date(date_str):
    if not date_str:
        return ""
    try:
        d = datetime.strptime(date_str[:8], "%Y%m%d")
        return d.strftime("%m/%d/%Y")
    except:
        return ""

def get_episode_code(text):
    if not text:
        return ""
    m = re.search(r"[Ss](\d+)\s*[Ee](\d+)", text)
    if m:
        s, e = m.groups()
        return f"S{int(s):02d}E{int(e):02d}"
    return ""

parser = etree.XMLParser(recover=True)
tree = etree.parse("epg.xml", parser)
root = tree.getroot()

for prog in root.findall("programme"):

    subtitle = clean(prog.findtext("sub-title") or "")
    desc = clean(prog.findtext("desc") or "")
    date = clean(prog.findtext("date") or "")
    category = " ".join([(c.text or "") for c in prog.findall("category")]).lower()

    desc_node = prog.find("desc")
    if desc_node is None:
        desc_node = etree.SubElement(prog, "desc")

    # MOVIES
    if "movie" in category:
        year = date[:4] if len(date) >= 4 else ""
        plot = clean(desc)
        if plot and year:
            desc_node.text = f"{plot}. ({year})"
        elif year:
            desc_node.text = f"({year})"
        else:
            desc_node.text = plot
        continue

    # TV EPISODES (STRICT)

    episode_title = subtitle  # ONLY source
    ep_code = get_episode_code(f"{subtitle} {desc}")

    # Clean plot
    plot = desc
    if subtitle:
        plot = re.sub(re.escape(subtitle), "", plot, flags=re.I)
    plot = re.sub(r"[Ss]\d+\s*[Ee]\d+", "", plot)
    plot = clean(plot)

    # Build EXACT format
    line = ""

    if episode_title:
        if ep_code:
            line = f"{episode_title} - {ep_code}"
        else:
            line = episode_title
    elif ep_code:
        line = ep_code

    if plot:
        if line:
            line += f". {plot}"
        else:
            line = plot

    airdate = format_date(date)
    if airdate:
        if line:
            line += f". ({airdate})"
        else:
            line = f"({airdate})"

    desc_node.text = line.strip()

tree.write("epg.xml", encoding="utf-8", xml_declaration=True)
