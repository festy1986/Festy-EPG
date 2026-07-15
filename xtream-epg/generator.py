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
        f"&action=get_live_streams"
    )

    print("Testing:")
    print(f"{XTREAM_URL}/player_api.php?action=get_live_streams")

    response = requests.get(
        url,
        headers={
            "User-Agent": "TiviMate"
        },
        timeout=60
    )

    print("Status:", response.status_code)
    print(response.text[:2000])


if __name__ == "__main__":
    main()
