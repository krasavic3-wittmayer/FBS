import sqlite3
from pathlib import Path

import numpy as np

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


def flash_arrays(flashes):
    """lat/lon/time as numpy arrays, for vectorized fingerprint building.

    Loaded once and reused across every candidate the solver tries, instead
    of round-tripping through SQLite per candidate.
    """
    lat = np.fromiter((f.lat for f in flashes), dtype=np.float64, count=len(flashes))
    lon = np.fromiter((f.lon for f in flashes), dtype=np.float64, count=len(flashes))
    time = np.fromiter((f.time for f in flashes), dtype=np.float64, count=len(flashes))
    return lat, lon, time


def build_index(lat, lon):
    """KD-tree over flash coordinates, so a candidate's nearby-flash lookup
    touches only nearby flashes instead of scanning the whole (global)
    flash array on every call.
    """
    from scipy.spatial import cKDTree

    return cKDTree(np.column_stack((lat, lon)))
