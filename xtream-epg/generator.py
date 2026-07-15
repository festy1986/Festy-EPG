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
    )

    print("Testing Xtream connection...")
    print("Server:", XTREAM_URL)

    response = requests.get(
        url,
        headers={
            "User-Agent": "TiviMate"
        },
        timeout=30
    )

    print("Status:", response.status_code)
    print("Response:")
    print(response.text[:1000])


if __name__ == "__main__":
    main()
