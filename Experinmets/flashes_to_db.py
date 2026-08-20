import random
import sqlite3 as sql
from pathlib import Path
from make_real_flashes import generate_all_flashes, storms


def generate_flashes_to_db():
    flashes = generate_all_flashes(storms, random.uniform(5, 20))

    conn = sql.connect(Path.home() / "Projects" / "FBS" / "Data"/ "TestData" / "lightning.db")

    cursor = conn.cursor()

    cursor.execute("DROP TABLE IF EXISTS flashes")  # Drop the table if it exists

    cursor.execute("""
        CREATE TABLE  flashes (
            id INTEGER PRIMARY KEY,
            lat REAL NOT NULL,
            lon REAL NOT NULL,
            time REAL NOT NULL
        )"""
    )

    cursor.executemany("""
        INSERT INTO flashes (lat, lon, time)
        VALUES (?, ?, ?)
        """,
        (
            (flash.lat, flash.lon, flash.time)
            for flash in flashes
        )
    )

    conn.commit()
    conn.close()

if __name__ == "__main__":
    generate_flashes_to_db()