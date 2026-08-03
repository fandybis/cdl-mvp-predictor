"""Inspect the embedded Next.js JSON from BreakingPoint."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from bs4 import BeautifulSoup


HTML_PATH = Path("data/raw/breakingpoint_stats_page.html")
JSON_PATH = Path("data/raw/breakingpoint_next_data.json")

SEARCH_TERMS = (
    "player",
    "stat",
    "season",
    "game",
    "hardpoint",
    "snd",
    "search",
    "control",
    "kd",
    "damage",
    "kp10",
)


def search_json(
    value: Any,
    path: str = "root",
    results: list[str] | None = None,
) -> list[str]:
    """Find JSON paths whose keys contain relevant statistics terms."""

    if results is None:
        results = []

    if isinstance(value, dict):
        for key, child in value.items():
            child_path = f"{path}.{key}"

            if any(term in str(key).lower() for term in SEARCH_TERMS):
                results.append(child_path)

            search_json(child, child_path, results)

    elif isinstance(value, list):
        for index, child in enumerate(value[:25]):
            search_json(child, f"{path}[{index}]", results)

    return results


def main() -> None:
    if not HTML_PATH.exists():
        raise FileNotFoundError(
            f"{HTML_PATH} does not exist. Run audit_breakingpoint.py first."
        )

    html = HTML_PATH.read_text(encoding="utf-8")
    soup = BeautifulSoup(html, "lxml")

    next_data_element = soup.select_one("script#__NEXT_DATA__")

    if next_data_element is None or not next_data_element.string:
        raise RuntimeError("No usable __NEXT_DATA__ JSON was found.")

    next_data = json.loads(next_data_element.string)

    JSON_PATH.write_text(
        json.dumps(next_data, indent=2),
        encoding="utf-8",
    )

    print(f"Saved formatted JSON to: {JSON_PATH}")

    print("\nTop-level keys")
    print("-" * 50)

    for key in next_data:
        print(key)

    print("\nNext.js metadata")
    print("-" * 50)
    print(f"Page: {next_data.get('page')}")
    print(f"Build ID: {next_data.get('buildId')}")
    print(f"Query: {next_data.get('query')}")

    matching_paths = sorted(set(search_json(next_data)))

    print("\nPotentially relevant JSON paths")
    print("-" * 50)

    if not matching_paths:
        print("No relevant paths were detected.")
    else:
        for result in matching_paths[:100]:
            print(result)

        if len(matching_paths) > 100:
            print(
                f"\nShowing 100 of {len(matching_paths)} matching paths."
            )

    serialized = json.dumps(next_data).lower()

    print("\nTerm checks")
    print("-" * 50)

    for term in SEARCH_TERMS:
        print(f"{term:<15} {'FOUND' if term in serialized else 'not found'}")


if __name__ == "__main__":
    main()
