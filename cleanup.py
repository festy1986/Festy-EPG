import re

INPUT_FILE = "channels.txt"
OUTPUT_FILE = "channels_clean.txt"


def clean_name(line):

    # Remove ID and separator
    line = re.sub(r"^\d+\s*\|\s*", "", line)

    # Remove leading colon separator
    line = re.sub(r"^:\s*", "", line)

    # Remove MC: prefix
    line = re.sub(r"^MC:\s*", "", line, flags=re.IGNORECASE)

    # Remove category headers
    if line.strip().startswith("##"):
        return None

    # Remove extra spaces
    line = line.strip()

    if not line:
        return None

    return line


def main():

    channels = set()

    with open(INPUT_FILE, "r", encoding="utf-8") as file:
        for line in file:
            name = clean_name(line)

            if name:
                channels.add(name)


    # Sort alphabetically
    channels = sorted(channels, key=str.lower)


    with open(OUTPUT_FILE, "w", encoding="utf-8") as file:
        for channel in channels:
            file.write(channel + "\n")


    print(f"Created {OUTPUT_FILE}")
    print(f"Total channels: {len(channels)}")


if __name__ == "__main__":
    main()
