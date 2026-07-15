import re


INPUT_FILE = "channels.txt"
OUTPUT_FILE = "channels_clean.txt"


def clean_name(line):

    # Remove ID at the beginning
    line = re.sub(r"^\d+\s*\|\s*", "", line)

    # Remove the category prefix
    line = re.sub(r"^:\s*", "", line)

    # Remove MC: prefix
    line = re.sub(r"^MC:\s*", "", line, flags=re.IGNORECASE)

    # Remove category headers
    if "##" in line:
        return None

    # Clean spaces
    line = line.strip()

    if not line:
        return None

    return line


def main():

    channels = set()

    with open(INPUT_FILE, "r", encoding="utf-8") as f:

        for line in f:

            cleaned = clean_name(line)

            if cleaned:
                channels.add(cleaned)


    # Alphabetical sort
    channels = sorted(channels, key=str.lower)


    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:

        for channel in channels:
            f.write(channel + "\n")


    print(f"Cleaned {len(channels)} channels")
    print(f"Saved to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
