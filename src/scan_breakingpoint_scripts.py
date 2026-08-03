"""Download and scan BreakingPoint JavaScript for statistics API procedures."""

from __future__ import annotations

import re
from pathlib import Path
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup


HTML_PATH = Path("data/raw/breakingpoint_stats_page.html")
OUTPUT_DIR = Path("data/raw/breakingpoint_js")

SEARCH_TERMS = (
    "opening duel",
    "openingduel",
    "first blood",
    "firstblood",
    "kp10",
    "kills per 10",
    "damage per 10",
    "damageper10",
    "playerstats",
    "player stats",
    "advancedstats",
    "advanced stats",
    "fetchstats",
    "fetchplayer",
    "getstats",
    "statstable",
    "seasonstats",
    "snd_kd",
    "hp_kd",
    "ctl_kd",
    "trpc",
    "/api/trpc",
)

TRPC_PATTERN = re.compile(
    r"""["']([A-Za-z0-9_-]+(?:\.[A-Za-z0-9_-]+){1,6})["']"""
)


def safe_filename(url: str, index: int) -> str:
    """Create a filesystem-safe name for a JavaScript URL."""

    path_name = Path(urlparse(url).path).name or f"script_{index}.js"
    clean_name = re.sub(r"[^A-Za-z0-9._-]", "_", path_name)

    return f"{index:02d}_{clean_name}"


def context_snippet(
    text: str,
    position: int,
    radius: int = 220,
) -> str:
    """Return readable text surrounding a keyword match."""

    start = max(0, position - radius)
    end = min(len(text), position + radius)

    snippet = text[start:end]
    snippet = snippet.replace("\n", " ").replace("\r", " ")

    return re.sub(r"\s+", " ", snippet)


def main() -> None:
    if not HTML_PATH.exists():
        raise FileNotFoundError(
            f"{HTML_PATH} was not found. Run audit_breakingpoint.py first."
        )

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    html = HTML_PATH.read_text(encoding="utf-8")
    soup = BeautifulSoup(html, "lxml")

    script_urls = [
        urljoin(
            "https://breakingpoint.gg/stats",
            script["src"],
        )
        for script in soup.find_all("script", src=True)
    ]

    print(f"Found {len(script_urls)} external JavaScript files.")

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 Chrome/130 Safari/537.36"
        )
    }

    keyword_hits: list[tuple[str, str, str]] = []
    possible_procedures: set[str] = set()

    for index, script_url in enumerate(script_urls, start=1):
        print(f"Downloading {index}/{len(script_urls)}: {script_url}")

        try:
            response = requests.get(
                script_url,
                headers=headers,
                timeout=30,
            )
            response.raise_for_status()
        except requests.RequestException as exc:
            print(f"  Failed: {exc}")
            continue

        script_text = response.text

        output_path = OUTPUT_DIR / safe_filename(script_url, index)
        output_path.write_text(script_text, encoding="utf-8")

        lowered = script_text.lower()

        for term in SEARCH_TERMS:
            start = 0

            while True:
                position = lowered.find(term, start)

                if position == -1:
                    break

                keyword_hits.append(
                    (
                        output_path.name,
                        term,
                        context_snippet(script_text, position),
                    )
                )

                start = position + len(term)

                # Prevent one heavily repeated term from flooding output.
                if sum(
                    1
                    for filename, found_term, _ in keyword_hits
                    if filename == output_path.name
                    and found_term == term
                ) >= 5:
                    break

        for match in TRPC_PATTERN.finditer(script_text):
            candidate = match.group(1)
            lowered_candidate = candidate.lower()

            if any(
                keyword in lowered_candidate
                for keyword in (
                    "stat",
                    "player",
                    "leader",
                    "season",
                    "advanced",
                    "game",
                )
            ):
                possible_procedures.add(candidate)

    print("\nKeyword matches")
    print("=" * 80)

    if not keyword_hits:
        print("No relevant keyword matches were found.")
    else:
        for filename, term, snippet in keyword_hits[:100]:
            print(f"\nFile: {filename}")
            print(f"Term: {term}")
            print(f"Context: {snippet}")

        if len(keyword_hits) > 100:
            print(
                f"\nShowing 100 of {len(keyword_hits)} keyword matches."
            )

    print("\nPossible tRPC procedure or object names")
    print("=" * 80)

    if not possible_procedures:
        print("No likely procedure names were detected.")
    else:
        for procedure in sorted(possible_procedures):
            print(procedure)


if __name__ == "__main__":
    main()
