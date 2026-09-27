# Photon Laser Tag System — Project Specification

## 1. Purpose

Build a laser tag game-management application that allows an operator to register players, assign equipment, run timed games, communicate with laser tag hardware over UDP, and display live scoring information.

The application may use more than one window or screen.

## 2. Runtime Environment

| Requirement | Value |
| --- | --- |
| Operating system | Debian virtual machine supplied by the instructor |
| Implementation language | Team's choice |
| Database system | PostgreSQL |
| Database name | `photon` |
| Player table | `players` |
| Default network address | `127.0.0.1` |

## 3. Teams and Players

- A game has two teams: **red** and **green**.
- Each team may contain no more than 15 players.
- A persistent player is identified by a player ID and codename stored in PostgreSQL.
- Each player in the current game is assigned an integer equipment ID.
- Equipment assignments and scores apply to the current game rather than the permanent player record.

## 4. UDP Communication

The system must use two UDP sockets to communicate with the laser tag equipment.

| Direction | Port | Bind or destination | Purpose |
| --- | ---: | --- | --- |
| Server to equipment | `7500` | Default destination `127.0.0.1` | Broadcast equipment IDs and control codes |
| Equipment to server | `7501` | Listen on all local interfaces | Receive tag and base events |

The operator must be able to change the network address used for UDP transmission.

### 4.1 Outbound message format

Normal outbound messages contain one integer:

```text
<equipmentID>
```

The integer identifies the equipment belonging to the player who was hit.

### 4.2 Inbound message format

Normal inbound messages contain two integer equipment IDs separated by a colon:

```text
<transmittingEquipmentID>:<hitEquipmentID>
```

Example:

```text
12:34
```

In this example, equipment `12` transmitted the event and equipment `34` was hit.

### 4.3 Required control codes

| Code | Meaning | Required behavior |
| ---: | --- | --- |
| `202` | Game start | Broadcast once after the 30-second pre-game countdown finishes. |
| `221` | Game end | Broadcast three times when the game ends. |
| `53` | Red base hit | Award 100 points when the scoring player belongs to the green team and display the base icon beside that player's codename. |
| `43` | Green base hit | Award 100 points when the scoring player belongs to the red team and display the base icon beside that player's codename. |

### 4.4 Tag responses

When a tag event is received:

- Broadcast the equipment ID of the player who was hit.
- If the tag was between players on the same team, also broadcast the tagging player's equipment ID.
- A same-team tag therefore results in two outbound transmissions.

## 5. Application Flow

### 5.1 Startup

1. Display the supplied logo on a splash screen for three seconds.
2. Automatically proceed to the player-entry screen.

### 5.2 Player entry

For each player:

1. The operator enters a player ID.
2. The application queries PostgreSQL for the corresponding codename.
3. If the player is not found, prompt the operator for a codename and add a persistent player record to the database.
4. Prompt the operator for the integer equipment ID assigned to the player.
5. Assign the player to either the red or green team.
6. Broadcast the equipment ID through UDP port `7500`.
7. Add the player to the current game roster.

The player-entry screen must also provide:

- A maximum of 15 players per team.
- A single action to clear all current entries, using `F12` or an equivalent button.
- An action to start the game and open the play-action screen, using `F5` or an equivalent button.

### 5.3 Pre-game countdown

1. Display a 30-second warning countdown.
2. Keep the game in a pre-start state during the countdown.
3. Broadcast code `202` when the countdown finishes.
4. Begin the six-minute game timer.

### 5.4 Active game

During play, the application must continuously:

- Receive equipment events through UDP port `7501`.
- Apply individual and team scoring rules.
- Display play-by-play events.
- Update team scores.
- Update and sort individual scores.
- Visually indicate the team currently in the lead.
- Play a random supplied MP3 file synchronized with the game countdown.

### 5.5 End of game

1. End the game after the six-minute timer expires.
2. Broadcast code `221` three times.
3. Stop or synchronize the music with the completed timer.
4. Leave the play-action screen visible with the final state.
5. Provide a button that returns the operator to the player-entry screen.

## 6. Scoring Rules

| Event | Tagging player | Hit player |
| --- | ---: | ---: |
| Tag a player on the opposing team | `+10` | No specified change |
| Tag a player on the same team | `-10` | `-10` |
| Valid opposing-team base score | `+100` | Not applicable |

Additional requirements:

- Team totals must update whenever an individual score changes.
- Players must be displayed from highest to lowest score within each team.
- The team with the higher score must flash during active play.

## 7. Play-Action Screen

The play-action screen must contain three continuously updating areas:

1. **Play-by-play feed** — displays game events and allows older events to scroll out of view.
2. **Team scores** — displays cumulative red and green team scores.
3. **Individual scores** — displays each team's players ordered from highest to lowest score.

When a player earns a valid base score, place the supplied base icon to the left of that player's codename.

## 8. Supplied Assets

The application depends on assets supplied through the instructor's GitHub repository:

- Startup logo
- Base icon
- MP3 music files
- Player-entry screen captures or layout examples

## 9. Acceptance Checklist

- [ ] Runs on the supplied Debian virtual machine.
- [ ] Connects to the `photon` PostgreSQL database and `players` table.
- [ ] Displays the splash screen for three seconds.
- [ ] Supports persistent player lookup and creation.
- [ ] Supports red and green rosters with no more than 15 players each.
- [ ] Assigns and broadcasts an integer equipment ID for every game player.
- [ ] Allows all current-game entries to be cleared at once.
- [ ] Allows the UDP destination network to be changed.
- [ ] Sends on UDP port `7500` and receives on UDP port `7501` from any interface.
- [ ] Displays a 30-second pre-game warning and broadcasts `202` at game start.
- [ ] Runs a six-minute game.
- [ ] Processes opponent tags, friendly-fire tags, and base scores.
- [ ] Continuously updates the play-by-play feed, team totals, and individual scores.
- [ ] Sorts individual scores from highest to lowest within each team.
- [ ] Flashes the leading team's score.
- [ ] Plays a random supplied MP3 synchronized with the game timer.
- [ ] Broadcasts `221` three times at game end.
- [ ] Keeps the final play-action screen visible and provides a return action.

## 10. Clarifications Needed

The source specification does not completely define the following behavior. These items should be confirmed with the instructor before the relevant implementation is finalized.

1. **Localhost versus LAN broadcast:** `127.0.0.1` is specified as the default address, but it is a loopback unicast address rather than a LAN broadcast address.
2. **Network-change protocol:** The payload, acknowledgment behavior, and transition timing for changing networks are not defined.
3. **New player IDs:** The specification does not state whether a newly created database player keeps the operator-entered ID or receives a server-generated ID.
4. **Base-code position:** It is not stated whether `43` and `53` appear as the transmitting ID, the hit ID, or as standalone messages.
5. **Friendly-fire transmission order:** The required order of the two outbound equipment IDs is not stated.
6. **Clear behavior:** “Clear all entries” is assumed to clear the current game roster without deleting persistent database players.
7. **Timer boundary:** It is assumed that the 30-second warning occurs before, rather than as part of, the six-minute game.
8. **Music behavior:** The expected behavior when the selected MP3 is shorter or longer than the game is not defined.
