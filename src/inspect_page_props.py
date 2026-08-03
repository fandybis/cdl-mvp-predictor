"""Summarize BreakingPoint's embedded Next.js page properties."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


JSON_PATH = Path("data/raw/breakingpoint_next_data.json")

STAT_KEYWORDS = (
    "kd",
    "kills",
    "deaths",
    "damage",
    "kp10",
    "kpr",
    "first_blood",
    "firstblood",
    "opening_duel",
    "engagement",
)


def format_sample(value: Any, max_characters: int = 2500) -> str:
    """Convert a value to readable JSON without printing enormous objects."""

    formatted = json.dumps(
        value,
        indent=2,
        ensure_ascii=False,
        default=str,
    )

    if len(formatted) > max_characters:
        return formatted[:max_characters] + "\n... output truncated ..."

    return formatted


def find_stat_paths(
    value: Any,
    path: str = "pageProps",
    matches: list[str] | None = None,
) -> list[str]:
    """Find dictionaries containing keys that resemble player statistics."""

    if matches is None:
        matches = []

    if ".messages" in path:
        return matches

    if isinstance(value, dict):
        lowered_keys = [str(key).lower() for key in value]

        matching_keys = sorted(
            {
                key
                for key in lowered_keys
                if any(keyword in key for keyword in STAT_KEYWORDS)
            }
        )

        if matching_keys:
            matches.append(
                f"{path} -> matching keys: {', '.join(matching_keys)}"
            )

        for key, child in value.items():
            find_stat_paths(
                child,
                f"{path}.{key}",
                matches,
            )

    elif isinstance(value, list):
        # Inspect enough records to reveal schemas without traversing
        # an unnecessarily large dataset.
        for index, child in enumerate(value[:50]):
            find_stat_paths(
                child,
                f"{path}[{index}]",
                matches,
            )

    return matches


def describe_value(name: str, value: Any) -> None:
    """Print the type, size, and representative sample of a page property."""

    print(f"\n{name}")
    print("-" * 70)
    print(f"Type: {type(value).__name__}")

    if isinstance(value, (list, dict, str)):
        print(f"Length: {len(value)}")

    if isinstance(value, list):
        if not value:
            print("The list is empty.")
            return

        print("\nFirst record:")
        print(format_sample(value[0]))

        if len(value) > 1:
            print("\nSecond record:")
            print(format_sample(value[1]))

    elif isinstance(value, dict):
        print(f"Keys: {list(value.keys())[:50]}")
        print("\nSample:")
        print(format_sample(value))

    else:
        print(f"Value: {value}")


def main() -> None:
    if not JSON_PATH.exists():
        raise FileNotFoundError(
            f"{JSON_PATH} was not found. Run inspect_next_data.py first."
        )

    next_data = json.loads(JSON_PATH.read_text(encoding="utf-8"))

    page_props = (
        next_data
        .get("props", {})
        .get("pageProps", {})
    )

    if not page_props:
        raise RuntimeError("No pageProps object was found.")

    print("pageProps overview")
    print("=" * 70)

    for key, value in page_props.items():
        size = len(value) if isinstance(value, (list, dict, str)) else "N/A"

        print(
            f"{key:<30} "
            f"type={type(value).__name__:<10} "
            f"size={size}"
        )

    targets = (
        "allPlayers",
        "allSeasons",
        "allMaps",
        "allTeams",
    )

    for target in targets:
        if target in page_props:
            describe_value(target, page_props[target])
        else:
            print(f"\n{target}: not present")

    stat_paths = sorted(set(find_stat_paths(page_props)))

    print("\nPotential statistical data paths")
    print("=" * 70)

    if not stat_paths:
        print("No dictionaries with statistical-looking keys were found.")
    else:
        for match in stat_paths[:100]:
            print(match)

        if len(stat_paths) > 100:
            print(
                f"\nShowing 100 of {len(stat_paths)} possible paths."
            )


if __name__ == "__main__":
    main()
