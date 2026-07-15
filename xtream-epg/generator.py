import os
import requests

XTREAM_URL = os.environ["XTREAM_URL"].rstrip("/")
USERNAME = os.environ["XTREAM_USERNAME"]
PASSWORD = os.environ["XTREAM_PASSWORD"]


def main():

    url = (
        f"{XTREAM_URL}/player_api.php"
        f"?username={USERNAME}"
        f"&password={PASSWORD}"
        f"&action=get_live_categories"
    )

    response = requests.get(
        url,
        headers={
            "User-Agent": "TiviMate"
        },
        timeout=60
    )

    response.raise_for_status()

    categories = response.json()

    print(f"Found {len(categories)} categories")

    for category in categories:
        print(
            category["category_id"],
            "-",
            category["category_name"]
        )


if __name__ == "__main__":
    main()
