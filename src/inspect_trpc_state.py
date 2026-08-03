"""Inspect BreakingPoint's embedded tRPC state for statistics queries."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


NEXT_DATA_PATH = Path("data/raw/breakingpoint_next_data.json")
TRPC_OUTPUT_PATH = Path("data/raw/breakingpoint_trpc_state.json")

SEARCH_TERMS = (
    "player",
    "stat",
    "advanced",
    "leaderboard",
    "season",
    "event",
    "match",
    "hardpoint",
    "search",
    "control",
    "query",
    "procedure",
)


def preview(value: Any, limit: int = 600) -> str:
    """Return a shortened JSON representation."""

    text = json.dumps(
        value,
        ensure_ascii=False,
        default=str,
    )

    if len(text) > limit:
        return text[:limit] + " ..."

    return text


def inspect_structure(
    value: Any,
    path: str = "trpcState",
    depth: int = 0,
    max_depth: int = 8,
) -> None:
    """Print the structure of nested tRPC data."""

    indent = "  " * depth

    if depth > max_depth:
        print(f"{indent}{path}: maximum depth reached")
        return

    if isinstance(value, dict):
        keys = list(value.keys())

        print(
            f"{indent}{path}: dict "
            f"({len(keys)} keys: {keys[:20]})"
        )

        for key, child in value.items():
            inspect_structure(
                child,
                f"{path}.{key}",
                depth + 1,
                max_depth,
            )

    elif isinstance(value, list):
        print(f"{indent}{path}: list ({len(value)} items)")

        for index, child in enumerate(value[:5]):
            inspect_structure(
                child,
                f"{path}[{index}]",
                depth + 1,
                max_depth,
            )

        if len(value) > 5:
            print(
                f"{indent}  ... skipped {len(value) - 5} additional items"
            )

    else:
        print(
            f"{indent}{path}: "
            f"{type(value).__name__} = {preview(value)}"
        )


def find_relevant_strings(
    value: Any,
    path: str = "trpcState",
    results: list[str] | None = None,
) -> list[str]:
    """Locate strings containing words related to player statistics."""

    if results is None:
        results = []

    if isinstance(value, dict):
        for key, child in value.items():
            child_path = f"{path}.{key}"

            if any(term in str(key).lower() for term in SEARCH_TERMS):
                results.append(
                    f"{child_path} [matching key]"
                )

            find_relevant_strings(child, child_path, results)

    elif isinstance(value, list):
        for index, child in enumerate(value):
            find_relevant_strings(
                child,
                f"{path}[{index}]",
                results,
            )

    elif isinstance(value, str):
        lowered = value.lower()

        if any(term in lowered for term in SEARCH_TERMS):
            results.append(
                f"{path} = {value[:300]}"
            )

    return results


def main() -> None:
    if not NEXT_DATA_PATH.exists():
        raise FileNotFoundError(
            f"{NEXT_DATA_PATH} was not found."
        )

    next_data = json.loads(
        NEXT_DATA_PATH.read_text(encoding="utf-8")
    )

    page_props = (
        next_data
        .get("props", {})
        .get("pageProps", {})
    )

    trpc_state = page_props.get("trpcState")

    if trpc_state is None:
        raise RuntimeError("No trpcState object was found.")

    TRPC_OUTPUT_PATH.write_text(
        json.dumps(
            trpc_state,
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    print(f"Saved tRPC state to: {TRPC_OUTPUT_PATH}")

    print("\ntRPC structure")
    print("=" * 70)
    inspect_structure(trpc_state)

    matches = sorted(set(find_relevant_strings(trpc_state)))

    print("\nRelevant keys and strings")
    print("=" * 70)

    if not matches:
        print("No relevant keys or strings were found.")
    else:
        for match in matches[:100]:
            print(match)

        if len(matches) > 100:
            print(
                f"\nShowing 100 of {len(matches)} matches."
            )


if __name__ == "__main__":
    main()
