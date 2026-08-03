"""Build a category-based Version 2 CDL MVP Impact Score."""

from __future__ import annotations

import math
from pathlib import Path

import numpy as np
import pandas as pd


INPUT_PATH = Path(
    "data/interim/bo6_player_stats_full.csv"
)

V1_PATH = Path(
    "data/processed/bo6_mvp_leaderboard.csv"
)

OUTPUT_PATH = Path(
    "data/processed/bo6_mvp_leaderboard_v2.csv"
)

COMPONENT_OUTPUT_PATH = Path(
    "data/interim/bo6_mvp_v2_components.csv"
)

MINIMUM_PARTICIPATION_SHARE = 0.50


CATEGORY_WEIGHTS = {
    "overall_efficiency_score": 0.15,
    "hardpoint_impact_score": 0.30,
    "snd_impact_score": 0.30,
    "control_impact_score": 0.20,
    "participation_score": 0.05,
}


HARDPOINT_METRICS = {
    "hp_dmg_10m": 0.25,
    "hp_engagements_10m": 0.20,
    "hp_assists_10m": 0.10,
    "hp_hill_time_10m": 0.15,
    "hp_contested_time_10m": 0.10,
    "hp_non_traded_kill_pct": 0.20,
}


SND_METRICS = {
    "snd_kd": 0.20,
    "snd_kills_per_round": 0.10,
    "snd_first_bloods_per_round": 0.20,
    "snd_opening_duel_win_pct": 0.15,
    "snd_non_traded_kill_pct": 0.20,
    "snd_objective_actions_per_round": 0.15,
}


CONTROL_METRICS = {
    "ctl_dmg_10m": 0.25,
    "ctl_kills_10m": 0.20,
    "ctl_assists_10m": 0.15,
    "ctl_non_traded_kill_pct": 0.20,
    "ctl_ticks_per_attack_round": 0.20,
}


def safe_divide(
    numerator: pd.Series,
    denominator: pd.Series,
) -> pd.Series:
    """Divide two Series while replacing invalid results with NaN."""

    result = numerator / denominator.replace(0, np.nan)

    return result.replace(
        [np.inf, -np.inf],
        np.nan,
    )


def require_columns(
    dataframe: pd.DataFrame,
    required_columns: list[str],
) -> None:
    """Ensure that every required source column is present."""

    missing = [
        column
        for column in required_columns
        if column not in dataframe.columns
    ]

    if missing:
        raise RuntimeError(
            "Missing required columns: "
            + ", ".join(missing)
        )


def validate_weights(
    weights: dict[str, float],
    label: str,
) -> None:
    """Confirm that a collection of weights totals 100%."""

    total = sum(weights.values())

    if not np.isclose(total, 1.0):
        raise RuntimeError(
            f"{label} weights total {total:.4f}, not 1.0."
        )


def add_percentile_column(
    dataframe: pd.DataFrame,
    metric: str,
) -> str:
    """Create and return a 0-100 percentile column for a metric."""

    percentile_column = f"{metric}_percentile"

    dataframe[percentile_column] = (
        dataframe[metric]
        .rank(
            method="average",
            pct=True,
            ascending=True,
        )
        * 100
    )

    return percentile_column


def calculate_category_score(
    dataframe: pd.DataFrame,
    metrics: dict[str, float],
    output_column: str,
) -> list[str]:
    """Calculate one category from weighted metric percentiles."""

    percentile_columns = []

    dataframe[output_column] = 0.0

    for metric, weight in metrics.items():
        percentile_column = add_percentile_column(
            dataframe,
            metric,
        )

        percentile_columns.append(
            percentile_column
        )

        dataframe[output_column] += (
            dataframe[percentile_column]
            * weight
        )

    return percentile_columns


def main() -> None:
    validate_weights(
        CATEGORY_WEIGHTS,
        "Category",
    )

    validate_weights(
        HARDPOINT_METRICS,
        "Hardpoint",
    )

    validate_weights(
        SND_METRICS,
        "Search and Destroy",
    )

    validate_weights(
        CONTROL_METRICS,
        "Control",
    )

    if not INPUT_PATH.exists():
        raise FileNotFoundError(
            f"{INPUT_PATH} was not found."
        )

    dataframe = pd.read_csv(INPUT_PATH)

    source_columns = [
        "player_id",
        "player_tag",
        "game_count",
        "hp_game_count",
        "snd_game_count",
        "ctl_game_count",
        "kills",
        "deaths",
        "hp_kills",
        "hp_deaths",
        "hp_assists",
        "hp_damage",
        "hp_gametime",
        "hill_time",
        "contested_hill_time",
        "hp_non_traded_kills",
        "snd_kills",
        "snd_deaths",
        "snd_rounds",
        "first_blood_count",
        "first_death_count",
        "snd_non_traded_kills",
        "plant_count",
        "defuse_count",
        "ctl_kills",
        "ctl_deaths",
        "ctl_assists",
        "ctl_damage",
        "ctl_gametime",
        "ctl_non_traded_kills",
        "ctl_ticks",
        "ctl_attack_rounds",
    ]

    require_columns(
        dataframe,
        source_columns,
    )

    numeric_columns = [
        column
        for column in source_columns
        if column != "player_tag"
    ]

    for column in numeric_columns:
        dataframe[column] = pd.to_numeric(
            dataframe[column],
            errors="coerce",
        )

    # ------------------------------------------------------------------
    # Overall efficiency
    # ------------------------------------------------------------------

    dataframe["overall_kd"] = safe_divide(
        dataframe["kills"],
        dataframe["deaths"],
    )

    # ------------------------------------------------------------------
    # Hardpoint
    # ------------------------------------------------------------------

    dataframe["hp_dmg_10m"] = (
        safe_divide(
            dataframe["hp_damage"],
            dataframe["hp_gametime"],
        )
        * 10
    )

    dataframe["hp_engagements_10m"] = (
        safe_divide(
            dataframe["hp_kills"]
            + dataframe["hp_deaths"],
            dataframe["hp_gametime"],
        )
        * 10
    )

    dataframe["hp_assists_10m"] = (
        safe_divide(
            dataframe["hp_assists"],
            dataframe["hp_gametime"],
        )
        * 10
    )

    # BreakingPoint stores hill-time fields in seconds and
    # hp_gametime in minutes.
    dataframe["hp_hill_time_10m"] = (
        safe_divide(
            dataframe["hill_time"] / 60,
            dataframe["hp_gametime"],
        )
        * 10
    )

    dataframe["hp_contested_time_10m"] = (
        safe_divide(
            dataframe["contested_hill_time"] / 60,
            dataframe["hp_gametime"],
        )
        * 10
    )

    dataframe["hp_non_traded_kill_pct"] = safe_divide(
        dataframe["hp_non_traded_kills"],
        dataframe["hp_kills"],
    )

    # ------------------------------------------------------------------
    # Search and Destroy
    # ------------------------------------------------------------------

    dataframe["snd_kd"] = safe_divide(
        dataframe["snd_kills"],
        dataframe["snd_deaths"],
    )

    dataframe["snd_kills_per_round"] = safe_divide(
        dataframe["snd_kills"],
        dataframe["snd_rounds"],
    )

    dataframe["snd_first_bloods_per_round"] = safe_divide(
        dataframe["first_blood_count"],
        dataframe["snd_rounds"],
    )

    opening_duels = (
        dataframe["first_blood_count"]
        + dataframe["first_death_count"]
    )

    dataframe["snd_opening_duel_win_pct"] = safe_divide(
        dataframe["first_blood_count"],
        opening_duels,
    )

    dataframe["snd_non_traded_kill_pct"] = safe_divide(
        dataframe["snd_non_traded_kills"],
        dataframe["snd_kills"],
    )

    dataframe[
        "snd_objective_actions_per_round"
    ] = safe_divide(
        dataframe["plant_count"]
        + dataframe["defuse_count"],
        dataframe["snd_rounds"],
    )

    # ------------------------------------------------------------------
    # Control
    # ------------------------------------------------------------------

    dataframe["ctl_dmg_10m"] = (
        safe_divide(
            dataframe["ctl_damage"],
            dataframe["ctl_gametime"],
        )
        * 10
    )

    dataframe["ctl_kills_10m"] = (
        safe_divide(
            dataframe["ctl_kills"],
            dataframe["ctl_gametime"],
        )
        * 10
    )

    dataframe["ctl_assists_10m"] = (
        safe_divide(
            dataframe["ctl_assists"],
            dataframe["ctl_gametime"],
        )
        * 10
    )

    dataframe["ctl_non_traded_kill_pct"] = safe_divide(
        dataframe["ctl_non_traded_kills"],
        dataframe["ctl_kills"],
    )

    dataframe["ctl_ticks_per_attack_round"] = safe_divide(
        dataframe["ctl_ticks"],
        dataframe["ctl_attack_rounds"],
    )

    # ------------------------------------------------------------------
    # Eligibility
    # ------------------------------------------------------------------

    maximum_games = int(
        dataframe["game_count"].max()
    )

    minimum_games = math.ceil(
        maximum_games
        * MINIMUM_PARTICIPATION_SHARE
    )

    eligible = dataframe[
        dataframe["game_count"] >= minimum_games
    ].copy()

    required_metrics = [
        "overall_kd",
        *HARDPOINT_METRICS.keys(),
        *SND_METRICS.keys(),
        *CONTROL_METRICS.keys(),
    ]

    before_drop = len(eligible)

    eligible = eligible.dropna(
        subset=required_metrics
    ).copy()

    dropped_for_missing_metrics = (
        before_drop - len(eligible)
    )

    if eligible.empty:
        raise RuntimeError(
            "No players remained after eligibility "
            "and missing-value filters."
        )

    # ------------------------------------------------------------------
    # Category scoring
    # ------------------------------------------------------------------

    all_percentile_columns = []

    overall_percentile = add_percentile_column(
        eligible,
        "overall_kd",
    )

    all_percentile_columns.append(
        overall_percentile
    )

    eligible["overall_efficiency_score"] = (
        eligible[overall_percentile]
    )

    all_percentile_columns.extend(
        calculate_category_score(
            eligible,
            HARDPOINT_METRICS,
            "hardpoint_impact_score",
        )
    )

    all_percentile_columns.extend(
        calculate_category_score(
            eligible,
            SND_METRICS,
            "snd_impact_score",
        )
    )

    all_percentile_columns.extend(
        calculate_category_score(
            eligible,
            CONTROL_METRICS,
            "control_impact_score",
        )
    )

    eligible["participation_rate"] = (
        eligible["game_count"]
        / maximum_games
    )

    eligible["participation_score"] = (
        eligible["game_count"]
        .rank(
            method="average",
            pct=True,
            ascending=True,
        )
        * 100
    )

    eligible["mvp_score_v2"] = 0.0

    for category, weight in CATEGORY_WEIGHTS.items():
        eligible["mvp_score_v2"] += (
            eligible[category]
            * weight
        )

    eligible = eligible.sort_values(
        [
            "mvp_score_v2",
            "game_count",
        ],
        ascending=[
            False,
            False,
        ],
    ).reset_index(drop=True)

    eligible["mvp_rank_v2"] = (
        eligible.index + 1
    )

    # ------------------------------------------------------------------
    # Compare Version 2 with Version 1
    # ------------------------------------------------------------------

    if V1_PATH.exists():
        version_one = pd.read_csv(V1_PATH)

        version_one = version_one[
            [
                "player_id",
                "mvp_rank",
                "mvp_score",
                "bp_rating_rank",
            ]
        ].rename(
            columns={
                "mvp_rank": "mvp_rank_v1",
                "mvp_score": "mvp_score_v1",
            }
        )

        eligible = eligible.merge(
            version_one,
            on="player_id",
            how="left",
        )

        eligible["movement_vs_v1"] = (
            eligible["mvp_rank_v1"]
            - eligible["mvp_rank_v2"]
        )

        eligible["movement_vs_bp"] = (
            eligible["bp_rating_rank"]
            - eligible["mvp_rank_v2"]
        )

    # ------------------------------------------------------------------
    # Save files
    # ------------------------------------------------------------------

    core_output_columns = [
        "mvp_rank_v2",
        "player_id",
        "player_tag",
        "mvp_score_v2",
        "overall_efficiency_score",
        "hardpoint_impact_score",
        "snd_impact_score",
        "control_impact_score",
        "participation_score",
        "participation_rate",
        "game_count",
        "hp_game_count",
        "snd_game_count",
        "ctl_game_count",
        "overall_kd",
        *HARDPOINT_METRICS.keys(),
        *SND_METRICS.keys(),
        *CONTROL_METRICS.keys(),
    ]

    comparison_columns = [
        column
        for column in [
            "mvp_rank_v1",
            "mvp_score_v1",
            "movement_vs_v1",
            "bp_rating_rank",
            "movement_vs_bp",
        ]
        if column in eligible.columns
    ]

    leaderboard_columns = (
        core_output_columns
        + comparison_columns
    )

    leaderboard = eligible[
        leaderboard_columns
    ].copy()

    OUTPUT_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    leaderboard.to_csv(
        OUTPUT_PATH,
        index=False,
    )

    component_columns = [
        *leaderboard_columns,
        *all_percentile_columns,
    ]

    eligible[
        component_columns
    ].to_csv(
        COMPONENT_OUTPUT_PATH,
        index=False,
    )

    # ------------------------------------------------------------------
    # Terminal output
    # ------------------------------------------------------------------

    print("BO6 CDL MVP Impact Score — Version 2")
    print("=" * 116)
    print(f"Players in source data: {len(dataframe)}")
    print(f"Maximum maps played: {maximum_games}")
    print(f"Minimum maps required: {minimum_games}")
    print(f"Eligible players: {len(eligible)}")
    print(
        "Players dropped for missing metrics: "
        f"{dropped_for_missing_metrics}"
    )

    print("\nCategory weights")
    print("=" * 116)

    for category, weight in CATEGORY_WEIGHTS.items():
        print(f"{category:<40} {weight:>6.0%}")

    print("\nHardpoint sub-weights")
    print("=" * 116)

    for metric, weight in HARDPOINT_METRICS.items():
        print(f"{metric:<40} {weight:>6.0%}")

    print("\nSearch and Destroy sub-weights")
    print("=" * 116)

    for metric, weight in SND_METRICS.items():
        print(f"{metric:<40} {weight:>6.0%}")

    print("\nControl sub-weights")
    print("=" * 116)

    for metric, weight in CONTROL_METRICS.items():
        print(f"{metric:<40} {weight:>6.0%}")

    print("\nTop 20 MVP candidates — Version 2")
    print("=" * 116)

    display_columns = [
        "mvp_rank_v2",
        "player_tag",
        "mvp_score_v2",
        "overall_efficiency_score",
        "hardpoint_impact_score",
        "snd_impact_score",
        "control_impact_score",
        "participation_score",
        "game_count",
    ]

    if "mvp_rank_v1" in eligible.columns:
        display_columns.extend(
            [
                "mvp_rank_v1",
                "movement_vs_v1",
            ]
        )

    display = eligible[
        display_columns
    ].head(20).copy()

    score_columns = [
        "mvp_score_v2",
        "overall_efficiency_score",
        "hardpoint_impact_score",
        "snd_impact_score",
        "control_impact_score",
        "participation_score",
    ]

    display[score_columns] = display[
        score_columns
    ].round(2)

    print(
        display.to_string(index=False)
    )

    if "movement_vs_v1" in eligible.columns:
        print("\nLargest upward movers from Version 1")
        print("=" * 116)

        upward = eligible.sort_values(
            "movement_vs_v1",
            ascending=False,
        )

        print(
            upward[
                [
                    "player_tag",
                    "mvp_rank_v2",
                    "mvp_rank_v1",
                    "movement_vs_v1",
                    "mvp_score_v2",
                ]
            ]
            .head(12)
            .round(
                {
                    "mvp_score_v2": 2,
                }
            )
            .to_string(index=False)
        )

        print("\nLargest downward movers from Version 1")
        print("=" * 116)

        downward = eligible.sort_values(
            "movement_vs_v1",
            ascending=True,
        )

        print(
            downward[
                [
                    "player_tag",
                    "mvp_rank_v2",
                    "mvp_rank_v1",
                    "movement_vs_v1",
                    "mvp_score_v2",
                ]
            ]
            .head(12)
            .round(
                {
                    "mvp_score_v2": 2,
                }
            )
            .to_string(index=False)
        )

    print("\nTop 10 category profiles")
    print("=" * 116)

    category_display = eligible[
        [
            "mvp_rank_v2",
            "player_tag",
            "overall_efficiency_score",
            "hardpoint_impact_score",
            "snd_impact_score",
            "control_impact_score",
            "participation_score",
        ]
    ].head(10).copy()

    category_display = category_display.round(2)

    print(
        category_display.to_string(index=False)
    )

    print("\nCreated files")
    print("=" * 116)
    print(OUTPUT_PATH)
    print(COMPONENT_OUTPUT_PATH)


if __name__ == "__main__":
    main()
