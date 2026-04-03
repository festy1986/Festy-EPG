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

def get_episode_code(prog, subtitle, desc):
    # 1) Prefer explicit <episode-num>
    for ep in prog.findall("episode-num"):
        value = clean(ep.text or "")
        system = (ep.get("system") or "").lower()

        m = re.search(r"[Ss](\d+)\s*[Ee](\d+)", value)
        if m:
            s, e = m.groups()
            return f"S{int(s):02d}E{int(e):02d}"

        if system == "xmltv_ns":
            m = re.match(r"(\d+)\.(\d+)\.?", value)
            if m:
                s, e = m.groups()
                return f"S{int(s)+1:02d}E{int(e)+1:02d}"

    # 2) Fallback: look in subtitle + desc
    combined = f"{subtitle} {desc}"

    m = re.search(r"[Ss](\d+)\s*[Ee](\d+)", combined)
    if m:
        s, e = m.groups()
        return f"S{int(s):02d}E{int(e):02d}"

    m = re.search(r"\b(\d+)[xX](\d+)\b", combined)
    if m:
        s, e = m.groups()
        return f"S{int(s):02d}E{int(e):02d}"

    return ""

def strip_episode_code(text):
    if not text:
        return ""
    text = re.sub(r"[Ss]\d+\s*[Ee]\d+", "", text)
    text = re.sub(r"\b\d+[xX]\d+\b", "", text)
    return clean(text)

parser = etree.XMLParser(recover=True)
tree = etree.parse("epg.xml", parser)
root = tree.getroot()

for prog in root.findall("programme"):
    show_title = clean(prog.findtext("title") or "")
    subtitle = clean(prog.findtext("sub-title") or "")
    desc = clean(prog.findtext("desc") or "")
    date = clean(prog.findtext("date") or "")
    category = " ".join((c.text or "") for c in prog.findall("category")).lower()

    desc_node = prog.find("desc")
    if desc_node is None:
        desc_node = etree.SubElement(prog, "desc")

    # Movies: description should be plot + (YEAR)
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

    # TV episodes:
    # - NEVER use show_title in description output
    # - ONLY use subtitle as episode title
    # - If subtitle is missing, do not replace it with show_title

    episode_title = strip_episode_code(subtitle)
    ep_code = get_episode_code(prog, subtitle, desc)

    plot = desc

    # Remove any show title leakage from plot
    if show_title:
        plot = re.sub(re.escape(show_title), "", plot, flags=re.I)

    # Remove subtitle if repeated in plot
    if subtitle:
        plot = re.sub(re.escape(subtitle), "", plot, flags=re.I)

    # Remove cleaned episode title if repeated in plot
    if episode_title:
        plot = re.sub(re.escape(episode_title), "", plot, flags=re.I)

    # Remove episode code if repeated in plot
    plot = strip_episode_code(plot)

    # Build EXACT desired format:
    # Episode Title - SxxExx. Plot description. (MM/DD/YYYY)

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

    final = line.strip()

    airdate = format_date(date)
    if airdate:
        if final:
            final += f". ({airdate})"
        else:
            final = f"({airdate})"

    desc_node.text = final

tree.write("epg.xml", encoding="utf-8", xml_declaration=True)
