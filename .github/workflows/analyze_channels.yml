from collections import defaultdict
import re

INPUT_FILE = "channels.txt"   # change this if your file has another name

categories = defaultdict(list)

with open(INPUT_FILE, "r", encoding="utf-8", errors="ignore") as f:
    for line in f:
        line = line.strip()

        if not line:
            continue

        # expects:
        # channel_id | category_id | something | name
        parts = [x.strip() for x in line.split("|")]

        if len(parts) < 3:
            continue

        channel_id = parts[0]
        category_id = parts[1]

        name = parts[-1]

        categories[category_id].append({
            "id": channel_id,
            "name": name
        })


print("\nCATEGORY SUMMARY")
print("=" * 50)

for cat, items in sorted(categories.items(), key=lambda x: len(x[1]), reverse=True):
    print(f"Category {cat}: {len(items)} channels")


print("\n\nSAMPLE CHANNELS BY CATEGORY")
print("=" * 50)

for cat, items in sorted(categories.items(), key=lambda x: len(x[1]), reverse=True):

    print(f"\n--- CATEGORY {cat} ({len(items)}) ---")

    for item in items[:10]:
        print(f"{item['id']} | {item['name']}")
