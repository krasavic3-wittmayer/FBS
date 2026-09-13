import numpy as np

from physics import amplitude, delay, distance_km


def build_fingerprint(outpost, rows, max_distance_km=16, bins=200, window_s=1800, min_flashes=1):
    events = []

    for lat, lon, time in rows:
        dist_km = distance_km(outpost.lat, outpost.lon, lat, lon)
        if dist_km > max_distance_km:
            continue
        dist_m = dist_km * 1000
        events.append((time, delay(dist_m), amplitude(dist_m)))

    if len(events) < min_flashes:
        return None

    start_time = min(time for time, _, _ in events)
    fingerprint = np.zeros(bins)

    for time, event_delay, event_amplitude in events:
        arrival = time + event_delay - start_time
        bin_index = int(arrival / window_s * bins)
        if 0 <= bin_index < bins:
            fingerprint[bin_index] += event_amplitude

    return fingerprint


def similarity(a, b):
    if a is None or b is None or not np.any(a) or not np.any(b):
        return 0.0
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))
