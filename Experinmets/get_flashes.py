import json
from pathlib import Path
from math import radians, sqrt, cos
import random

filename = Path("~/Projects/FBS/Data/TestData/fake_data.json").expanduser()

close_flashes = []

total_attempts = 0

def distance_km(lat1, lon1, lat2, lon2):
    lat_km = (lat2 - lat1) * 111
    lon_km = (lon2 - lon1) * 111 * cos(
        radians((lat1 + lat2) / 2)
    )

    return sqrt(lat_km**2 + lon_km**2)


with open(filename, "r") as f:
    data = json.load(f)


while True:

    total_attempts += 1

    outpost = {
        "lat": random.uniform(-40, 40),
        "lon": random.uniform(-90, 90)
    }

    close_flashes = []

    for flash in data:

        distance = distance_km(
            outpost["lat"],
            outpost["lon"],
            flash["lat"],
            flash["lon"]
        )

        if distance < 16:
            flash["distance"] = distance
            close_flashes.append(flash)

    if len(close_flashes) < 5:
        print("Not enough flashes found, generating new outpost location...")
        continue

    # Seřadíme podle času
    close_flashes.sort(key=lambda flash: flash["time"])

    # Začátek nahrávky = první blesk
    start_time = close_flashes[0]["time"]
    end_time = start_time + 1800

    recording_flashes = [
        flash
        for flash in close_flashes
        if flash["time"] <= end_time
    ]

    # Teprve TADY kontrolujeme počet
    if len(recording_flashes) >= 5:
        break

    print("Not enough flashes in 30-minute recording, generating new outpost location...")


# Seřadíme blesky podle času
close_flashes.sort(key=lambda flash: flash["time"])

# První nalezený blesk je začátek nahrávky
start_time = close_flashes[0]["time"]

# Nahrávka trvá maximálně 30 minut
end_time = start_time + 1800

recording_flashes = [
    flash
    for flash in close_flashes
    if flash["time"] <= end_time
]


print()
print(
    f"Outpost: "
    f"lat={outpost['lat']:.6f}, "
    f"lon={outpost['lon']:.6f}"
)

print(f"Flashes within 16 km: {len(close_flashes)}")
print(
    f"Recording: "
    f"{start_time:.2f}s → {end_time:.2f}s"
)
print(f"Flashes in recording: {len(recording_flashes)}")
print()

for flash in recording_flashes:
    print(
        f"time={flash['time']:.2f}s "
        f"lat={flash['lat']:.4f} "
        f"lon={flash['lon']:.4f} "
        f"distance={flash['distance']:.2f}km"
    )

print(total_attempts, "outpost locations were generated before finding a suitable one.")