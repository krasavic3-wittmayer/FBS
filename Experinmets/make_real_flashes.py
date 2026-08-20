from make_real_storm import Storm, generate_storms
import random
from math import sqrt, sin, cos, radians

#random.seed(42)  # For reproducible results

class Flash:
    def __init__(self, lat, lon, time):
        self.lat = lat
        self.lon = lon
        self.time = time

    @classmethod
    def make_flash(cls, storm, storm_radius):
        distance = storm_radius * sqrt(random.random())
        angle = random.uniform(0, 2 * 3.14159)

        dlat = distance * cos(angle) / 111.32
        dlon = distance * sin(angle) / (111.32 * cos(radians(storm.lat)))

        lat = storm.lat + dlat
        lon = storm.lon + dlon

        storm_start_time = storm.end_time - storm.duration
        time = random.uniform(storm_start_time, storm.end_time)

        return cls(lat, lon, time)

    def __repr__(self):
        return f"Flash(lat={self.lat:.2f}, lon={self.lon:.2f}, time={self.time:.1f})"
    
storms = generate_storms(24 * 60, 5)  # Generate storms for 24 hours with 5 initial storms

def generate_storm_flashes(storm, storm_radius):
    flash_count = int(storm.intensity * 10 * storm.duration)  # Number of flashes based on intensity and duration
    flashes = [Flash.make_flash(storm, storm_radius) for _ in range(flash_count)]
    return flashes

def generate_all_flashes(storms, storm_radius):
    all_flashes = []
    for storm in storms:
        flashes = generate_storm_flashes(storm, storm_radius)
        all_flashes.extend(flashes)
    return all_flashes

#print(len(generate_storm_flashes(Storm.make_storm(), random.uniform(5, 20))))
print(len(generate_all_flashes(storms, random.uniform(5, 20))))
