import random
from math import cos, radians, sin, sqrt

from models import Flash, Storm


def make_storm(current_time):
    lat = random.uniform(-20, 20)
    lon = random.uniform(-50, 50)
    intensity = random.uniform(0.5, 1.0)
    duration = random.uniform(30, 150)  # minutes
    return Storm(lat, lon, intensity, duration, current_time + duration)


def generate_storms(total_minutes, storm_count):
    time = 0.0
    active = [make_storm(time) for _ in range(storm_count)]
    all_storms = list(active)

    while time < total_minutes:
        time += min(storm.end_time - time for storm in active)

        if time > total_minutes:
            break

        finished = [storm for storm in active if storm.end_time <= time]

        for storm in finished:
            active.remove(storm)
            new_storm = make_storm(time)
            active.append(new_storm)
            all_storms.append(new_storm)

    return all_storms


def make_flash(storm, storm_radius_km):
    distance = storm_radius_km * sqrt(random.random())
    angle = random.uniform(0, 2 * 3.14159)

    dlat = distance * cos(angle) / 111.32
    dlon = distance * sin(angle) / (111.32 * cos(radians(storm.lat)))

    storm_start = storm.end_time - storm.duration
    time_minutes = random.uniform(storm_start, storm.end_time)

    # Flash.time is stored in seconds — calc_delay/amplitude work in
    # meters/seconds, so minutes here would misalign the fingerprint.
    return Flash(storm.lat + dlat, storm.lon + dlon, time_minutes * 60)


def generate_flashes(storms, storm_radius_km):
    flashes = []
    for storm in storms:
        count = int(storm.intensity * 10 * storm.duration)
        flashes.extend(make_flash(storm, storm_radius_km) for _ in range(count))
    return flashes
