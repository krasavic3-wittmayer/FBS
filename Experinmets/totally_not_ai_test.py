import random
import sqlite3
import time
from math import cos, radians, floor


DB_UNORGANIZED = "/home/michal/Projects/FBS/Data/TestData/lightning.db"
DB_ORGANIZED = "/home/michal/Projects/FBS/Data/TestData/lightning_grid.db"

CELL_SIZE_KM = 20
TIME_CELL_SECONDS = 50

RADIUS_KM = 10
TIME_WINDOW = 50

KM_PER_DEGREE = 111

SAMPLES = 1000


def get_bounds(lat, lon, timestamp):
    lat_delta = RADIUS_KM / KM_PER_DEGREE

    lon_delta = RADIUS_KM / (
        KM_PER_DEGREE * cos(radians(lat))
    )

    return (
        lat - lat_delta,
        lat + lat_delta,
        lon - lon_delta,
        lon + lon_delta,
        timestamp,
        timestamp + TIME_WINDOW,
    )


def brute_force(conn, lat, lon, timestamp):
    (
        min_lat,
        max_lat,
        min_lon,
        max_lon,
        min_time,
        max_time,
    ) = get_bounds(lat, lon, timestamp)

    return conn.execute("""
        SELECT id
        FROM flashes
        WHERE lat BETWEEN ? AND ?
          AND lon BETWEEN ? AND ?
          AND time BETWEEN ? AND ?
    """, (
        min_lat,
        max_lat,
        min_lon,
        max_lon,
        min_time,
        max_time,
    )).fetchall()


def organized(conn, lat, lon, timestamp):
    (
        min_lat,
        max_lat,
        min_lon,
        max_lon,
        min_time,
        max_time,
    ) = get_bounds(lat, lon, timestamp)

    # Find every grid cell touched by the bounding box.
    min_lat_cell = floor(
        min_lat * KM_PER_DEGREE / CELL_SIZE_KM
    )
    max_lat_cell = floor(
        max_lat * KM_PER_DEGREE / CELL_SIZE_KM
    )

    # Longitude cell size depends on latitude.
    min_lon_cell = floor(
        min_lon * KM_PER_DEGREE / CELL_SIZE_KM
    )

    max_lon_cell = floor(
        max_lon * KM_PER_DEGREE / CELL_SIZE_KM
    )

    min_time_cell = floor(
        min_time / TIME_CELL_SECONDS
    )
    max_time_cell = floor(
        max_time / TIME_CELL_SECONDS
    )

    return conn.execute("""
        SELECT id
        FROM flashes
        WHERE lat_cell BETWEEN ? AND ?
          AND lon_cell BETWEEN ? AND ?
          AND time_cell BETWEEN ? AND ?

          AND lat BETWEEN ? AND ?
          AND lon BETWEEN ? AND ?
          AND time BETWEEN ? AND ?
    """, (
        min_lat_cell,
        max_lat_cell,
        min_lon_cell,
        max_lon_cell,
        min_time_cell,
        max_time_cell,

        min_lat,
        max_lat,
        min_lon,
        max_lon,
        min_time,
        max_time,
    )).fetchall()


def main():
    unorganized_db  = sqlite3.connect(DB_UNORGANIZED)
    organized_db = sqlite3.connect(DB_ORGANIZED)

    flashes = organized_db.execute("""
        SELECT id, lat, lon, time
        FROM flashes
    """).fetchall()

    samples = random.sample(
        flashes,
        min(SAMPLES, len(flashes)),
    )

    print(f"Database size: {len(flashes):,} flashes")
    print(f"Testing:       {len(samples):,} queries")
    print()

    brute_times = []
    organized_times = []

    total_results = 0

    for index, (_, lat, lon, timestamp) in enumerate(samples, 1):

        # -------------------------
        # UNORGANIZED
        # -------------------------

        start = time.perf_counter()

        brute_result = brute_force(
            unorganized_db,
            lat,
            lon,
            timestamp,
        )

        brute_times.append(
            time.perf_counter() - start
        )

        # -------------------------
        # ORGANIZED
        # -------------------------

        start = time.perf_counter()

        organized_result = organized(
            organized_db,
            lat,
            lon,
            timestamp,
        )

        organized_times.append(
            time.perf_counter() - start
        )

        brute_ids = {
            row[0]
            for row in brute_result
        }

        organized_ids = {
            row[0]
            for row in organized_result
        }

        # -------------------------
        # CORRECTNESS
        # -------------------------

        if brute_ids != organized_ids:
            print()
            print("❌ CORRECTNESS FAILURE")
            print(f"Query: {index}")
            print(f"Brute force: {len(brute_ids)}")
            print(f"Organized:   {len(organized_ids)}")

            missing = brute_ids - organized_ids
            extra = organized_ids - brute_ids

            print(f"Missing: {len(missing)}")
            print(f"Extra:   {len(extra)}")

            print("Missing IDs:", list(missing)[:20])
            print("Extra IDs:", list(extra)[:20])

            return

        total_results += len(brute_ids)

    # -------------------------
    # RESULTS
    # -------------------------

    brute_total = sum(brute_times)
    organized_total = sum(organized_times)

    brute_avg = brute_total / len(samples)
    organized_avg = organized_total / len(samples)

    speedup = brute_total / organized_total

    print("✅ CORRECTNESS: PASS")
    print()

    print(f"Total matching flashes: {total_results:,}")
    print()

    print("UNORGANIZED")
    print(f"  Total:   {brute_total:.4f} s")
    print(f"  Average: {brute_avg * 1000:.4f} ms/query")

    print()

    print("ORGANIZED")
    print(f"  Total:   {organized_total:.4f} s")
    print(f"  Average: {organized_avg * 1000:.4f} ms/query")

    print()

    print(f"Speedup: {speedup:.2f}×")

    unorganized_db.close()
    organized_db.close()


if __name__ == "__main__":
    main()