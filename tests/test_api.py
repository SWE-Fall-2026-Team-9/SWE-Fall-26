#!/usr/bin/env python3
"""Smoke-test the Flask API over HTTP without sending equipment messages.

Start the server first:

    python -m app

Then run this script from the project root:

    python scripts/test_api.py

An alternative server URL can be provided with --base-url.
"""

import argparse
import json
import sys
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class ApiTestFailure(Exception):
    """Raised when an API response does not match the expected contract."""


def request_json(base_url, method, path, body=None):
    """Send an HTTP request and return its status code and decoded JSON body."""
    encoded_body = None
    headers = {"Accept": "application/json"}

    if body is not None:
        encoded_body = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"

    request = Request(
        f"{base_url.rstrip('/')}{path}",
        data=encoded_body,
        headers=headers,
        method=method,
    )

    try:
        with urlopen(request, timeout=5) as response:
            status = response.status
            response_body = response.read().decode("utf-8")
    except HTTPError as error:
        status = error.code
        response_body = error.read().decode("utf-8")
    except URLError as error:
        raise ApiTestFailure(
            f"Could not connect to {base_url}: {error.reason}. "
            "Start the server with `python -m app` first."
        ) from error

    try:
        return status, json.loads(response_body)
    except json.JSONDecodeError as error:
        raise ApiTestFailure(
            f"{method} {path} returned non-JSON data with HTTP {status}: "
            f"{response_body!r}"
        ) from error


def require(condition, message):
    if not condition:
        raise ApiTestFailure(message)


def require_success(status, response, operation):
    require(status == 200, f"{operation} returned HTTP {status}: {response}")
    require(isinstance(response, dict), f"{operation} did not return a JSON object")
    require(response.get("success") is True, f"{operation} failed: {response}")
    return response.get("data")


def print_pass(description):
    print(f"PASS: {description}")


def run_tests(base_url):
    created_player_id = None
    test_codename = f"API_TEST_{int(time.time())}"
    updated_codename = f"{test_codename}_UPDATED"

    try:
        status, response = request_json(base_url, "GET", "/api/database/players")
        players = require_success(status, response, "List database players")
        require(isinstance(players, list), "Database player data is not an array")
        print_pass("listed persistent database players")

        status, response = request_json(
            base_url,
            "POST",
            "/api/database/players/create",
            {},
        )
        require(status == 200, f"Invalid-create test returned HTTP {status}")
        require(
            response.get("success") is False,
            f"Creating a player without a codename unexpectedly succeeded: {response}",
        )
        print_pass("rejected a missing codename")

        status, response = request_json(
            base_url,
            "POST",
            "/api/database/players/create",
            {"codename": test_codename},
        )
        created_player = require_success(status, response, "Create database player")
        require(isinstance(created_player, dict), "Created-player data is not an object")
        require(
            created_player.get("codename") == test_codename,
            f"Created player has the wrong codename: {created_player}",
        )
        created_player_id = created_player.get("playerID")
        require(
            isinstance(created_player_id, int),
            f"Created player has an invalid ID: {created_player}",
        )
        print_pass(f"created persistent player {created_player_id}")

        player_path = f"/api/database/players/{created_player_id}"
        status, response = request_json(base_url, "GET", player_path)
        retrieved_player = require_success(status, response, "Get database player")
        require(
            retrieved_player == created_player,
            f"Retrieved player does not match created player: {retrieved_player}",
        )
        print_pass("retrieved the created player")

        status, response = request_json(
            base_url,
            "POST",
            f"{player_path}/update",
            {"codename": updated_codename},
        )
        updated_player = require_success(status, response, "Update database player")
        require(
            updated_player.get("codename") == updated_codename,
            f"Player codename was not updated: {updated_player}",
        )
        print_pass("updated the player's codename")

        status, response = request_json(base_url, "GET", "/api/game/players")
        game_players = require_success(status, response, "List game players")
        require(isinstance(game_players, list), "Game-player data is not an array")
        print_pass("listed the current game roster without modifying it")

    finally:
        if created_player_id is not None:
            delete_path = f"/api/database/players/{created_player_id}/delete"
            try:
                status, response = request_json(base_url, "POST", delete_path)
                require_success(status, response, "Delete test database player")
                print_pass(f"deleted temporary player {created_player_id}")
            except ApiTestFailure as error:
                print(f"CLEANUP FAILED: {error}", file=sys.stderr)
                raise

    status, response = request_json(
        base_url,
        "GET",
        f"/api/database/players/{created_player_id}",
    )
    require(status == 200, f"Deleted-player lookup returned HTTP {status}")
    require(
        response.get("success") is False,
        f"Deleted player {created_player_id} is still available: {response}",
    )
    print_pass("confirmed the temporary player was deleted")


def main():
    parser = argparse.ArgumentParser(
        description="Test the Flask HTTP API without equipment communication."
    )
    parser.add_argument(
        "--base-url",
        default="http://127.0.0.1:8000",
        help="Flask server base URL (default: %(default)s)",
    )
    args = parser.parse_args()

    try:
        run_tests(args.base_url)
    except ApiTestFailure as error:
        print(f"FAIL: {error}", file=sys.stderr)
        return 1

    print("All client-server API tests passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
