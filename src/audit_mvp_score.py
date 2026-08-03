"""Diagnose the BO6 MVP Impact Score and identify overlapping metrics."""

from __future__ import annotations

from pathlib import Path

import pandas as pd


INPUT_PATH = Path(
    "data/processed/bo6_mvp_leaderboard.csv"
)

DIAGNOSTIC_OUTPUT_PATH = Path(
    "data/interim/bo6_mvp_score_diagnostics.csv"
)

CORRELATION_OUTPUT_PATH = Path(
    "data/interim/bo6_mvp_metric_correlations.csv"
)

METRICS = {
    "kd": {
        "component": "overall_kd_score",
        "weight": 0.25,
        "label": "Overall KD",
    },
    "hp_dmg_10m": {
        "component": "hp_damage_score",
        "weight": 0.20,
        "label": "HP Damage",
    },
    "hp_k_10m": {
        "component": "hp_pace_score",
        "weight": 0.15,
        "label": "HP Pace",
    },
    "snd_kd_calculated": {
        "component": "snd_kd_score",
        "weight": 0.15,
        "label": "SND KD",
    },
    "snd_kills_per_round": {
        "component": "snd_kpr_score",
        "weight": 0.10,
        "label": "SND KPR",
    },
    "snd_opening_duel_win_pct_calculated": {
        "component": "snd_opening_duel_score",
        "weight": 0.10,
        "label": "SND Opening",
    },
    "ctl_dmg_10m": {
        "component": "control_damage_score",
        "weight": 0.05,
        "label": "CTL Damage",
    },
}

NOTABLE_PLAYERS = [
    "Scrap",
    "HyDra",
    "Dashy",
    "RenKoR",
    "Cellium",
    "Shotzzy",
    "Ghosty",
    "Envoy",
    "Nero",
    "Mercules",
]


def require_columns(
    dataframe: pd.DataFrame,
    columns: list[str],
) -> None:
    """Validate that expected leaderboard columns exist."""

    missing = [
        column
        for column in columns
        if column not in dataframe.columns
    ]

    if missing:
        raise RuntimeError(
            "Missing required columns: "
            + ", ".join(missing)
        )


def main() -> None:
    if not INPUT_PATH.exists():
        raise FileNotFoundError(
            f"{INPUT_PATH} was not found."
        )

    dataframe = pd.read_csv(INPUT_PATH)

    required_columns = [
        "mvp_rank",
        "player_tag",
        "mvp_score",
        "impact_score",
        "consistency_multiplier",
        "game_count",
    ]

    for configuration in METRICS.values():
        required_columns.append(
            configuration["component"]
        )

    required_columns.extend(
        METRICS.keys()
    )

    require_columns(
        dataframe,
        required_columns,
    )

    contribution_columns = []

    for metric, configuration in METRICS.items():
        contribution_column = (
            f"{metric}_contribution"
        )

        dataframe[contribution_column] = (
            dataframe[configuration["component"]]
            * configuration["weight"]
        )

        contribution_columns.append(
            contribution_column
        )

    dataframe["calculated_impact_score"] = (
        dataframe[contribution_columns]
        .sum(axis=1)
    )

    dataframe["impact_score_difference"] = (
        dataframe["impact_score"]
        - dataframe["calculated_impact_score"]
    )

    dataframe.to_csv(
        DIAGNOSTIC_OUTPUT_PATH,
        index=False,
    )

    raw_metric_columns = list(
        METRICS.keys()
    )

    correlations = (
        dataframe[raw_metric_columns]
        .corr()
    )

    correlations.to_csv(
        CORRELATION_OUTPUT_PATH
    )

    print("MVP score diagnostic")
    print("=" * 110)
    print(f"Eligible players: {len(dataframe)}")
    print(f"Input file: {INPUT_PATH}")

    print("\nRaw metric correlation matrix")
    print("=" * 110)

    print(
        correlations
        .round(3)
        .to_string()
    )

    print("\nStrong metric relationships")
    print("=" * 110)

    relationships = []

    for left_index, left_metric in enumerate(
        raw_metric_columns
    ):
        for right_metric in raw_metric_columns[
            left_index + 1:
        ]:
            correlation = correlations.loc[
                left_metric,
                right_metric,
            ]

            if abs(correlation) >= 0.65:
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
            "No metric pairs have an absolute "
            "correlation of at least 0.65."
        )
    else:
        for left, right, correlation in relationships:
            print(
                f"{left:<42} "
                f"{right:<42} "
                f"{correlation:>7.3f}"
            )

    print("\nTop 15 component breakdown")
    print("=" * 110)

    display_columns = [
        "mvp_rank",
        "player_tag",
        "mvp_score",
        "impact_score",
        "consistency_multiplier",
        "game_count",
        *contribution_columns,
    ]

    print(
        dataframe[display_columns]
        .head(15)
        .to_string(
            index=False,
            formatters={
                "mvp_score": lambda value: f"{value:.2f}",
                "impact_score": lambda value: f"{value:.2f}",
                "consistency_multiplier": (
                    lambda value: f"{value:.3f}"
                ),
                **{
                    column: (
                        lambda value: f"{value:.2f}"
                    )
                    for column in contribution_columns
                },
            },
        )
    )

    print("\nSelected player profiles")
    print("=" * 110)

    selected = dataframe[
        dataframe["player_tag"].isin(
            NOTABLE_PLAYERS
        )
    ].copy()

    selected = selected.sort_values(
        "mvp_rank"
    )

    if selected.empty:
        print("No selected players were found.")
    else:
        print(
            selected[display_columns]
            .to_string(
                index=False,
                formatters={
                    "mvp_score": (
                        lambda value: f"{value:.2f}"
                    ),
                    "impact_score": (
                        lambda value: f"{value:.2f}"
                    ),
                    "consistency_multiplier": (
                        lambda value: f"{value:.3f}"
                    ),
                    **{
                        column: (
                            lambda value: f"{value:.2f}"
                        )
                        for column in contribution_columns
                    },
                },
            )
        )

    print("\nCreated files")
    print("=" * 110)
    print(DIAGNOSTIC_OUTPUT_PATH)
    print(CORRELATION_OUTPUT_PATH)


if __name__ == "__main__":
    main()
