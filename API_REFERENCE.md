# Client–Server API Reference

## Base URL

```text
http://127.0.0.1:8000
```

Use relative URLs when the frontend is served by the Flask application.

## Conventions

- JSON requests require `Content-Type: application/json`.
- Every API response contains a boolean `success` field.
- The frontend must inspect `success`; application errors may still use HTTP status `200`.
- Database players are persistent PostgreSQL records containing an ID and codename.
- Game players are temporary roster entries containing a database player, equipment assignment, team, and score.
- Creating a database player assigns `max(existing player IDs) + 1`, starting at `1` when the database is empty.

## Endpoint summary

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/api/database/players` | List persistent players |
| `POST` | `/api/database/players/create` | Create a persistent player |
| `GET` | `/api/database/players/{playerID}` | Get one persistent player |
| `POST` | `/api/database/players/{playerID}/update` | Update a persistent player's codename |
| `POST` | `/api/database/players/{playerID}/delete` | Permanently delete a player |
| `GET` | `/api/game/players` | List the current game roster |
| `POST` | `/api/game/players/add` | Add a persistent player to the game |
| `POST` | `/api/game/players/{playerID}/remove` | Remove one player from the game |
| `POST` | `/api/game/players/clear` | Clear the current game roster |
| `POST` | `/api/network/destination/change` | Change the UDP destination address |

## Database players

### List database players

```http
GET /api/database/players
```

```json
{
  "success": true,
  "data": [
    {
      "playerID": 1,
      "codename": "Alpha"
    }
  ]
}
```

### Get a database player

```http
GET /api/database/players/1
```

Successful response:

```json
{
  "success": true,
  "data": {
    "playerID": 1,
    "codename": "Alpha"
  }
}
```

Not found:

```json
{
  "success": false,
  "error": "Player with ID 1 not found."
}
```

### Create a database player

```http
POST /api/database/players/create
Content-Type: application/json
```

```json
{
  "codename": "Alpha"
}
```

The server assigns the next player ID.

```json
{
  "success": true,
  "data": {
    "playerID": 1,
    "codename": "Alpha"
  }
}
```

### Update a database player

```http
POST /api/database/players/1/update
Content-Type: application/json
```

```json
{
  "codename": "Bravo"
}
```

```json
{
  "success": true,
  "data": {
    "playerID": 1,
    "codename": "Bravo"
  }
}
```

If the player is currently in the game, their roster codename is updated too.

### Delete a database player

```http
POST /api/database/players/1/delete
```

```json
{
  "success": true,
  "message": "Player with ID 1 deleted."
}
```

Deleting a database player also removes that player from the current game.

## Game players

### List game players

```http
GET /api/game/players
```

```json
{
  "success": true,
  "data": [
    {
      "playerID": 1,
      "codename": "Alpha",
      "equipmentID": 8,
      "team": "red",
      "score": 0
    }
  ]
}
```

### Add a player to the game

The player must already exist in the database.

```http
POST /api/game/players/add
Content-Type: application/json
```

```json
{
  "playerID": 1,
  "equipmentID": 8,
  "team": "red"
}
```

| Field | Type | Description |
| --- | --- | --- |
| `playerID` | integer | Persistent database player ID |
| `equipmentID` | integer | Equipment assigned for this game |
| `team` | string | `red` or `green` |

The server rejects duplicate players, duplicate equipment assignments, and teams containing more than 15 players. After validation, it broadcasts the equipment ID through UDP port `7500`.

Successful response:

```json
{
  "success": true,
  "data": {
    "playerID": 1,
    "codename": "Alpha",
    "equipmentID": 8,
    "team": "red",
    "score": 0
  }
}
```

### Remove one game player

```http
POST /api/game/players/1/remove
```

This removes the player's equipment assignment and score but preserves the database record.

### Clear the game roster

```http
POST /api/game/players/clear
```

This clears all current-game players, equipment assignments, and scores. Database players are preserved.

## Change the network destination

```http
POST /api/network/destination/change
Content-Type: application/json
```

```json
{
  "ip": "192.168.1.255"
}
```

The server sends the network-change control message through the current destination before changing the transmitter destination.

## Frontend workflow

Look up the operator-entered player ID:

```javascript
const lookup = await fetch('/api/database/players/7');
const lookupResult = await lookup.json();
```

If the player is not found, prompt for a codename and create a persistent record:

```javascript
const createResponse = await fetch('/api/database/players/create', {
  method: 'POST',
  headers: {'Content-Type': 'application/json'},
  body: JSON.stringify({codename: 'Alpha'})
});

const createdPlayer = await createResponse.json();
```

Use the ID returned by the server when adding the player to the game:

```javascript
await fetch('/api/game/players/add', {
  method: 'POST',
  headers: {'Content-Type': 'application/json'},
  body: JSON.stringify({
    playerID: createdPlayer.data.playerID,
    equipmentID: 8,
    team: 'red'
  })
});
```

## Page routes

| Method | Path | Page |
| --- | --- | --- |
| `GET` | `/` | Player entry page |
| `GET` | `/game` | Game page |
