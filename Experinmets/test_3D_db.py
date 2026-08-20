import sqlite3
import time
from pathlib import Path
from math import cos, radians, floor


INPUT_DB = Path("/home/michal/Projects/FBS/Data/TestData/lightning.db")
OUTPUT_DB = Path("/home/michal/Projects/FBS/Data/TestData/lightning_grid.db")

CELL_SIZE_KM = 20
TIME_CELL_SECONDS = 50

KM_PER_DEGREE = 111


def lat_cell(lat):
    return floor(lat * KM_PER_DEGREE / CELL_SIZE_KM)


def lon_cell(lon):
    return floor(
        lon * KM_PER_DEGREE / CELL_SIZE_KM
    )


def time_cell(timestamp):
    return floor(timestamp / TIME_CELL_SECONDS)


def main():
    start = time.perf_counter()

    if OUTPUT_DB.exists():
        OUTPUT_DB.unlink()

    source = sqlite3.connect(INPUT_DB)
    target = sqlite3.connect(OUTPUT_DB)

    target.execute("""
        CREATE TABLE flashes (
            id INTEGER PRIMARY KEY,
            lat REAL NOT NULL,
            lon REAL NOT NULL,
            time REAL NOT NULL,
            lat_cell INTEGER NOT NULL,
            lon_cell INTEGER NOT NULL,
            time_cell INTEGER NOT NULL
        )
    """)

    rows = source.execute("""
        SELECT id, lat, lon, time
        FROM flashes
    """)

    batch = []
    processed = 0

    for flash_id, lat, lon, timestamp in rows:
        batch.append((
            flash_id,
            lat,
            lon,
            timestamp,+
            lat_cell(lat),
            lon_cell(lon),
            time_cell(timestamp),
        ))

        if len(batch) >= 10_000:
            target.executemany("""
                INSERT INTO flashes
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, batch)

            target.commit()

            processed += len(batch)
            batch.clear()

    if batch:
        target.executemany("""
            INSERT INTO flashes
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, batch)

        target.commit()
        processed += len(batch)

    target.execute("""
        CREATE INDEX idx_flashes_3d
        ON flashes (lat_cell, lon_cell, time_cell)
    """)

    target.commit()

    source.close()
    target.close()

    elapsed = time.perf_counter() - start

    print(f"Processed: {processed:,} flashes")
    print(f"Time:      {elapsed:.3f} s")
    print(f"Speed:     {processed / elapsed:,.0f} flashes/s")
    print(f"Output:    {OUTPUT_DB}")


if __name__ == "__main__":
    main()