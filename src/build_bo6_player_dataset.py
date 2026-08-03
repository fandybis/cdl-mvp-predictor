"""Convert BreakingPoint BO6 player data into MVP-model features."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd


INPUT_PATH = Path(
    "data/raw/breakingpoint_bo6_player_stats.json"
)

FULL_OUTPUT_PATH = Path(
    "data/interim/bo6_player_stats_full.csv"
)

FEATURE_OUTPUT_PATH = Path(
    "data/processed/bo6_mvp_features.csv"
)


def safe_divide(
    numerator: pd.Series,
    denominator: pd.Series,
) -> pd.Series:
    """Divide two columns while preventing divide-by-zero results."""

    denominator = denominator.replace(0, np.nan)
    return numerator / denominator


def ensure_numeric(
    dataframe: pd.DataFrame,
    columns: list[str],
) -> None:
    """Convert available columns to numeric values."""

    for column in columns:
        if column in dataframe.columns:
            dataframe[column] = pd.to_numeric(
                dataframe[column],
                errors="coerce",
            )


def main() -> None:
    if not INPUT_PATH.exists():
        raise FileNotFoundError(
            f"{INPUT_PATH} does not exist. "
            "Run probe_player_stats_api.py first."
        )

    records = json.loads(
        INPUT_PATH.read_text(encoding="utf-8")
    )

    if not isinstance(records, list) or not records:
        raise RuntimeError(
            "The saved BreakingPoint file contains no player records."
        )

    dataframe = pd.DataFrame(records)

    print("Loaded BreakingPoint data")
    print("=" * 72)
    print(f"Player rows: {len(dataframe)}")
    print(f"Source columns: {len(dataframe.columns)}")

    numeric_columns = [
        "player_id",
        "game_count",
        "hp_game_count",
        "snd_game_count",
        "ctl_game_count",
        "kills",
        "deaths",
        "damage",
        "kd",
        "hp_kills",
        "hp_deaths",
        "hp_damage",
        "hp_gametime",
        "hp_kd",
        "hp_k_10m",
        "hp_dmg_10m",
        "snd_kills",
        "snd_deaths",
        "snd_damage",
        "snd_rounds",
        "snd_kd",
        "first_blood_count",
        "first_death_count",
        "first_blood_percentage",
        "ctl_kills",
        "ctl_deaths",
        "ctl_damage",
        "ctl_gametime",
        "ctl_kd",
        "ctl_k_10m",
        "ctl_dmg_10m",
        "bp_rating",
        "slayer_rating",
    ]

    ensure_numeric(dataframe, numeric_columns)

    # Recalculate several metrics from their underlying totals.
    # This provides validation and consistent definitions.
    dataframe["overall_kd_calculated"] = safe_divide(
        dataframe["kills"],
        dataframe["deaths"],
    )

    dataframe["hp_kd_calculated"] = safe_divide(
        dataframe["hp_kills"],
        dataframe["hp_deaths"],
    )

    dataframe["snd_kd_calculated"] = safe_divide(
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

    opening_duel_total = (
        dataframe["first_blood_count"]
        + dataframe["first_death_count"]
    )

    dataframe["snd_opening_duel_win_pct_calculated"] = safe_divide(
        dataframe["first_blood_count"],
        opening_duel_total,
    )

    dataframe["ctl_kd_calculated"] = safe_divide(
        dataframe["ctl_kills"],
        dataframe["ctl_deaths"],
    )

    # Keep the complete response for later exploration.
    FULL_OUTPUT_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    dataframe.to_csv(
        FULL_OUTPUT_PATH,
        index=False,
    )

    desired_features = [
        "player_id",
        "player_tag",
        "game_count",
        "hp_game_count",
        "snd_game_count",
        "ctl_game_count",
        "kills",
        "deaths",
        "damage",
        "kd",
        "overall_kd_calculated",
        "hp_kd",
        "hp_kd_calculated",
        "hp_k_10m",
        "hp_dmg_10m",
        "snd_kd",
        "snd_kd_calculated",
        "snd_kills_per_round",
        "first_blood_count",
        "first_death_count",
        "first_blood_percentage",
        "snd_opening_duel_win_pct_calculated",
        "snd_first_bloods_per_round",
        "ctl_kd",
        "ctl_kd_calculated",
        "ctl_k_10m",
        "ctl_dmg_10m",
        "bp_rating",
        "slayer_rating",
    ]

    available_features = [
        column
        for column in desired_features
        if column in dataframe.columns
    ]

    missing_features = [
        column
        for column in desired_features
        if column not in dataframe.columns
    ]

    feature_data = dataframe[
        available_features
    ].copy()

    # Sort by the existing BreakingPoint rating for inspection only.
    # We are not using BP Rating as our final MVP score.
    if "bp_rating" in feature_data.columns:
        feature_data = feature_data.sort_values(
            "bp_rating",
            ascending=False,
        )

    FEATURE_OUTPUT_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    feature_data.to_csv(
        FEATURE_OUTPUT_PATH,
        index=False,
    )

    print("\nCreated files")
    print("=" * 72)
    print(FULL_OUTPUT_PATH)
    print(FEATURE_OUTPUT_PATH)

    print("\nSelected feature columns")
    print("=" * 72)

    for column in available_features:
        print(column)

    print("\nUnavailable requested columns")
    print("=" * 72)

    if missing_features:
        for column in missing_features:
            print(column)
    else:
        print("None")

    print("\nMissing-value counts")
    print("=" * 72)

    missing_counts = (
        feature_data
        .isna()
        .sum()
        .sort_values(ascending=False)
    )

    for column, count in missing_counts.items():
        if count > 0:
            print(f"{column:<45} {count}")

    print("\nTop 10 players by BreakingPoint rating")
    print("=" * 72)

    display_columns = [
        column
        for column in [
            "player_tag",
            "game_count",
            "kd",
            "hp_k_10m",
            "hp_dmg_10m",
            "snd_kd",
            "snd_kills_per_round",
            "snd_opening_duel_win_pct_calculated",
            "ctl_dmg_10m",
            "bp_rating",
        ]
        if column in feature_data.columns
    ]

    print(
        feature_data[display_columns]
        .head(10)
        .to_string(index=False)
    )


if __name__ == "__main__":
    main()
