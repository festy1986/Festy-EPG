import re

INPUT_FILE = "channels.txt"
OUTPUT_FILE = "channels_clean.txt"


def clean_channel(line):
    # Remove numeric ID and separator
    line = re.sub(r"^\d+\s*\|\s*", "", line)

    # Remove colon separator
    line = re.sub(r"^:\s*", "", line)

    # Remove Music Choice prefix
    line = re.sub(r"^MC:\s*", "", line, flags=re.IGNORECASE)

    # Remove section headers
    if line.startswith("##"):
        return None

    # Trim spaces
    line = line.strip()

    if not line:
        return None

    return line


channels = set()

with open(INPUT_FILE, "r", encoding="utf-8") as file:
    for line in file:
        cleaned = clean_channel(line)

        if cleaned:
            channels.add(cleaned)


# Alphabetical order
channels = sorted(channels, key=str.lower)


with open(OUTPUT_FILE, "w", encoding="utf-8") as file:
    for channel in channels:
        file.write(channel + "\n")


print(f"Created {OUTPUT_FILE}")
print(f"Total channels: {len(channels)}")
