import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "flashes.db"


def create_db(flashes, path=DB_PATH):
    if path.exists():
        path.unlink()

    conn = sqlite3.connect(path)
    conn.execute(
        """
        CREATE TABLE flashes (
            id INTEGER PRIMARY KEY,
            lat REAL NOT NULL,
            lon REAL NOT NULL,
            time REAL NOT NULL
        )
        """
    )
    conn.executemany(
        "INSERT INTO flashes (lat, lon, time) VALUES (?, ?, ?)",
        ((f.lat, f.lon, f.time) for f in flashes),
    )
    conn.execute("CREATE INDEX idx_flashes_lat_lon ON flashes (lat, lon)")
    conn.commit()
    return conn


def query_nearby(conn, outpost, box_deg=0.3):
    """Bounding-box prefilter in SQL; exact radius filter stays in Python."""
    return conn.execute(
        """
        SELECT lat, lon, time FROM flashes
        WHERE lat BETWEEN ? AND ?
          AND lon BETWEEN ? AND ?
        """,
        (
            outpost.lat - box_deg,
            outpost.lat + box_deg,
            outpost.lon - box_deg,
            outpost.lon + box_deg,
        ),
    ).fetchall()
