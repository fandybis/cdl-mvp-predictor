"""Evaluate participation thresholds for BO6 MVP eligibility."""

from __future__ import annotations

import math
from pathlib import Path

import pandas as pd


INPUT_PATH = Path(
    "data/processed/bo6_mvp_features.csv"
)

OUTPUT_PATH = Path(
    "data/interim/bo6_mvp_eligibility_audit.csv"
)

THRESHOLD_SHARES = [
    0.25,
    0.35,
    0.40,
    0.50,
    0.60,
]


def display_boundary(
    dataframe: pd.DataFrame,
    minimum_games: int,
) -> None:
    """Print players immediately above and below a threshold."""

    display_columns = [
        "player_tag",
        "game_count",
        "hp_game_count",
        "snd_game_count",
        "ctl_game_count",
        "kd",
        "bp_rating",
    ]

    eligible = (
        dataframe[
            dataframe["game_count"] >= minimum_games
        ]
        .sort_values(
            "game_count",
            ascending=True,
        )
        .head(6)
    )

    excluded = (
        dataframe[
            dataframe["game_count"] < minimum_games
        ]
        .sort_values(
            "game_count",
            ascending=False,
        )
        .head(6)
    )

    print("\nLowest-volume eligible players")
    print("-" * 76)

    if eligible.empty:
        print("None")
    else:
        print(
            eligible[display_columns]
            .to_string(index=False)
        )

    print("\nHighest-volume excluded players")
    print("-" * 76)

    if excluded.empty:
        print("None")
    else:
        print(
            excluded[display_columns]
            .to_string(index=False)
        )


def main() -> None:
    if not INPUT_PATH.exists():
        raise FileNotFoundError(
            f"{INPUT_PATH} does not exist. "
            "Rebuild the full feature dataset first."
        )

    dataframe = pd.read_csv(INPUT_PATH)

    count_columns = [
        "game_count",
        "hp_game_count",
        "snd_game_count",
        "ctl_game_count",
    ]

    for column in count_columns:
        dataframe[column] = pd.to_numeric(
            dataframe[column],
            errors="coerce",
        )

    dataframe = dataframe.dropna(
        subset=["player_tag", "game_count"]
    ).copy()

    maximum_games = int(
        dataframe["game_count"].max()
    )

    dataframe["participation_rate"] = (
        dataframe["game_count"]
        / maximum_games
    )

    print("BO6 MVP eligibility audit")
    print("=" * 76)
    print(f"Players in full dataset: {len(dataframe)}")
    print(f"Maximum maps played: {maximum_games}")

    print("\nThreshold summary")
    print("=" * 76)

    summary_rows = []

    for share in THRESHOLD_SHARES:
        minimum_games = math.ceil(
            maximum_games * share
        )

        eligible_count = int(
            (
                dataframe["game_count"]
                >= minimum_games
            ).sum()
        )

        summary_rows.append(
            {
                "minimum_share": share,
                "minimum_games": minimum_games,
                "eligible_players": eligible_count,
            }
        )

    summary = pd.DataFrame(summary_rows)

    print(
        summary.to_string(
            index=False,
            formatters={
                "minimum_share": (
                    lambda value: f"{value:.0%}"
                )
            },
        )
    )

    for share in THRESHOLD_SHARES:
        minimum_games = math.ceil(
            maximum_games * share
        )

        print("\n")
        print("=" * 76)
        print(
            f"Threshold: {share:.0%} of maximum maps "
            f"({minimum_games} maps)"
        )
        print("=" * 76)

        display_boundary(
            dataframe,
            minimum_games,
        )

        flag_name = (
            f"eligible_{int(share * 100)}pct"
        )

        dataframe[flag_name] = (
            dataframe["game_count"]
            >= minimum_games
        )

    dataframe = dataframe.sort_values(
        [
            "game_count",
            "player_tag",
        ],
        ascending=[
            False,
            True,
        ],
    )

    OUTPUT_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    dataframe.to_csv(
        OUTPUT_PATH,
        index=False,
    )

    print("\nAudit file created")
    print("=" * 76)
    print(OUTPUT_PATH)


if __name__ == "__main__":
    main()
