"""Find BO6 players excluded by BreakingPoint's current-team filter."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd


UNFILTERED_PATH = Path(
    "data/raw/breakingpoint_bo6_player_stats_unfiltered.json"
)

FILTERED_PATH = Path(
    "data/raw/breakingpoint_bo6_player_stats.json"
)

OUTPUT_PATH = Path(
    "data/interim/bo6_excluded_players.csv"
)


def load_records(path: Path) -> pd.DataFrame:
    """Load a saved BreakingPoint JSON response."""

    if not path.exists():
        raise FileNotFoundError(
            f"{path} does not exist."
        )

    records = json.loads(
        path.read_text(encoding="utf-8")
    )

    if not isinstance(records, list):
        raise RuntimeError(
            f"{path} does not contain a list."
        )

    return pd.DataFrame(records)


def preview_value(value: Any, limit: int = 500) -> str:
    """Create a short representation of a nested field."""

    try:
        text = json.dumps(
            value,
            ensure_ascii=False,
            default=str,
        )
    except TypeError:
        text = str(value)

    if len(text) > limit:
        return text[:limit] + " ..."

    return text


def main() -> None:
    unfiltered = load_records(
        UNFILTERED_PATH
    )

    filtered = load_records(
        FILTERED_PATH
    )

    print("Dataset comparison")
    print("=" * 76)
    print(f"Unfiltered players: {len(unfiltered)}")
    print(f"Filtered players:   {len(filtered)}")

    if "player_id" not in unfiltered.columns:
        raise RuntimeError(
            "The unfiltered data has no player_id column."
        )

    if "player_id" not in filtered.columns:
        raise RuntimeError(
            "The filtered data has no player_id column."
        )

    team_related_columns = [
        column
        for column in unfiltered.columns
        if any(
            keyword in column.lower()
            for keyword in (
                "team",
                "roster",
                "event",
                "division",
                "league",
            )
        )
    ]

    print("\nTeam, event, and league-related columns")
    print("=" * 76)

    if not team_related_columns:
        print("None found")
    else:
        for column in team_related_columns:
            print(column)

    filtered_player_ids = set(
        filtered["player_id"].tolist()
    )

    excluded = unfiltered[
        ~unfiltered["player_id"].isin(
            filtered_player_ids
        )
    ].copy()

    numeric_columns = [
        "game_count",
        "hp_game_count",
        "snd_game_count",
        "ctl_game_count",
        "kd",
        "bp_rating",
    ]

    for column in numeric_columns:
        if column in excluded.columns:
            excluded[column] = pd.to_numeric(
                excluded[column],
                errors="coerce",
            )

    excluded = excluded.sort_values(
        "game_count",
        ascending=False,
    )

    OUTPUT_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    excluded.to_csv(
        OUTPUT_PATH,
        index=False,
    )

    print("\nExcluded-player summary")
    print("=" * 76)
    print(f"Excluded players: {len(excluded)}")
    print(f"Saved to: {OUTPUT_PATH}")

    display_columns = [
        column
        for column in [
            "player_id",
            "player_tag",
            "game_count",
            "hp_game_count",
            "snd_game_count",
            "ctl_game_count",
            "kd",
            "bp_rating",
            *team_related_columns,
        ]
        if column in excluded.columns
    ]

    print("\nAll excluded players")
    print("=" * 76)

    print(
        excluded[display_columns]
        .to_string(index=False)
    )

    established_excluded = excluded[
        excluded["game_count"] >= 50
    ]

    print("\nExcluded players with at least 50 maps")
    print("=" * 76)

    if established_excluded.empty:
        print("None")
    else:
        print(
            established_excluded[
                display_columns
            ].to_string(index=False)
        )

    print("\nSamples from nested team-related fields")
    print("=" * 76)

    if not team_related_columns:
        print("No team-related fields available.")
    else:
        for column in team_related_columns:
            non_null = unfiltered[column].dropna()

            print(f"\nColumn: {column}")

            if non_null.empty:
                print("No non-null values")
                continue

            for value in non_null.head(3):
                print(preview_value(value))


if __name__ == "__main__":
    main()
