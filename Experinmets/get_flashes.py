import sqlite3

from config import DB_PATH
from distance import distance_km
from models import Outpost


def get_flashes(outpost: Outpost) -> list[dict]:

    with sqlite3.connect(DB_PATH) as conn:

        # SQL query na prostor kolem outpostu
        ...

        flashes = []

        for flash in rows:

            distance = distance_km(
                outpost.lat,
                outpost.lon,
                flash["lat"],
                flash["lon"],
            )

            if distance < 16:
                flash["distance"] = distance
                flashes.append(flash)

        if len(flashes) < 5:
            return []

        flashes.sort(key=lambda flash: flash["time"])

        start_time = flashes[0]["time"]
        end_time = start_time + 1800

        return [
            flash
            for flash in flashes
            if flash["time"] <= end_time
        ]