import json
import random
from pathlib import Path

filename = Path("~/Projects/FBS/Data/TestData/fake_data_more.json").expanduser()

secs_in_day = 24 * 60 * 60

def generate_fake_data():
    data = []
    for time in range(secs_in_day * 100):
        entry = {
            "lat": random.uniform(-20, 20),
            "lon": random.uniform(-50, 50),
            "time": time / 100 # 100 flashes per second
        }
        data.append(entry)
    return data

data = generate_fake_data()

filename.parent.mkdir(parents=True, exist_ok=True)

with open(filename, "w") as f:
    json.dump(data, f)
