"""Build and audit additional BO6 player-impact features."""

from __future__ import annotations

import math
from pathlib import Path

import numpy as np
import pandas as pd


INPUT_PATH = Path(
    "data/interim/bo6_player_stats_full.csv"
)

OUTPUT_PATH = Path(
    "data/interim/bo6_extended_impact_features.csv"
)

MINIMUM_PARTICIPATION_SHARE = 0.50

CORE_METRICS = [
    "kd",
    "hp_dmg_10m",
    "hp_k_10m",
    "snd_kd_calculated",
    "snd_kills_per_round",
    "snd_opening_duel_win_pct_calculated",
    "ctl_dmg_10m",
]

EXTENDED_METRICS = {
    "hp_assists_10m_calculated": "HP assists per 10",
    "hp_hill_time_10m": "HP hill time per 10",
    "hp_contested_time_10m": "HP contested time per 10",
    "hp_non_traded_kill_pct_calculated": "HP non-traded kill %",
    "snd_first_bloods_per_round": "SND first bloods per round",
    "snd_non_traded_kill_pct_calculated": "SND non-traded kill %",
    "snd_objective_actions_per_round": "SND plants + defuses per round",
    "ctl_kills_10m_calculated": "CTL kills per 10",
    "ctl_assists_10m_calculated": "CTL assists per 10",
    "ctl_non_traded_kill_pct_calculated": "CTL non-traded kill %",
    "ctl_ticks_per_attack_round": "CTL ticks per attacking round",
}

SELECTED_PLAYERS = [
    "Scrap",
    "HyDra",
    "Dashy",
    "RenKoR",
    "Cellium",
    "Shotzzy",
    "Neptune",
    "CleanX",
    "Simp",
    "Ghosty",
    "Envoy",
    "Nero",
]


def safe_divide(
    numerator: pd.Series,
    denominator: pd.Series,
) -> pd.Series:
    """Divide two numeric Series while avoiding infinite values."""

    denominator = denominator.replace(0, np.nan)

    result = numerator / denominator

    return result.replace(
        [np.inf, -np.inf],
        np.nan,
    )


def require_columns(
    dataframe: pd.DataFrame,
    columns: list[str],
) -> None:
    """Confirm that all source columns needed for the audit exist."""

    missing = [
        column
        for column in columns
        if column not in dataframe.columns
    ]

    if missing:
        raise RuntimeError(
            "Missing required source columns: "
            + ", ".join(missing)
        )


def main() -> None:
    if not INPUT_PATH.exists():
        raise FileNotFoundError(
            f"{INPUT_PATH} does not exist."
        )

    dataframe = pd.read_csv(INPUT_PATH)

    required_source_columns = [
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
        "hp_non_traded_kills",
        "hill_time",
        "contested_hill_time",
        "snd_kills",
        "snd_deaths",
        "snd_rounds",
        "snd_non_traded_kills",
        "first_blood_count",
        "first_death_count",
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
        "hp_dmg_10m",
        "hp_k_10m",
        "ctl_dmg_10m",
    ]

    require_columns(
        dataframe,
        required_source_columns,
    )

    numeric_columns = [
        column
        for column in required_source_columns
        if column not in {
            "player_tag",
        }
    ]

    for column in numeric_columns:
        dataframe[column] = pd.to_numeric(
            dataframe[column],
            errors="coerce",
        )

    # Core metrics rebuilt from underlying totals.
    dataframe["kd"] = safe_divide(
        dataframe["kills"],
        dataframe["deaths"],
    )

    dataframe["snd_kd_calculated"] = safe_divide(
        dataframe["snd_kills"],
        dataframe["snd_deaths"],
    )

    dataframe["snd_kills_per_round"] = safe_divide(
        dataframe["snd_kills"],
        dataframe["snd_rounds"],
    )

    opening_duels = (
        dataframe["first_blood_count"]
        + dataframe["first_death_count"]
    )

    dataframe[
        "snd_opening_duel_win_pct_calculated"
    ] = safe_divide(
        dataframe["first_blood_count"],
        opening_duels,
    )

    # Hardpoint impact features.
    dataframe["hp_assists_10m_calculated"] = safe_divide(
        dataframe["hp_assists"],
        dataframe["hp_gametime"],
    ) * 10

    # BreakingPoint hill-time fields appear to be stored in seconds,
    # while hp_gametime is measured in minutes.
    dataframe["hp_hill_time_10m"] = safe_divide(
        dataframe["hill_time"] / 60,
        dataframe["hp_gametime"],
    ) * 10

    dataframe["hp_contested_time_10m"] = safe_divide(
        dataframe["contested_hill_time"] / 60,
        dataframe["hp_gametime"],
    ) * 10

    dataframe[
        "hp_non_traded_kill_pct_calculated"
    ] = safe_divide(
        dataframe["hp_non_traded_kills"],
        dataframe["hp_kills"],
    )

    # Search and Destroy impact features.
    dataframe["snd_first_bloods_per_round"] = safe_divide(
        dataframe["first_blood_count"],
        dataframe["snd_rounds"],
    )

    dataframe[
        "snd_non_traded_kill_pct_calculated"
    ] = safe_divide(
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

    # Control impact features.
    dataframe["ctl_kills_10m_calculated"] = safe_divide(
        dataframe["ctl_kills"],
        dataframe["ctl_gametime"],
    ) * 10

    dataframe["ctl_assists_10m_calculated"] = safe_divide(
        dataframe["ctl_assists"],
        dataframe["ctl_gametime"],
    ) * 10

    dataframe[
        "ctl_non_traded_kill_pct_calculated"
    ] = safe_divide(
        dataframe["ctl_non_traded_kills"],
        dataframe["ctl_kills"],
    )

    dataframe["ctl_ticks_per_attack_round"] = safe_divide(
        dataframe["ctl_ticks"],
        dataframe["ctl_attack_rounds"],
    )

    maximum_games = int(
        dataframe["game_count"].max()
    )

    minimum_games = math.ceil(
        maximum_games
        * MINIMUM_PARTICIPATION_SHARE
    )

    dataframe["mvp_eligible"] = (
        dataframe["game_count"]
        >= minimum_games
    )

    output_columns = [
        "player_id",
        "player_tag",
        "mvp_eligible",
        "game_count",
        "hp_game_count",
        "snd_game_count",
        "ctl_game_count",
        *CORE_METRICS,
        *EXTENDED_METRICS.keys(),
    ]

    output_data = dataframe[
        output_columns
    ].copy()

    output_data.to_csv(
        OUTPUT_PATH,
        index=False,
    )

    eligible = output_data[
        output_data["mvp_eligible"]
    ].copy()

    audit_metrics = [
        *CORE_METRICS,
        *EXTENDED_METRICS.keys(),
    ]

    correlations = eligible[
        audit_metrics
    ].corr()

    print("Extended BO6 impact audit")
    print("=" * 118)
    print(f"Players in source data: {len(output_data)}")
    print(f"Maximum maps played: {maximum_games}")
    print(f"Minimum maps required: {minimum_games}")
    print(f"Eligible players: {len(eligible)}")

    print("\nExtended metric distributions")
    print("=" * 118)

    distribution = eligible[
        list(EXTENDED_METRICS.keys())
    ].describe().transpose()

    distribution = distribution[
        [
            "min",
            "25%",
            "50%",
            "75%",
            "max",
        ]
    ]

    distribution.insert(
        0,
        "label",
        [
            EXTENDED_METRICS[column]
            for column in distribution.index
        ],
    )

    print(
        distribution
        .round(4)
        .to_string()
    )

    print("\nStrong relationships involving extended metrics")
    print("=" * 118)

    relationships = []

    for left_index, left_metric in enumerate(
        audit_metrics
    ):
        for right_metric in audit_metrics[
            left_index + 1:
        ]:
            correlation = correlations.loc[
                left_metric,
                right_metric,
            ]

            if (
                abs(correlation) >= 0.65
                and (
                    left_metric in EXTENDED_METRICS
                    or right_metric in EXTENDED_METRICS
                )
            ):
                relationships.append(
                    (
                        left_metric,
                        right_metric,
                        correlation,
                    )
                )

    relationships.sort(
        key=lambda row: abs(row[2]),
        reverse=True,
    )

    if not relationships:
        print(
            "No extended metric relationships reached "
            "an absolute correlation of 0.65."
        )
    else:
        for left, right, correlation in relationships:
            print(
                f"{left:<47} "
                f"{right:<47} "
                f"{correlation:>7.3f}"
            )

    print("\nSelected player extended profiles")
    print("=" * 118)

    selected = eligible[
        eligible["player_tag"].isin(
            SELECTED_PLAYERS
        )
    ].copy()

    selected = selected.sort_values(
        "player_tag"
    )

    selected_columns = [
        "player_tag",
        "game_count",
        "hp_assists_10m_calculated",
        "hp_hill_time_10m",
        "hp_contested_time_10m",
        "hp_non_traded_kill_pct_calculated",
        "snd_first_bloods_per_round",
        "snd_non_traded_kill_pct_calculated",
        "snd_objective_actions_per_round",
        "ctl_kills_10m_calculated",
        "ctl_assists_10m_calculated",
        "ctl_non_traded_kill_pct_calculated",
        "ctl_ticks_per_attack_round",
    ]

    print(
        selected[selected_columns]
        .to_string(
            index=False,
            formatters={
                "hp_assists_10m_calculated": (
                    lambda value: f"{value:.2f}"
                ),
                "hp_hill_time_10m": (
                    lambda value: f"{value:.2f}"
                ),
                "hp_contested_time_10m": (
                    lambda value: f"{value:.2f}"
                ),
                "hp_non_traded_kill_pct_calculated": (
                    lambda value: f"{value:.1%}"
                ),
                "snd_first_bloods_per_round": (
                    lambda value: f"{value:.3f}"
                ),
                "snd_non_traded_kill_pct_calculated": (
                    lambda value: f"{value:.1%}"
                ),
                "snd_objective_actions_per_round": (
                    lambda value: f"{value:.3f}"
                ),
                "ctl_kills_10m_calculated": (
                    lambda value: f"{value:.2f}"
                ),
                "ctl_assists_10m_calculated": (
                    lambda value: f"{value:.2f}"
                ),
                "ctl_non_traded_kill_pct_calculated": (
                    lambda value: f"{value:.1%}"
                ),
                "ctl_ticks_per_attack_round": (
                    lambda value: f"{value:.2f}"
                ),
            },
        )
    )

    print("\nTop five players in each extended metric")
    print("=" * 118)

    for metric, label in EXTENDED_METRICS.items():
        print(f"\n{label}")
        print("-" * 70)

        leaders = eligible[
            [
                "player_tag",
                "game_count",
                metric,
            ]
        ].sort_values(
            metric,
            ascending=False,
        ).head(5)

        print(
            leaders.to_string(
                index=False,
                formatters={
                    metric: lambda value: f"{value:.4f}",
                },
            )
        )

    print("\nCreated file")
    print("=" * 118)
    print(OUTPUT_PATH)


if __name__ == "__main__":
    main()
