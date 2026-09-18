import psycopg

DEFAULT_CONNINFO = "host=127.0.0.1 port=5432 dbname=photon user=student"

class Player:
    def __init__(self, id, codename):
        self.id = id
        self.codename = codename

    def __repr__(self):
        return f"Player(id={self.id!r}, codename={self.codename!r})"

class PlayerDatabase:
    """Read/write access to the players table, returning Player objects."""

    def __init__(self, conninfo=None):
        self.conninfo = conninfo or DEFAULT_CONNINFO

    def _connect(self):
        return psycopg.connect(self.conninfo)

    def getAll(self):
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute("SELECT id, codename FROM players")
            return [Player(*row) for row in cur.fetchall()]

    def getById(self, id: int):
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute("SELECT id, codename FROM players WHERE id = %s", (id,))
            row = cur.fetchone()
            if row is None:
                return None
            return Player(*row)

    def insert(self, player: Player):
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(
                "INSERT INTO players (id, codename) VALUES (%s, %s)",
                (player.id, player.codename),
            )
            conn.commit()

    def update(self, player: Player):
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(
                "UPDATE players SET codename = %s WHERE id = %s",
                (player.codename, player.id),
            )
            updated = cur.rowcount
            conn.commit()
            return updated

    def delete(self, id: int):
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute("DELETE FROM players WHERE id = %s", (id,))
            deleted = cur.rowcount
            conn.commit()
            return deleted
