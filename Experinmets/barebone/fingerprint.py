import numpy as np

from physics import MAX_DISTANCE_M, SPEED_OF_SOUND


def build_fingerprint(outpost, lat, lon, time, tree=None, max_distance_km=16, bins=200, window_s=1800, min_flashes=1):
    """Vectorized over the nearby flash subset — same math as the original
    per-row distance_km/delay/amplitude loop, just batched with numpy
    instead of calling those functions once per flash.
    """
    if tree is not None:
        # KD-tree prefilter: only touches flashes near this candidate,
        # instead of scanning the whole (global) flash array every call.
        query_radius_deg = max_distance_km / 111 * 1.5
        idx = np.asarray(tree.query_ball_point((outpost.lat, outpost.lon), r=query_radius_deg), dtype=np.int64)
        lat, lon, time = lat[idx], lon[idx], time[idx]
    else:
        # Plain bounding-box prefilter (plain array compares) before the
        # trig-heavy exact distance calc, to shrink the array early.
        box_deg = max_distance_km / 111 * 1.5
        box_mask = (np.abs(lat - outpost.lat) <= box_deg) & (np.abs(lon - outpost.lon) <= box_deg)
        lat, lon, time = lat[box_mask], lon[box_mask], time[box_mask]

    lat_km = (lat - outpost.lat) * 111
    mean_lat = (outpost.lat + lat) / 2
    lon_km = (lon - outpost.lon) * 111 * np.cos(np.radians(mean_lat))
    dist_km = np.sqrt(lat_km**2 + lon_km**2)

    mask = dist_km <= max_distance_km
    if mask.sum() < min_flashes:
        return None

    dist_m = dist_km[mask] * 1000
    event_time = time[mask]
    event_delay = np.sqrt(dist_m**2 + 2000.0**2) / SPEED_OF_SOUND
    event_amplitude = np.clip(1.0 - dist_m / MAX_DISTANCE_M, 0.0, None)

    start_time = event_time.min()
    arrival = event_time + event_delay - start_time
    bin_index = (arrival / window_s * bins).astype(np.int64)

    valid = (bin_index >= 0) & (bin_index < bins)
    fingerprint = np.zeros(bins)
    np.add.at(fingerprint, bin_index[valid], event_amplitude[valid])

    return fingerprint


def similarity(a, b):
    if a is None or b is None or not np.any(a) or not np.any(b):
        return 0.0
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))
