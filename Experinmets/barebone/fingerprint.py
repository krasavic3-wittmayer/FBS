import numpy as np

from physics import MAX_DISTANCE_M, SPEED_OF_SOUND


def build_fingerprints(outpost, lat, lon, time, tree=None, max_distance_km=16, bins=200, window_s=1800,
                        min_flashes=1, burst_gap_s=3 * 3600):
    """Fingerprints for a candidate location, one per distinct time-burst.

    Real flash data spans years; a candidate location may have been hit by
    many unrelated storms at different times. Lumping all of a location's
    history into one fingerprint would blend unrelated storms together and
    make matching meaningless — the *time* the recording was made is just
    as unknown as the location, so every plausible burst near a candidate
    location has to be tried separately, not just the one location.

    Returns a list of (fingerprint, burst_start_time, burst_end_time).
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
        return []

    dist_m = dist_km[mask] * 1000
    event_time = time[mask]
    event_delay = np.sqrt(dist_m**2 + 2000.0**2) / SPEED_OF_SOUND
    event_amplitude = np.clip(1.0 - dist_m / MAX_DISTANCE_M, 0.0, None)
    arrival_time = event_time + event_delay

    order = np.argsort(event_time)
    event_time = event_time[order]
    arrival_time = arrival_time[order]
    event_amplitude = event_amplitude[order]

    # Split into bursts wherever consecutive (emission-time-sorted) events
    # are further apart than burst_gap_s — each gap marks a boundary
    # between unrelated storms passing through the same spot.
    if len(event_time) > 1:
        split_at = np.where(np.diff(event_time) > burst_gap_s)[0] + 1
    else:
        split_at = np.array([], dtype=np.int64)

    fingerprints = []
    start = 0
    for end in [*split_at, len(event_time)]:
        if end - start >= min_flashes:
            burst_start = event_time[start:end].min()
            # start_time is the earliest flash *emission* time in this
            # burst, not earliest arrival — those differ since delay varies
            # per flash by distance.
            fingerprint = bin_events(
                arrival_time[start:end], event_amplitude[start:end], bins, window_s, start_time=burst_start
            )
            fingerprints.append((fingerprint, burst_start, event_time[start:end].max()))
        start = end

    return fingerprints


def bin_events(arrival_time, amplitude, bins=200, window_s=1800, start_time=None):
    """Bins (arrival_time, amplitude) events into a fingerprint vector.

    Shared by the synthetic geometry-based path (arrival_time = flash emit
    time + simulated sound delay, start_time = earliest emit time) and real
    audio detection (arrival_time = the detected clap's timestamp, delay
    already physically baked in, start_time = earliest arrival — there's no
    separate emission time available).
    """
    if len(arrival_time) == 0:
        return None

    if start_time is None:
        start_time = arrival_time.min()
    relative = arrival_time - start_time
    bin_index = (relative / window_s * bins).astype(np.int64)

    valid = (bin_index >= 0) & (bin_index < bins)
    fingerprint = np.zeros(bins)
    np.add.at(fingerprint, bin_index[valid], amplitude[valid])

    return fingerprint


def similarity(a, b):
    if a is None or b is None or not np.any(a) or not np.any(b):
        return 0.0
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))
