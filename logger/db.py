import sqlite3
from pathlib import Path

from models import Flash

DB_PATH = Path(__file__).parent / "live_flashes.db"


def open_db(path=DB_PATH):
    """Opens (or creates) the append-only flash DB.

    Never wipes existing rows — the logger runs indefinitely across many
    restarts and each real strike is only ever observed once.
    """
    conn = sqlite3.connect(path)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS flashes (
            id INTEGER PRIMARY KEY,
            lat REAL NOT NULL,
            lon REAL NOT NULL,
            time REAL NOT NULL
        )
        """
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_flashes_lat_lon ON flashes (lat, lon)")
    conn.commit()
    return conn


def insert_flashes(conn, flashes):
    conn.executemany(
        "INSERT INTO flashes (lat, lon, time) VALUES (?, ?, ?)",
        ((f.lat, f.lon, f.time) for f in flashes),
    )
    conn.commit()


def load_all_flashes(conn):
    rows = conn.execute("SELECT lat, lon, time FROM flashes").fetchall()
    return [Flash(lat, lon, time) for lat, lon, time in rows]
