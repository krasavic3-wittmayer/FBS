import numpy as np
from numba import njit

from physics import MAX_DISTANCE_M, SPEED_OF_SOUND


@njit(cache=True)
def _score_burst_windows(arrival_sorted, amplitude_sorted, recorded_fingerprint, recorded_norm, duration_s, bins, min_flashes):
    """Best-scoring window start within one burst, JIT-compiled.

    Plain nested loops instead of a vectorized numpy batch — the numpy
    version (repeat/cumsum/bincount/norm, one round of small array ops per
    burst) paid real Python-level call overhead across the ~54k bursts a
    coarse-search pass touches; a batched-tensor rewrite to avoid that
    overhead hit a different wall (O(anchors * burst_size^2) memory blew
    up on dense storms). A compiled loop avoids both: no per-call numpy
    dispatch overhead (it's one compiled function call per burst) and no
    large intermediate arrays (the inner loop breaks as soon as it walks
    past duration_s, so cost is O(events actually in each window), same
    early-exit the searchsorted version relied on).

    Returns (best_score, best_start_index); best_start_index is -1 if no
    window had at least min_flashes events.
    """
    n = arrival_sorted.shape[0]
    best_score = -1.0
    best_start_index = -1
    fingerprint = np.zeros(bins)

    for i in range(n):
        for b in range(bins):
            fingerprint[b] = 0.0

        start_t = arrival_sorted[i]
        count = 0
        j = i
        while j < n and (arrival_sorted[j] - start_t) < duration_s:
            bin_index = int((arrival_sorted[j] - start_t) / duration_s * bins)
            if bin_index >= bins:
                bin_index = bins - 1
            fingerprint[bin_index] += amplitude_sorted[j]
            count += 1
            j += 1

        if count < min_flashes:
            continue

        norm_sq = 0.0
        dot = 0.0
        for b in range(bins):
            norm_sq += fingerprint[b] * fingerprint[b]
            dot += fingerprint[b] * recorded_fingerprint[b]
        norm = np.sqrt(norm_sq)
        if norm == 0.0:
            continue

        score = dot / (norm * recorded_norm)
        if score > best_score:
            best_score = score
            best_start_index = i

    return best_score, best_start_index


def nearby_bursts(outpost, lat, lon, time, tree=None, idx=None, max_distance_km=16, min_flashes=1, burst_gap_s=3 * 3600):
    """Raw (unbinned) nearby-flash events for a candidate location, split
    into distinct time-bursts.

    Real flash data spans years; a candidate location may have been hit by
    many unrelated storms at different times. Lumping all of a location's
    history together would blend unrelated storms into one signal and make
    matching meaningless — the *time* a recording was made is just as
    unknown as its location, so every plausible burst near a candidate has
    to be considered separately.

    idx: precomputed KD-tree neighbor indices for this outpost, if the
    caller already batch-queried the tree for many outposts at once (a
    single query_ball_point call per outpost is expensive at scale — tens
    of thousands of coarse-search candidates each paying Python call
    overhead). Skips the tree query below when given.

    Returns a list of (emission_time, arrival_time, amplitude, burst_start, burst_end),
    each already sorted by emission_time within the burst.
    """
    if idx is not None:
        lat, lon, time = lat[idx], lon[idx], time[idx]
    elif tree is not None:
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

    bursts = []
    start = 0
    for end in [*split_at, len(event_time)]:
        if end - start >= min_flashes:
            bursts.append((
                event_time[start:end],
                arrival_time[start:end],
                event_amplitude[start:end],
                event_time[start:end].min(),
                event_time[start:end].max(),
            ))
        start = end

    return bursts


# Comfortably above the longest possible single storm in generate.py
# (duration is random.uniform(30, 150) minutes = up to 9000s) — every
# candidate's whole-burst fingerprint must use the SAME window_s, or bin
# width (and therefore comparability) varies with each burst's own length.
MAX_BURST_WINDOW_S = 9500


def build_fingerprints(outpost, lat, lon, time, tree=None, idx=None, max_distance_km=16, bins=200, window_s=MAX_BURST_WINDOW_S,
                        min_flashes=1, burst_gap_s=3 * 3600):
    """Whole-burst fingerprints for a candidate location, one per distinct
    time-burst — the entire burst is treated as one recording.

    Only correct when the actual recording covers a whole burst (the
    synthetic random-outpost path, which has no separate concept of a
    short recording window). A real recording is normally a short slice of
    a longer storm — use sliding_fingerprints for that case instead, or
    this will compare a short slice against a fingerprint built from the
    whole (much longer) burst and never align.

    window_s must be fixed and the same across every candidate — using
    each burst's own span would give different candidates different bin
    widths, making their fingerprints incomparable by cosine similarity.

    Returns a list of (fingerprint, burst_start_time, burst_end_time) —
    burst_start/end are the burst's emission-time span, for identifying
    *which* burst this is; the fingerprint itself is arrival-time anchored.
    """
    fingerprints = []
    for _, arrival_time, amplitude, burst_start, burst_end in nearby_bursts(
        outpost, lat, lon, time, tree=tree, idx=idx, max_distance_km=max_distance_km, min_flashes=min_flashes, burst_gap_s=burst_gap_s
    ):
        fingerprint = bin_events(arrival_time, amplitude, bins, window_s=window_s)
        fingerprints.append((fingerprint, burst_start, burst_end))

    return fingerprints


def sliding_fingerprints(outpost, lat, lon, time, duration_s, tree=None, max_distance_km=16, bins=200,
                          min_flashes=1, burst_gap_s=3 * 3600):
    """Fingerprints for every duration_s-long window that could be "this
    recording" within a candidate location's bursts.

    A short recording is normally just a slice of a longer storm, so its
    own first captured event's arrival time relative to the burst's start
    is unknown — comparing it against a fingerprint of the *whole* burst
    (build_fingerprints) would almost never align. Instead, try starting
    the window at each of the burst's own event arrival times (the
    recording's first event must be one of the real events, so this covers
    every plausible alignment without guessing a slide step).

    Returns a list of (fingerprint, candidate_window_start, candidate_window_end),
    all in arrival-time terms. These are the solver's own *guesses* at where
    the recording might sit within this burst — not ground truth (the
    solver never sees or receives the recording's true start time; a
    candidate here is just one of many hypotheses being scored).
    """
    results = []
    for _, arrival_time, amplitude, _, _ in nearby_bursts(
        outpost, lat, lon, time, tree=tree, max_distance_km=max_distance_km, min_flashes=min_flashes, burst_gap_s=burst_gap_s
    ):
        order = np.argsort(arrival_time)
        arrival_sorted = arrival_time[order]
        amplitude_sorted = amplitude[order]

        # arrival_sorted is sorted, so for each candidate window start the
        # window's end index is a binary search away — avoids an O(n^2)
        # rescan of the burst for every candidate start.
        end_idx = np.searchsorted(arrival_sorted, arrival_sorted + duration_s, side="left")

        for i, j in enumerate(end_idx):
            if j - i < min_flashes:
                continue
            candidate_window_start = arrival_sorted[i]
            fingerprint = bin_events(arrival_sorted[i:j], amplitude_sorted[i:j], bins, window_s=duration_s)
            results.append((fingerprint, candidate_window_start, candidate_window_start + duration_s))

    return results


def best_sliding_match(outpost, lat, lon, time, recorded_fingerprint, duration_s, tree=None, idx=None, max_distance_km=16,
                        bins=200, min_flashes=1, burst_gap_s=3 * 3600):
    """Best-scoring within-burst window for one candidate, scored against
    recorded_fingerprint. The actual per-window search is JIT-compiled
    (_score_burst_windows) — see its docstring for why.

    idx: precomputed KD-tree neighbor indices for this outpost — see
    nearby_bursts. Lets a caller scoring many outposts batch the tree query
    once instead of paying Python call overhead per outpost.

    recorded_fingerprint is the only information this function has about
    the actual recording — built entirely from detected/synthetic events
    upstream of this call. Nothing here ever receives the recording's true
    time or location; every window_start below is a hypothesis generated
    from the known flash database (arrival_sorted), scored against that
    fingerprint, and returned only if it won.

    Returns (best_score, matched_window_start, matched_window_end).
    """
    best_score = -1.0
    best_window = (None, None)

    recorded_norm = np.linalg.norm(recorded_fingerprint) if recorded_fingerprint is not None else 0.0
    if recorded_norm == 0.0:
        return best_score, best_window

    for _, arrival_time, amplitude, _, _ in nearby_bursts(
        outpost, lat, lon, time, tree=tree, idx=idx, max_distance_km=max_distance_km,
        min_flashes=min_flashes, burst_gap_s=burst_gap_s
    ):
        order = np.argsort(arrival_time)
        arrival_sorted = arrival_time[order]
        amplitude_sorted = amplitude[order]

        score, start_index = _score_burst_windows(
            arrival_sorted, amplitude_sorted, recorded_fingerprint, recorded_norm, duration_s, bins, min_flashes
        )
        if start_index >= 0 and score > best_score:
            best_score = float(score)
            matched_window_start = float(arrival_sorted[start_index])
            best_window = (matched_window_start, matched_window_start + duration_s)

    return best_score, best_window


def bin_events(arrival_time, amplitude, bins=200, window_s=1800):
    """Bins (arrival_time, amplitude) events into a fingerprint vector,
    relative to the earliest arrival.

    Shared by the synthetic geometry-based path (arrival_time = flash emit
    time + simulated sound delay) and real audio detection (arrival_time =
    the detected clap's timestamp, delay already physically baked in). Both
    must anchor to earliest *arrival*, not earliest emission — a real
    recording never observes emission time, so the known-database side has
    to match that to stay comparable.
    """
    if len(arrival_time) == 0:
        return None

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
