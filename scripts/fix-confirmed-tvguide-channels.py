from pathlib import Path
import re

FILE = Path("guides/tvguide.xml")

confirmed = {
    "CNN.us": ("9100002976#9233013812", "CNN"),
    "FX.us": ("9100002976#9200006932", "FX"),
    "MTV.us": ("9100002976#9200014754", "MTV"),
    "SHOWTIME.SHOWCASE.us": ("9100002976#9233003805", "SHOWTIME SHOWCASE"),
    "FREEFRM.us": ("9100002976#9200006942", "FREEFORM"),
    "HBO.MOVIES.us": ("9100002976#9233009866", "HBO MOVIES"),
    "HBO.us": ("9100002976#9200004886", "HBO"),
}

text = FILE.read_text(encoding="utf-8")

def channel_line(xmltv_id, site_id, name):
    return f'  <channel site="tvguide.com" lang="en" xmltv_id="{xmltv_id}" site_id="{site_id}">{name}</channel>'

# Replace or add confirmed channels
for xmltv_id, (site_id, name) in confirmed.items():
    new_line = channel_line(xmltv_id, site_id, name)

    pattern = re.compile(
        rf'\s*<channel site="tvguide\.com" lang="en" xmltv_id="{re.escape(xmltv_id)}" site_id="[^"]+">[^<]*</channel>',
        re.MULTILINE,
    )

    if pattern.search(text):
        text = pattern.sub("\n" + new_line, text, count=1)
    else:
        text = text.replace("</channels>", new_line + "\n</channels>")

# 🔥 Clean ALL duplicate HBO.us entries first
hbo_pattern = re.compile(
    r'\s*<channel site="tvguide\.com" lang="en" xmltv_id="HBO\.us" site_id="[^"]+">[^<]*</channel>',
    re.MULTILINE,
)

text = hbo_pattern.sub("", text)

# ✅ Add back ONLY the correct HBO main
hbo_line = channel_line("HBO.us", confirmed["HBO.us"][0], confirmed["HBO.us"][1])
text = text.replace("</channels>", hbo_line + "\n</channels>")

FILE.write_text(text.strip() + "\n", encoding="utf-8")

print("✅ Updated channels:")
for xmltv_id, (site_id, name) in confirmed.items():
    print(f"{xmltv_id} -> {site_id} -> {name}")
