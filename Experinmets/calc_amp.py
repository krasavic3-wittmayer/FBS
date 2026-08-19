import numpy as np
import matplotlib.pyplot as plt

from wav_fingerprint import wav_to_fingerprint
from calc_delay import delay


#flash = wav_to_fingerprint("./Experinmets/flash.wav")

## Nejvyšší peak = 1
#flash = flash / np.max(flash)
#
MAX_DISTANCE = 16_000


def amplitude(distance):
    return max(0.0, 1.0 - distance / MAX_DISTANCE)


#def generate_fingerprint(distances, gap=0):
#    silence = np.zeros(
#        gap * len(flash),
#        dtype=np.float32
#    )
#
#    # Spočítáme čas, kdy každý hrom dorazí
#    events = []
#
#    for distance in distances:
#        events.append({
#            "distance": distance,
#            "delay": delay(distance),
#            "amplitude": amplitude(distance)
#        })
#
#    # Nejbližší arrival time první
#    events.sort(key=lambda event: event["delay"])
#
#    parts = []
#
#    for event in events:
#        parts.append(
#            flash * event["amplitude"]
#        )
#        parts.append(silence)
#
#    return np.concatenate(parts), events
#
#
#distances = [
#    2_000,
#    5_000,
#    8_000,
#    12_000,
#    15_000,
#    13_000,
#    10_000,
#    6_000,
#    3_000,
#    1_000
#]
#
#fingerprint, events = generate_fingerprint(distances)
#
#print("flash length:", len(flash))
#print("total length:", len(fingerprint))
#
#print("\nArrival order:")
#
#for event in events:
#    print(
#        f"{event['distance']:>5} m | "
#        f"{event['delay']:6.2f} s | "
#        f"amplitude {event['amplitude']:.3f}"
#    )
#
#
#plt.plot(fingerprint)
#plt.xlabel("Fingerprint sample")
#plt.ylabel("Amplitude")
#plt.title("Synthetic lightning fingerprint")
#plt.show()