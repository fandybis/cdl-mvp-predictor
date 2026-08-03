"""Inspect how BreakingPoint serves its player-statistics page."""

from pathlib import Path
from urllib.parse import urljoin
import sys

import requests
from bs4 import BeautifulSoup


STATS_URL = "https://breakingpoint.gg/stats"

EXPECTED_LABELS = [
    "K/D",
    "Hardpoint K/D",
    "Hardpoint KP10M",
    "Hardpoint DMG/10M",
    "SND K/D",
    "SND KPR",
    "SND Opening Duel Win %",
    "Control K/D",
    "Control KP10M",
    "Control DMG/10M",
]


def main() -> None:
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 Chrome/130 Safari/537.36"
        )
    }

    print(f"Requesting: {STATS_URL}")

    try:
        response = requests.get(
            STATS_URL,
            headers=headers,
            timeout=30,
        )
    except requests.RequestException as exc:
        print(f"Request failed: {exc}")
        sys.exit(1)

    print(f"Status code: {response.status_code}")
    print(f"Content type: {response.headers.get('content-type')}")
    print(f"Response size: {len(response.content):,} bytes")

    if response.status_code != 200:
        print("The page did not return HTTP 200.")
        sys.exit(1)

    output_path = Path("data/raw/breakingpoint_stats_page.html")
    output_path.write_text(response.text, encoding="utf-8")
    print(f"Saved page HTML to: {output_path}")

    soup = BeautifulSoup(response.text, "lxml")
    page_text = soup.get_text(" ", strip=True)

    print("\nExpected statistic labels")
    print("-" * 40)

    for label in EXPECTED_LABELS:
        result = "FOUND" if label.lower() in page_text.lower() else "not found"
        print(f"{label:<32} {result}")

    tables = soup.find_all("table")
    rows = soup.select("table tbody tr")

    print("\nHTML structure")
    print("-" * 40)
    print(f"Tables found: {len(tables)}")
    print(f"Rendered table rows found: {len(rows)}")

    scripts = [
        urljoin(STATS_URL, script["src"])
        for script in soup.find_all("script", src=True)
    ]

    print(f"External scripts found: {len(scripts)}")
    for script_url in scripts[:10]:
        print(f"  {script_url}")

    next_data = soup.select_one("script#__NEXT_DATA__")
    print(
        "Embedded Next.js data: "
        + ("FOUND" if next_data is not None else "not found")
    )

    possible_api_links = sorted(
        {
            urljoin(STATS_URL, element["href"])
            for element in soup.find_all("a", href=True)
            if "api" in element["href"].lower()
        }
    )

    print("\nPossible API links")
    print("-" * 40)

    if possible_api_links:
        for api_link in possible_api_links:
            print(api_link)
    else:
        print("No obvious API links found in the HTML.")

    if rows:
        print("\nResult: table data appears in the returned HTML.")
    elif next_data:
        print("\nResult: player data may be embedded in Next.js JSON.")
    else:
        print(
            "\nResult: the table is probably populated by browser-side "
            "JavaScript or a separate API request."
        )


if __name__ == "__main__":
    main()
