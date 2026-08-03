"""Fetch BO6 player statistics for CDL franchises from BreakingPoint."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd
import requests


BASE_URL = "https://breakingpoint.gg/api/trpc"
PROCEDURE = (
    "cached.playerStats."
    "getAggregatedOrderedPlayerStats"
)

SEASON_ID = 2025
MODE_IDS = [1, 2, 3]

NEXT_DATA_PATH = Path(
    "data/raw/breakingpoint_next_data.json"
)

OUTPUT_PATH = Path(
    "data/raw/breakingpoint_bo6_player_stats.json"
)


def load_page_props() -> dict[str, Any]:
    """Load BreakingPoint reference data from the saved Next.js payload."""

    if not NEXT_DATA_PATH.exists():
        raise FileNotFoundError(
            f"{NEXT_DATA_PATH} does not exist."
        )

    next_data = json.loads(
        NEXT_DATA_PATH.read_text(encoding="utf-8")
    )

    page_props = (
        next_data
        .get("props", {})
        .get("pageProps", {})
    )

    if not page_props:
        raise RuntimeError(
            "No BreakingPoint pageProps data was found."
        )

    return page_props


def get_bo6_map_ids(
    page_props: dict[str, Any],
) -> list[int]:
    """Return every map associated with the BO6 season."""

    return sorted(
        {
            int(game_map["id"])
            for game_map in page_props.get("allMaps", [])
            if game_map.get("season_id") == SEASON_ID
            and game_map.get("id") is not None
        }
    )


def get_cdl_team_ids(
    page_props: dict[str, Any],
) -> tuple[list[int], list[tuple[int, str]]]:
    """Return teams listed by BreakingPoint as participating in BO6."""

    selected_teams = []

    for team in page_props.get("allTeams", []):
        season_ids = team.get("season_ids") or []

        if SEASON_ID in season_ids:
            selected_teams.append(
                (
                    int(team["id"]),
                    str(team["name"]),
                )
            )

    selected_teams.sort(
        key=lambda team: team[1].lower()
    )

    team_ids = [
        team_id
        for team_id, _ in selected_teams
    ]

    return team_ids, selected_teams


def extract_result(
    payload: Any,
) -> list[dict[str, Any]]:
    """Extract player rows from a tRPC response."""

    if not isinstance(payload, dict):
        raise RuntimeError(
            "Unexpected response format."
        )

    result = (
        payload
        .get("result", {})
        .get("data", {})
        .get("json")
    )

    if not isinstance(result, list):
        raise RuntimeError(
            "The response did not contain a player list."
        )

    return result


def main() -> None:
    page_props = load_page_props()

    map_ids = get_bo6_map_ids(page_props)
    team_ids, selected_teams = get_cdl_team_ids(
        page_props
    )

    if not map_ids:
        raise RuntimeError(
            "No BO6 map IDs were found."
        )

    if not team_ids:
        raise RuntimeError(
            "No BO6 CDL team IDs were found."
        )

    print("BO6 collection filters")
    print("=" * 72)
    print(f"Season ID: {SEASON_ID}")
    print(f"Mode IDs: {MODE_IDS}")
    print(f"Map IDs: {map_ids}")

    print("\nCDL teams included")
    print("=" * 72)

    for team_id, team_name in selected_teams:
        print(f"{team_id:<6} {team_name}")

    print(f"\nTotal team IDs: {len(team_ids)}")

    request_payload = {
        "eventType": [],
        "mapId": map_ids,
        "modeId": MODE_IDS,
        "teamId": team_ids,
        "sortBy": "bp_rating",
        "eventId": [],
        "activePlayersOnly": False,
        "seasonId": SEASON_ID,
    }

    session = requests.Session()

    session.headers.update(
        {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 Chrome/130 Safari/537.36"
            ),
            "Accept": "application/json",
            "Referer": "https://breakingpoint.gg/stats",
            "Origin": "https://breakingpoint.gg",
            "x-trpc-source": "nextjs-react",
        }
    )

    response = session.get(
        f"{BASE_URL}/{PROCEDURE}",
        params={
            "input": json.dumps(
                {"json": request_payload},
                separators=(",", ":"),
            )
        },
        timeout=60,
    )

    print("\nBreakingPoint response")
    print("=" * 72)
    print(f"Status code: {response.status_code}")
    print(f"Response size: {len(response.content):,} bytes")

    response.raise_for_status()

    player_rows = extract_result(
        response.json()
    )

    if not player_rows:
        raise RuntimeError(
            "BreakingPoint returned zero players."
        )

    OUTPUT_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    OUTPUT_PATH.write_text(
        json.dumps(
            player_rows,
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    dataframe = pd.DataFrame(player_rows)

    print("\nCDL-filtered BO6 dataset")
    print("=" * 72)
    print(f"Player rows returned: {len(dataframe)}")
    print(f"Columns returned: {len(dataframe.columns)}")
    print(f"Saved to: {OUTPUT_PATH}")

    dataframe["game_count"] = pd.to_numeric(
        dataframe["game_count"],
        errors="coerce",
    )

    print("\nGame-count distribution")
    print("=" * 72)
    print(
        dataframe["game_count"]
        .describe()
        .to_string()
    )

    display_columns = [
        column
        for column in [
            "player_tag",
            "game_count",
            "hp_game_count",
            "snd_game_count",
            "ctl_game_count",
            "kd",
            "bp_rating",
        ]
        if column in dataframe.columns
    ]

    print("\nPlayers with the fewest games")
    print("=" * 72)

    print(
        dataframe[display_columns]
        .sort_values(
            "game_count",
            ascending=True,
        )
        .head(20)
        .to_string(index=False)
    )

    print("\nPlayers with the most games")
    print("=" * 72)

    print(
        dataframe[display_columns]
        .sort_values(
            "game_count",
            ascending=False,
        )
        .head(20)
        .to_string(index=False)
    )


if __name__ == "__main__":
    main()
