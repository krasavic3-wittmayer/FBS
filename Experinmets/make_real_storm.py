import random

time = 0

class Storm:
    def __init__(self, lat, lon, intensity, duration, end_time):
        self.lat = lat
        self.lon = lon
        self.intensity = intensity
        self.duration = duration
        self.end_time = end_time
        

    @classmethod
    def make_storm(cls):
        global time
        lat = random.uniform(-20, 20)
        lon = random.uniform(-50, 50)
        intensity = random.uniform(0.5, 1.0)
        duration = random.uniform(30, 150)  # Duration in minutes
        end_time = time + duration
        return cls(lat, lon, intensity, duration, end_time)

    def __repr__(self):
        return f"Storm(lat={self.lat:.2f}, lon={self.lon:.2f}, intensity={self.intensity:.2f}, duration={self.duration:.1f}, end_time={self.end_time:.1f})"

#storms = [Storm.make_storm() for _ in range(10)]

def generate_storms(t, storm_count):
    global time
    time_of_storms = t
    storms = [Storm.make_storm() for _ in range(storm_count)]

    while time < t:
        end_times = [storm.end_time for storm in storms]
        nearest_end_storm = min(end_times)


    return storms

storms = generate_storms(24 * 60, 10)  # 24 hours in minutes

for storm in storms:
    print(storm.__repr__())