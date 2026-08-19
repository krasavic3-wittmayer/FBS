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

    active_storms = [Storm.make_storm() for _ in range(storm_count)]
    all_storms = active_storms.copy()

    while time < t:
        nearest_end_storm = min(
            storm.end_time - time
            for storm in active_storms
        )

        time += nearest_end_storm

        if time > t:
            break

        finished = [
            storm for storm in active_storms
            if storm.end_time <= time
        ]

        for storm in finished:
            active_storms.remove(storm)

        for _ in finished:
            new_storm = Storm.make_storm()
            active_storms.append(new_storm)
            all_storms.append(new_storm)

    return all_storms
#
#storms = generate_storms(24 * 60, 10)  # 24 hours in minutes
#
#for storm in storms:
#    print(storm.__repr__())
#
#print(f"Total storms generated: {len(storms)}")
#
#total_storms = 0
#
#for i in range(1000):
#    time = 0
#    storms_test = generate_storms(24 * 60, 10)
#    total_storms += len(storms_test)
#
#
#print(f"Average storms generated over 1000 iterations: {total_storms / 1000}")