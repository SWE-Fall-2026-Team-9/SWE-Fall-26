#!/usr/bin/env python3
"""Testbench for the Socket.IO game-event plumbing and UDP receive loop.

This verifies:

- UDP events are described as tag/base-hit event dictionaries.
- Events are emitted to Socket.IO clients.
- UDP responses are sent for every inbound event.
- The game page signals readiness before the start signal is sent.
- The receive loop applies the game scoring rules.
- The game page listens for ``game-event`` and appends it to the feed.

Run from the project root:

    python tests/test_game_events.py
"""

import os
import sys
import unittest
from datetime import datetime


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

# Importing app.py constructs the UDP receiver, which binds port 7501. Replace
# the constructor during import so the testbench can run without a socket and
# does not conflict with a running server.
from modules import udp

_original_receiver_init = udp.Receiver.__init__


def _receiver_init_without_socket(self, logger=None):
    self.sock = None
    self.logger = logger


udp.Receiver.__init__ = _receiver_init_without_socket

try:
    import app
finally:
    udp.Receiver.__init__ = _original_receiver_init


class FakeReceiver:
    """Return queued UDP messages, then stop the receive loop with OSError."""

    def __init__(self, messages):
        self.messages = list(messages)

    def recv(self):
        if self.messages:
            return self.messages.pop(0)
        raise OSError("No more test messages")


class FakeTransmitter:
    """Record outbound equipment IDs."""

    def __init__(self):
        self.sent = []

    def send(self, equipment_id):
        self.sent.append(equipment_id)


class FailingTransmitter:
    """Raise on send so tests can verify UDP failures are isolated."""

    def send(self, equipment_id):
        raise OSError("UDP send failed")


class EventTestBase(unittest.TestCase):
    def setUp(self):
        # Never let the testbench send real UDP packets to port 7500.
        self.original_transmitter = app.transmitter
        self.fake_transmitter = FakeTransmitter()
        app.transmitter = self.fake_transmitter

        app.gamePlayers.clear()
        app.playerEquipment.clear()
        app.scores.clear()
        app.game_started = False
        app.gameStartTime = datetime.now()

        app.gamePlayers[1] = {
            "playerID": 1,
            "codename": "Alpha",
            "equipmentID": 12,
            "team": "red",
            "hasHitBase": False,
        }
        app.gamePlayers[2] = {
            "playerID": 2,
            "codename": "Bravo",
            "equipmentID": 34,
            "team": "green",
            "hasHitBase": False,
        }
        app.playerEquipment[12] = 1
        app.playerEquipment[34] = 2
        app.scores[1] = 0
        app.scores[2] = 0

    def tearDown(self):
        app.transmitter = self.original_transmitter


class GameStartTests(EventTestBase):
    def setUp(self):
        super().setUp()
        self.client = app.socket.test_client(app.app)
        self.client.get_received()  # Drain the connect message.

    def tearDown(self):
        self.client.disconnect()
        super().tearDown()

    def test_game_page_does_not_start_generator(self):
        web_client = app.app.test_client()

        response = web_client.get('/game')

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"socket.emit('game-ready')", response.data)
        self.assertEqual(self.fake_transmitter.sent, [])
        self.assertFalse(app.game_started)

    def test_game_ready_starts_generator_once(self):
        self.client.emit('game-ready')
        first_start_time = app.gameStartTime
        self.client.emit('game-ready')

        self.assertEqual(self.fake_transmitter.sent, [202])
        self.assertTrue(app.game_started)
        self.assertIsNotNone(first_start_time)
        self.assertIs(app.gameStartTime, first_start_time)


class BuildGameEventTests(EventTestBase):
    def test_tag_event_resolves_both_players(self):
        event = app.build_game_event(12, 34)

        self.assertEqual(event["type"], "tag")
        self.assertEqual(event["transmitterEquipmentID"], 12)
        self.assertEqual(event["hitEquipmentID"], 34)
        self.assertEqual(event["message"], "Alpha tagged Bravo (+10)")
        self.assertIsInstance(event["timestamp"], tuple)
        self.assertEqual(len(event["timestamp"]), 2)
        self.assertTrue(all(isinstance(value, int) for value in event["timestamp"]))
        self.assertEqual(
            event["transmitter"],
            {"playerID": 1, "codename": "Alpha", "team": "red"},
        )
        self.assertEqual(
            event["hit"],
            {"playerID": 2, "codename": "Bravo", "team": "green"},
        )

    def test_tag_event_falls_back_for_unknown_transmitter(self):
        event = app.build_game_event(99, 34)

        self.assertEqual(event["type"], "tag")
        self.assertIsNone(event["transmitter"])
        self.assertEqual(event["hit"]["codename"], "Bravo")
        self.assertEqual(event["message"], "Equipment 99 tagged Bravo")

    def test_tag_event_falls_back_for_two_unknown_ids(self):
        event = app.build_game_event(99, 77)

        self.assertIsNone(event["transmitter"])
        self.assertIsNone(event["hit"])
        self.assertEqual(event["message"], "Equipment 99 tagged Equipment 77")

    def test_red_base_code_as_hit_id(self):
        event = app.build_game_event(34, app.RED_BASE_CODE)

        self.assertEqual(event["type"], "base-hit")
        self.assertEqual(event["base"], "red")
        self.assertEqual(event["transmitterEquipmentID"], 34)
        self.assertEqual(event["hitEquipmentID"], app.RED_BASE_CODE)
        self.assertEqual(event["message"], "Bravo hit the red base (+100)")

    def test_green_base_code_as_transmitter_id(self):
        event = app.build_game_event(app.GREEN_BASE_CODE, 12)

        self.assertEqual(event["type"], "base-hit")
        self.assertEqual(event["base"], "green")
        self.assertEqual(event["transmitterEquipmentID"], app.GREEN_BASE_CODE)
        self.assertEqual(event["hitEquipmentID"], 12)
        self.assertEqual(event["message"], "Alpha hit the green base (+100)")

    def test_invalid_base_hit_shows_no_points(self):
        # Alpha is on the red team, so hitting the red base is not valid.
        event = app.build_game_event(12, app.RED_BASE_CODE)

        self.assertEqual(event["base"], "red")
        self.assertEqual(event["message"], "Alpha hit the red base (no points)")

    def test_same_team_tag_shows_negative_points_for_both(self):
        app.gamePlayers[3] = {
            "playerID": 3,
            "codename": "Charlie",
            "equipmentID": 56,
            "team": "red",
            "hasHitBase": False,
        }
        app.playerEquipment[56] = 3

        event = app.build_game_event(12, 56)

        self.assertEqual(event["message"], "Alpha tagged teammate Charlie (-10 each)")


class SocketEmissionTests(EventTestBase):
    def setUp(self):
        super().setUp()
        self.client = app.socket.test_client(app.app)
        self.client.get_received()  # Drain the connect message.

    def tearDown(self):
        self.client.disconnect()
        super().tearDown()

    def get_game_events(self):
        return [
            message["args"][0]
            for message in self.client.get_received()
            if message["name"] == "game-event"
        ]

    def test_process_tag_event_emits_game_event(self):
        app.process_game_event(12, 34)
        events = self.get_game_events()

        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["type"], "tag")
        self.assertEqual(events[0]["message"], "Alpha tagged Bravo (+10)")
        self.assertIsNotNone(events[0]["timestamp"])

    def test_process_base_event_emits_game_event(self):
        app.process_game_event(34, app.RED_BASE_CODE)
        events = self.get_game_events()

        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["type"], "base-hit")
        self.assertEqual(events[0]["base"], "red")
        self.assertEqual(events[0]["message"], "Bravo hit the red base (+100)")

    def test_udp_response_failure_still_emits_event(self):
        original_transmitter = app.transmitter
        app.transmitter = FailingTransmitter()

        try:
            with self.assertLogs("app", level="WARNING") as logs:
                app.process_game_event(12, 34)
        finally:
            app.transmitter = original_transmitter

        events = self.get_game_events()
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["message"], "Alpha tagged Bravo (+10)")
        self.assertTrue(any("UDP response failed" in line for line in logs.output))

    def test_receive_loop_emits_events(self):
        original_receiver = app.receiver
        app.receiver = FakeReceiver([(12, 34), (34, app.RED_BASE_CODE)])

        try:
            with self.assertLogs("app", level="ERROR"):
                app.receive_messages()
        finally:
            app.receiver = original_receiver

        events = self.get_game_events()
        self.assertEqual(len(events), 2)
        self.assertEqual(events[0]["message"], "Alpha tagged Bravo (+10)")
        self.assertEqual(events[1]["message"], "Bravo hit the red base (+100)")

    def test_base_event_not_emitted_after_has_hit_base(self):
        app.gamePlayers[2]["hasHitBase"] = True

        app.process_game_event(34, app.RED_BASE_CODE)

        self.assertEqual(self.get_game_events(), [])
        self.assertEqual(self.fake_transmitter.sent, [app.RED_BASE_CODE])

    def test_receive_loop_emits_for_each_udp_message(self):
        original_receiver = app.receiver
        app.receiver = FakeReceiver([(12, 34), (34, app.RED_BASE_CODE)])

        try:
            # The fake receiver ends the loop with OSError, which the loop logs.
            with self.assertLogs("app", level="ERROR") as logs:
                app.receive_messages()
        finally:
            app.receiver = original_receiver

        self.assertIn("UDP receiver stopped", logs.output[0])
        events = self.get_game_events()
        self.assertEqual(len(events), 2)
        self.assertEqual(events[0]["message"], "Alpha tagged Bravo (+10)")
        self.assertEqual(events[1]["message"], "Bravo hit the red base (+100)")


class EventResponseTests(EventTestBase):
    def test_opposing_tag_sends_hit_equipment_id(self):
        app.process_game_event(12, 34)

        self.assertEqual(self.fake_transmitter.sent, [34])

    def test_same_team_tag_sends_hit_then_tagger(self):
        app.gamePlayers[3] = {
            "playerID": 3,
            "codename": "Charlie",
            "equipmentID": 56,
            "team": "red",
            "hasHitBase": False,
        }
        app.playerEquipment[56] = 3
        app.scores[3] = 0

        app.process_game_event(12, 56)

        self.assertEqual(self.fake_transmitter.sent, [56, 12])

    def test_unknown_equipment_sends_only_hit_equipment_id(self):
        app.process_game_event(99, 34)

        self.assertEqual(self.fake_transmitter.sent, [34])

    def test_base_event_sends_hit_equipment_id(self):
        app.process_game_event(34, app.RED_BASE_CODE)

        self.assertEqual(self.fake_transmitter.sent, [app.RED_BASE_CODE])

    def test_repeated_base_event_still_sends_hit_equipment_id(self):
        app.process_game_event(34, app.RED_BASE_CODE)
        app.process_game_event(34, app.RED_BASE_CODE)

        self.assertEqual(
            self.fake_transmitter.sent,
            [app.RED_BASE_CODE, app.RED_BASE_CODE],
        )


class ScoringLoopTests(EventTestBase):
    """Exercise the scoring rules owned by ``receive_messages``.

    The scoring loop indexes ``gamePlayers`` and ``scores`` with the IDs that
    the UDP receiver returns, so these tests align player IDs with equipment
    IDs. Event construction is covered separately with equipment IDs.
    """

    def setUp(self):
        super().setUp()
        app.gamePlayers.clear()
        app.playerEquipment.clear()
        app.scores.clear()
        app.game_started = False

        app.gamePlayers[12] = {
            "playerID": 12,
            "codename": "Alpha",
            "equipmentID": 12,
            "team": "red",
            "hasHitBase": False,
        }
        app.gamePlayers[34] = {
            "playerID": 34,
            "codename": "Bravo",
            "equipmentID": 34,
            "team": "green",
            "hasHitBase": False,
        }
        app.playerEquipment[12] = 12
        app.playerEquipment[34] = 34
        app.scores[12] = 0
        app.scores[34] = 0

        self.client = app.socket.test_client(app.app)
        self.client.get_received()  # Drain the connect message.

    def tearDown(self):
        self.client.disconnect()
        super().tearDown()

    def get_game_events(self):
        return [
            message["args"][0]
            for message in self.client.get_received()
            if message["name"] == "game-event"
        ]

    def run_loop(self, messages):
        original_receiver = app.receiver
        app.receiver = FakeReceiver(messages)

        try:
            with self.assertLogs("app", level="ERROR"):
                app.receive_messages()
        finally:
            app.receiver = original_receiver

    def test_receive_loop_applies_scoring_rules(self):
        self.run_loop([(12, 34), (34, app.RED_BASE_CODE)])

        events = self.get_game_events()
        self.assertEqual(len(events), 2)
        self.assertEqual(events[0]["message"], "Alpha tagged Bravo (+10)")
        self.assertEqual(events[1]["message"], "Bravo hit the red base (+100)")
        self.assertEqual(app.scores, {12: 10, 34: 100})
        self.assertTrue(app.gamePlayers[34]["hasHitBase"])
        self.assertEqual(
            self.fake_transmitter.sent,
            [34, app.RED_BASE_CODE],
        )

    def test_receive_loop_skips_duplicate_base_event(self):
        self.run_loop([(34, app.RED_BASE_CODE), (34, app.RED_BASE_CODE)])

        events = self.get_game_events()
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["message"], "Bravo hit the red base (+100)")
        self.assertEqual(app.scores[34], 100)
        self.assertTrue(app.gamePlayers[34]["hasHitBase"])
        # Base hits get a reply for every inbound message, even when the
        # play-by-play event is suppressed.
        self.assertEqual(
            self.fake_transmitter.sent,
            [app.RED_BASE_CODE, app.RED_BASE_CODE],
        )

    def test_receive_loop_subtracts_for_friendly_fire(self):
        app.gamePlayers[56] = {
            "playerID": 56,
            "codename": "Charlie",
            "equipmentID": 56,
            "team": "red",
            "hasHitBase": False,
        }
        app.playerEquipment[56] = 56
        app.scores[56] = 0

        self.run_loop([(12, 56)])

        self.assertEqual(app.scores, {12: -10, 34: 0, 56: -10})
        self.assertEqual(self.fake_transmitter.sent, [56, 12])

    def test_invalid_base_hit_does_not_award_points(self):
        self.run_loop([(12, app.RED_BASE_CODE)])

        self.assertEqual(app.scores[12], 0)
        self.assertFalse(app.gamePlayers[12]["hasHitBase"])
        self.assertEqual(self.fake_transmitter.sent, [app.RED_BASE_CODE])
        events = self.get_game_events()
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["message"], "Alpha hit the red base (no points)")


class ClientTemplateTests(unittest.TestCase):
    def test_player_entry_syncs_game_start_to_random_track(self):
        template_path = os.path.join(PROJECT_ROOT, "templates", "player_entry.html")
        with open(template_path) as template:
            html = template.read()

        for track_number in range(1, 9):
            track_name = f"Track{track_number:02}.mp3"
            self.assertIn(f"photon_tracks/{track_name}", html)
            self.assertTrue(
                os.path.isfile(
                    os.path.join(PROJECT_ROOT, "static", "photon_tracks", track_name)
                )
            )

        self.assertIn("Math.floor(Math.random() * gameTracks.length)", html)
        self.assertIn("const countdownDuration = 30;", html)
        self.assertIn('countdown30.png', html)
        self.assertIn("countdownImage.src = countdownAssetUrl + imageName;", html)
        self.assertIn("if (remainingMs <= 15000 && !musicStarted)", html)
        self.assertIn('window.location.href = "/game";', html)

        with open(os.path.join(PROJECT_ROOT, "templates", "game.html")) as template:
            game_html = template.read()
        self.assertIn('sessionStorage.getItem("photonGameTrack")', game_html)
        self.assertIn("gameAudio.currentTime = elapsedSeconds;", game_html)

    def test_game_page_wires_game_event_to_feed(self):
        with open(os.path.join(PROJECT_ROOT, "templates", "game.html")) as template:
            html = template.read()

        self.assertIn("socket.on('game-event'", html)
        self.assertIn('document.getElementById("events")', html)
        self.assertIn("events.insertBefore(eventBox, events.firstChild)", html)
        self.assertIn("events.scrollTop = 0", html)
        self.assertIn("event.timestamp", html)
        self.assertIn("timestamp[0]", html)
        self.assertIn("timestamp[1]", html)
        self.assertIn("formatter.format(timestamp[0])", html)
        self.assertIn("formatter.format(timestamp[1])", html)
        self.assertIn("socket.emit('game-ready')", html)
        self.assertNotIn("socket.on('player-hit'", html)

    def test_game_page_loads_local_socketio_client(self):
        with open(os.path.join(PROJECT_ROOT, "templates", "game.html")) as template:
            html = template.read()

        self.assertIn("socket.io.min.js", html)
        self.assertNotIn("/socket.io/socket.io.js", html)


if __name__ == "__main__":
    unittest.main(verbosity=2)
