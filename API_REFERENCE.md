# Client–Server API Reference

This document describes the HTTP interface exposed by the Flask server for the frontend client.

## Base URL

For local development:

```text
http://127.0.0.1:8000
```

When the frontend is served by the same Flask application, relative URLs such as `/getPlayer` should be used.

## Conventions

- Request and response bodies use JSON unless an endpoint explicitly uses query parameters.
- JSON requests must include the `Content-Type: application/json` header.
- The frontend must inspect the response's `success` property to determine whether an operation succeeded. Application-level errors currently may still use HTTP status `200`.
- Player IDs are integers.
- Codenames are strings. Leading and trailing whitespace is removed by the server when a player is set.

## Endpoint summary

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/getPlayer` | Retrieve one player by ID |
| `GET` | `/getAllPlayers` | Retrieve every player |
| `POST` | `/setPlayer` | Create a player or update an existing player |
| `POST` | `/deletePlayer` | Delete a player by ID |

## Get one player

```http
GET /getPlayer?playerID=1
```

### Query parameters

| Name | Type | Required | Description |
| --- | --- | --- | --- |
| `playerID` | integer | Yes | ID of the player to retrieve |

### Successful response

```json
{
  "success": true,
  "data": {
    "playerID": 1,
    "codename": "Alpha"
  }
}
```

### Player not found

```json
{
  "success": false,
  "error": {
    "playerID": 999
  }
}
```

### Invalid or missing ID

```json
{
  "success": false,
  "error": "Invalid playerID"
}
```

## Get all players

```http
GET /getAllPlayers
```

### Successful response

```json
{
  "success": true,
  "data": [
    {
      "playerID": 1,
      "codename": "Alpha"
    },
    {
      "playerID": 2,
      "codename": "Bravo"
    }
  ]
}
```

If there are no players, `data` is an empty array:

```json
{
  "success": true,
  "data": []
}
```

## Create or update a player

```http
POST /setPlayer
Content-Type: application/json
```

### Request body

```json
{
  "playerID": -1,
  "codename": "Alpha"
}
```

| Field | Type | Required | Description |
| --- | --- | --- | --- |
| `playerID` | integer | Yes | Existing ID to update. Use `-1` when creating a new player. |
| `codename` | string | Yes | Nonblank player codename |

### Behavior

- If `playerID` matches an existing player, that player's codename is updated.
- If `playerID` does not match an existing player, a new player is created.
- The server assigns the new player's ID. It starts at `1` for an empty database; otherwise it uses the current highest ID plus one.
- The client should use the `playerID` returned by the server rather than assuming the submitted ID was used.

### Successful response

```json
{
  "success": true,
  "data": {
    "playerID": 1,
    "codename": "Alpha"
  }
}
```

### Validation errors

Invalid or missing player ID:

```json
{
  "success": false,
  "error": "Invalid playerID"
}
```

Missing or blank codename:

```json
{
  "success": false,
  "error": "Codename is required"
}
```

## Delete a player

```http
POST /deletePlayer
Content-Type: application/json
```

### Request body

```json
{
  "playerID": 1
}
```

| Field | Type | Required | Description |
| --- | --- | --- | --- |
| `playerID` | integer | Yes | ID of the player to delete |

### Successful response

```json
{
  "success": true,
  "message": "Player with ID 1 deleted."
}
```

### Player not found

```json
{
  "success": false,
  "error": "Player with ID 999 not found."
}
```

### Invalid or missing ID

```json
{
  "success": false,
  "error": "Invalid playerID"
}
```

## Frontend example

The following helper sends a JSON request and returns the parsed response:

```javascript
async function sendJson(path, body) {
  const response = await fetch(path, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify(body)
  });

  const result = await response.json();

  if (!result.success) {
    throw new Error(
      typeof result.error === 'string'
        ? result.error
        : JSON.stringify(result.error)
    );
  }

  return result;
}

const savedPlayer = await sendJson('/setPlayer', {
  playerID: -1,
  codename: 'Alpha'
});

await sendJson('/deletePlayer', {
  playerID: savedPlayer.data.playerID
});
```

Retrieving players:

```javascript
const response = await fetch('/getAllPlayers');
const result = await response.json();

if (result.success) {
  console.log(result.data);
}
```

## Page routes

These routes return HTML pages rather than API responses:

| Method | Path | Page |
| --- | --- | --- |
| `GET` | `/` | Player entry page |
| `GET` | `/game` | Game page |
