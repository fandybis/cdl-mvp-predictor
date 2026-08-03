"""Test BreakingPoint's tRPC player-statistics procedure for BO6."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import requests


BASE_URL = "https://breakingpoint.gg/api/trpc"
PROCEDURE = (
    "cached.playerStats."
    "getAggregatedOrderedPlayerStats"
)

NEXT_DATA_PATH = Path(
    "data/raw/breakingpoint_next_data.json"
)

OUTPUT_PATH = Path(
    "data/raw/breakingpoint_bo6_player_stats.json"
)

SEASON_ID = 2025
MODE_IDS = [1, 2, 3]


def get_bo6_map_ids() -> list[int]:
    """Read all BO6 map IDs from BreakingPoint's embedded page data."""

    if not NEXT_DATA_PATH.exists():
        raise FileNotFoundError(
            f"{NEXT_DATA_PATH} was not found."
        )

    next_data = json.loads(
        NEXT_DATA_PATH.read_text(encoding="utf-8")
    )

    all_maps = (
        next_data
        .get("props", {})
        .get("pageProps", {})
        .get("allMaps", [])
    )

    map_ids = sorted(
        {
            int(game_map["id"])
            for game_map in all_maps
            if game_map.get("season_id") == SEASON_ID
            and game_map.get("id") is not None
        }
    )

    return map_ids


def extract_result(payload: Any) -> Any:
    """Extract tRPC result data from single or batched responses."""

    if isinstance(payload, list):
        if not payload:
            return None

        payload = payload[0]

    if not isinstance(payload, dict):
        return None

    result = payload.get("result", {})
    data = result.get("data")

    if isinstance(data, dict) and "json" in data:
        return data["json"]

    return data


def request_single(
    session: requests.Session,
    request_payload: dict[str, Any],
) -> requests.Response:
    """Send a standard single tRPC GET request."""

    wrapped_input = {
        "json": request_payload,
    }

    return session.get(
        f"{BASE_URL}/{PROCEDURE}",
        params={
            "input": json.dumps(
                wrapped_input,
                separators=(",", ":"),
            )
        },
        timeout=60,
    )


def request_batch(
    session: requests.Session,
    request_payload: dict[str, Any],
) -> requests.Response:
    """Send a batched tRPC GET request."""

    wrapped_input = {
        "0": {
            "json": request_payload,
        }
    }

    return session.get(
        f"{BASE_URL}/{PROCEDURE}",
        params={
            "batch": "1",
            "input": json.dumps(
                wrapped_input,
                separators=(",", ":"),
            ),
        },
        timeout=60,
    )


def print_response(
    test_name: str,
    response: requests.Response,
) -> None:
    """Print enough response information for debugging."""

    print(f"\nTest: {test_name}")
    print("-" * 70)
    print(f"Status code: {response.status_code}")
    print(
        "Content type: "
        f"{response.headers.get('content-type')}"
    )
    print(f"Response size: {len(response.content):,} bytes")

    preview = response.text[:2000]

    print("\nResponse preview:")
    print(preview)

    if len(response.text) > 2000:
        print("\n... preview truncated ...")


def main() -> None:
    map_ids = get_bo6_map_ids()

    print(f"BO6 season ID: {SEASON_ID}")
    print(f"BO6 mode IDs: {MODE_IDS}")
    print(f"BO6 map IDs: {map_ids}")
    print(f"Number of BO6 maps: {len(map_ids)}")

    if not map_ids:
        raise RuntimeError(
            "No BO6 map IDs were found in the saved page data."
        )

    session = requests.Session()

    session.headers.update(
        {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 "
                "Chrome/130 Safari/537.36"
            ),
            "Accept": "application/json",
            "Referer": "https://breakingpoint.gg/stats",
            "Origin": "https://breakingpoint.gg",
            "x-trpc-source": "nextjs-react",
        }
    )

    payload_variants = [
        (
            "all BO6 maps — active players",
            {
                "eventType": [],
                "mapId": map_ids,
                "modeId": MODE_IDS,
                "teamId": [],
                "sortBy": "bp_rating",
                "eventId": [],
                "activePlayersOnly": True,
                "seasonId": SEASON_ID,
            },
        ),
        (
            "all BO6 maps — all players",
            {
                "eventType": [],
                "mapId": map_ids,
                "modeId": MODE_IDS,
                "teamId": [],
                "sortBy": "bp_rating",
                "eventId": [],
                "activePlayersOnly": False,
                "seasonId": SEASON_ID,
            },
        ),
        (
            "minimal BO6 request",
            {
                "sortBy": "bp_rating",
                "activePlayersOnly": False,
                "seasonId": SEASON_ID,
            },
        ),
    ]

    attempts = []

    for variant_name, request_payload in payload_variants:
        attempts.append(
            (
                f"single request: {variant_name}",
                request_single,
                request_payload,
            )
        )

        attempts.append(
            (
                f"batch request: {variant_name}",
                request_batch,
                request_payload,
            )
        )

    for test_name, request_function, request_payload in attempts:
        try:
            response = request_function(
                session,
                request_payload,
            )
        except requests.RequestException as exc:
            print(f"\nTest failed: {test_name}")
            print(exc)
            continue

        print_response(test_name, response)

        if response.status_code != 200:
            continue

        try:
            response_json = response.json()
        except ValueError:
            print("The response was not valid JSON.")
            continue

        result = extract_result(response_json)

        if not isinstance(result, list) or not result:
            print(
                "The request returned no non-empty player list."
            )
            continue

        OUTPUT_PATH.write_text(
            json.dumps(
                result,
                indent=2,
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

        print("\nSUCCESS")
        print("=" * 70)
        print(f"Player rows returned: {len(result)}")
        print(f"Saved player data to: {OUTPUT_PATH}")

        first_player = result[0]

        if isinstance(first_player, dict):
            print("\nFirst player record keys:")
            for key in sorted(first_player):
                print(key)

            print("\nFirst player record:")
            print(
                json.dumps(
                    first_player,
                    indent=2,
                    ensure_ascii=False,
                )[:5000]
            )

        return

    print("\nNo request variant returned player data.")
    print(
        "The response errors above should reveal which "
        "input field or encoding needs adjustment."
    )


if __name__ == "__main__":
    main()
