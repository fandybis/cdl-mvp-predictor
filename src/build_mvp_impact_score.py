"""Build a transparent BO6 CDL MVP Impact Score."""

from __future__ import annotations

import math
from pathlib import Path

import pandas as pd


INPUT_PATH = Path(
    "data/processed/bo6_mvp_features.csv"
)

LEADERBOARD_OUTPUT_PATH = Path(
    "data/processed/bo6_mvp_leaderboard.csv"
)

INELIGIBLE_OUTPUT_PATH = Path(
    "data/interim/bo6_mvp_ineligible_players.csv"
)

MINIMUM_PARTICIPATION_SHARE = 0.50

METRIC_WEIGHTS = {
    "kd": 0.25,
    "hp_dmg_10m": 0.20,
    "hp_k_10m": 0.15,
    "snd_kd_calculated": 0.15,
    "snd_kills_per_round": 0.10,
    "snd_opening_duel_win_pct_calculated": 0.10,
    "ctl_dmg_10m": 0.05,
}

COMPONENT_NAMES = {
    "kd": "overall_kd_score",
    "hp_dmg_10m": "hp_damage_score",
    "hp_k_10m": "hp_pace_score",
    "snd_kd_calculated": "snd_kd_score",
    "snd_kills_per_round": "snd_kpr_score",
    "snd_opening_duel_win_pct_calculated": (
        "snd_opening_duel_score"
    ),
    "ctl_dmg_10m": "control_damage_score",
}


def require_columns(
    dataframe: pd.DataFrame,
    required_columns: list[str],
) -> None:
    """Raise an informative error when a required column is absent."""

    missing_columns = [
        column
        for column in required_columns
        if column not in dataframe.columns
    ]

    if missing_columns:
        missing_text = ", ".join(missing_columns)

        raise RuntimeError(
            "The feature dataset is missing required columns: "
            f"{missing_text}"
        )


def add_percentile_components(
    dataframe: pd.DataFrame,
) -> pd.DataFrame:
    """Convert each impact metric into a 0-100 percentile score."""

    result = dataframe.copy()

    for metric, component_name in COMPONENT_NAMES.items():
        result[component_name] = (
            result[metric]
            .rank(
                method="average",
                pct=True,
                ascending=True,
            )
            * 100
        )

    return result


def main() -> None:
    if not INPUT_PATH.exists():
        raise FileNotFoundError(
            f"{INPUT_PATH} does not exist."
        )

    dataframe = pd.read_csv(INPUT_PATH)

    required_columns = [
        "player_id",
        "player_tag",
        "game_count",
        "hp_game_count",
        "snd_game_count",
        "ctl_game_count",
        "bp_rating",
        *METRIC_WEIGHTS.keys(),
    ]

    require_columns(
        dataframe,
        required_columns,
    )

    numeric_columns = [
        "game_count",
        "hp_game_count",
        "snd_game_count",
        "ctl_game_count",
        "bp_rating",
        *METRIC_WEIGHTS.keys(),
    ]

    for column in numeric_columns:
        dataframe[column] = pd.to_numeric(
            dataframe[column],
            errors="coerce",
        )

    dataframe = dataframe.dropna(
        subset=[
            "player_id",
            "player_tag",
            "game_count",
            *METRIC_WEIGHTS.keys(),
        ]
    ).copy()

    maximum_games = int(
        dataframe["game_count"].max()
    )

    minimum_games = math.ceil(
        maximum_games
        * MINIMUM_PARTICIPATION_SHARE
    )

    dataframe["participation_rate"] = (
        dataframe["game_count"]
        / maximum_games
    )

    eligible = dataframe[
        dataframe["game_count"] >= minimum_games
    ].copy()

    ineligible = dataframe[
        dataframe["game_count"] < minimum_games
    ].copy()

    if eligible.empty:
        raise RuntimeError(
            "No players passed the eligibility requirement."
        )

    eligible = add_percentile_components(
        eligible
    )

    eligible["impact_score"] = 0.0

    for metric, weight in METRIC_WEIGHTS.items():
        component_name = COMPONENT_NAMES[metric]

        eligible["impact_score"] += (
            eligible[component_name]
            * weight
        )

    # Reward full-season participation without allowing map volume
    # to overwhelm player performance.
    #
    # A player at the 50% eligibility threshold receives a multiplier
    # near 0.95. A player at the maximum receives 1.00.
    eligible["consistency_multiplier"] = (
        0.90
        + 0.10 * eligible["participation_rate"]
    )

    eligible["mvp_score"] = (
        eligible["impact_score"]
        * eligible["consistency_multiplier"]
    )

    eligible = eligible.sort_values(
        [
            "mvp_score",
            "impact_score",
            "game_count",
        ],
        ascending=[
            False,
            False,
            False,
        ],
    ).reset_index(drop=True)

    eligible["mvp_rank"] = (
        eligible.index + 1
    )

    # Compare our custom ranking with BreakingPoint's existing rating.
    eligible["bp_rating_rank"] = (
        eligible["bp_rating"]
        .rank(
            method="min",
            ascending=False,
        )
        .astype(int)
    )

    eligible["rank_difference_vs_bp"] = (
        eligible["bp_rating_rank"]
        - eligible["mvp_rank"]
    )

    output_columns = [
        "mvp_rank",
        "player_id",
        "player_tag",
        "mvp_score",
        "impact_score",
        "consistency_multiplier",
        "participation_rate",
        "game_count",
        "hp_game_count",
        "snd_game_count",
        "ctl_game_count",
        "kd",
        "hp_dmg_10m",
        "hp_k_10m",
        "snd_kd_calculated",
        "snd_kills_per_round",
        "snd_opening_duel_win_pct_calculated",
        "ctl_dmg_10m",
        "overall_kd_score",
        "hp_damage_score",
        "hp_pace_score",
        "snd_kd_score",
        "snd_kpr_score",
        "snd_opening_duel_score",
        "control_damage_score",
        "bp_rating",
        "bp_rating_rank",
        "rank_difference_vs_bp",
    ]

    eligible = eligible[
        output_columns
    ]

    LEADERBOARD_OUTPUT_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    eligible.to_csv(
        LEADERBOARD_OUTPUT_PATH,
        index=False,
    )

    ineligible = ineligible.sort_values(
        "game_count",
        ascending=False,
    )

    ineligible.to_csv(
        INELIGIBLE_OUTPUT_PATH,
        index=False,
    )

    print("BO6 CDL MVP Impact Score")
    print("=" * 100)
    print(f"Players in source data: {len(dataframe)}")
    print(f"Maximum maps played: {maximum_games}")
    print(f"Minimum maps required: {minimum_games}")
    print(f"Eligible players: {len(eligible)}")
    print(f"Ineligible players: {len(ineligible)}")

    print("\nMetric weights")
    print("=" * 100)

    for metric, weight in METRIC_WEIGHTS.items():
        print(f"{metric:<45} {weight:>6.0%}")

    print("\nTop 20 MVP candidates")
    print("=" * 100)

    display_columns = [
        "mvp_rank",
        "player_tag",
        "mvp_score",
        "game_count",
        "kd",
        "hp_dmg_10m",
        "hp_k_10m",
        "snd_kd_calculated",
        "snd_kills_per_round",
        "snd_opening_duel_win_pct_calculated",
        "ctl_dmg_10m",
        "bp_rating_rank",
        "rank_difference_vs_bp",
    ]

    print(
        eligible[display_columns]
        .head(20)
        .to_string(
            index=False,
            formatters={
                "mvp_score": lambda value: f"{value:.2f}",
                "kd": lambda value: f"{value:.3f}",
                "hp_dmg_10m": lambda value: f"{value:.1f}",
                "hp_k_10m": lambda value: f"{value:.2f}",
                "snd_kd_calculated": (
                    lambda value: f"{value:.3f}"
                ),
                "snd_kills_per_round": (
                    lambda value: f"{value:.3f}"
                ),
                "snd_opening_duel_win_pct_calculated": (
                    lambda value: f"{value:.1%}"
                ),
                "ctl_dmg_10m": lambda value: f"{value:.1f}",
            },
        )
    )

    print("\nLargest differences from BreakingPoint ranking")
    print("=" * 100)

    comparison = eligible.copy()

    comparison["absolute_rank_difference"] = (
        comparison["rank_difference_vs_bp"]
        .abs()
    )

    comparison = comparison.sort_values(
        "absolute_rank_difference",
        ascending=False,
    )

    print(
        comparison[
            [
                "player_tag",
                "mvp_rank",
                "bp_rating_rank",
                "rank_difference_vs_bp",
                "mvp_score",
            ]
        ]
        .head(15)
        .to_string(
            index=False,
            formatters={
                "mvp_score": lambda value: f"{value:.2f}",
            },
        )
    )

    print("\nCreated files")
    print("=" * 100)
    print(LEADERBOARD_OUTPUT_PATH)
    print(INELIGIBLE_OUTPUT_PATH)


if __name__ == "__main__":
    main()
