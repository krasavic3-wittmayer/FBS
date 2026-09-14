"""Estimates an outpost's location AND recording time from a recorded
fingerprint alone.

Never receives the true outpost coordinates or true time — only the
recorded fingerprint and the flash arrays, same as a real localization
task. Real flash data spans years, so a candidate location on its own
isn't enough: many unrelated storms may have passed through the same spot
at different times, so every plausible time-burst near a candidate has to
be tried too, not just the one location.
"""

import numpy as np

from fingerprint import best_sliding_match, build_fingerprints, similarity
from models import Outpost


def estimate_outpost(lat, lon, time, tree, recorded_fingerprint, duration_s=None, refine_step=0.02, refine_radius=0.3, coarse_k=20, coarse_grid_deg=0.01, debug_fn=None):
    """duration_s: the recording's actual length, if it's a short slice of
    a longer storm (real audio). None means the recorded_fingerprint covers
    a whole burst (the synthetic random-outpost path) — with a duration_s,
    every plausible within-burst window is tried instead of just the whole
    burst, since a short recording's offset into its storm is unknown.
    """
    # Coarse pass: probe near actual flash clusters, since the true outpost
    # must sit within range of real activity.
    #
    # similarity() decays sharply within ~1-3km of the true point (checked
    # empirically) and sits at a noise floor beyond that — a coarser grid
    # (0.02-0.1deg, ~2-11km) never actually samples the peak, so the true
    # location's score there is indistinguishable from (or worse than) a
    # spurious match elsewhere; widening top-k at that resolution doesn't
    # help since the true anchor may rank in the hundreds, not the top-k.
    # coarse_grid_deg must be fine enough to land inside the peak.
    anchors = _coarse_anchors(lat, lon, coarse_grid_deg)
    coarse_top = _top_k(lat, lon, time, tree, recorded_fingerprint, anchors, coarse_k, min_separation_deg=2 * refine_radius, duration_s=duration_s)
    if debug_fn:
        debug_fn(
            f"estimate_outpost: coarse anchors={len(anchors)} top_k={coarse_k} "
            + ", ".join(f"({o.lat:.4f},{o.lon:.4f})={s:.6f}" for o, _, s in coarse_top)
        )

    # Fine pass: local grid search around each retained coarse candidate,
    # keeping the best result across all of them.
    fine_best, fine_burst, fine_score = None, (None, None), -1.0
    for coarse_outpost, _, _ in coarse_top:
        fine_candidates = _grid(coarse_outpost, refine_step, refine_radius)
        candidate_best, candidate_burst, candidate_score = _best_of(lat, lon, time, tree, recorded_fingerprint, fine_candidates, duration_s=duration_s)
        if candidate_score > fine_score:
            fine_best, fine_burst, fine_score = candidate_best, candidate_burst, candidate_score

    if debug_fn:
        debug_fn(
            f"estimate_outpost: fine_best=({fine_best.lat:.4f},{fine_best.lon:.4f}) "
            f"burst=({fine_burst[0]},{fine_burst[1]}) score={fine_score:.6f}"
        )
    return fine_best, fine_burst[0], fine_burst[1]


def score_region(lat, lon, time, tree, recorded_fingerprint, center, duration_s=None, step=0.02, radius=0.3):
    """Similarity score at every point of a local grid around center — for
    visualization (a confidence heatmap), not used by estimate_outpost
    itself. Same grid spacing as the solver's own fine pass, so this shows
    exactly the resolution the answer was actually found at.

    Returns a list of (lat, lon, score).
    """
    candidates = _grid(center, step, radius)
    idx_per_candidate = _batch_query(tree, candidates)

    points = []
    for (clat, clon), idx in zip(candidates, idx_per_candidate):
        candidate = Outpost(clat, clon)
        score, _ = _best_burst(lat, lon, time, tree, recorded_fingerprint, candidate, duration_s=duration_s, idx=idx)
        points.append((clat, clon, score))

    return points


def _coarse_anchors(lat, lon, step, block_deg=0.1):
    """A uniform step-spaced grid, covering only the block_deg blocks that
    actually contain flash activity.

    Rounding each individual flash's own coordinate to step (the previous
    approach) looks like a uniform grid but isn't: it only places anchors
    where flashes happen to sit, so sparse areas — exactly where a
    low-flash-count recording comes from — get bigger gaps than step
    implies (observed 2-4km gaps at step=0.01deg, ~1.1km, in sparse spots).
    A real recording location isn't restricted to exact flash coordinates,
    so anchors shouldn't be either: uniformly tile every populated block
    instead, guaranteeing no gap larger than ~step everywhere activity
    could plausibly be.
    """
    occupied_blocks = np.unique(np.round(np.stack([lat, lon], axis=1) / block_deg) * block_deg, axis=0)
    offsets = np.arange(0, block_deg, step)

    grid_lat, grid_lon = np.meshgrid(offsets, offsets, indexing="ij")
    grid_offsets = np.stack([grid_lat.ravel(), grid_lon.ravel()], axis=1)

    anchors = (occupied_blocks[:, None, :] - block_deg / 2 + grid_offsets[None, :, :]).reshape(-1, 2)
    return np.unique(anchors, axis=0)


def _grid(center, step, radius):
    candidates = []
    lat = center.lat - radius
    while lat <= center.lat + radius:
        lon = center.lon - radius
        while lon <= center.lon + radius:
            candidates.append((lat, lon))
            lon += step
        lat += step
    return candidates


def _batch_query(tree, candidates, max_distance_km=16):
    """KD-tree neighbor indices for every candidate in one call.

    A single query_ball_point call per candidate is cheap on its own, but
    tens of thousands of candidates each paying that Python call overhead
    dominated runtime once the coarse grid got fine enough to be accurate
    (profiling: ~14s of a ~28s solve was inside per-candidate calls, much
    of it call overhead, not the underlying math). Batching the query
    amortizes that overhead across all candidates at once.
    """
    if tree is None:
        return [None] * len(candidates)
    query_radius_deg = max_distance_km / 111 * 1.5
    return tree.query_ball_point(np.asarray(candidates), r=query_radius_deg)


def _best_burst(lat, lon, time, tree, recorded_fingerprint, candidate, duration_s=None, idx=None):
    """Best-scoring time-burst (or within-burst window, if duration_s is
    given) for one candidate location."""
    if duration_s is not None:
        # Vectorized: scores every window of every burst in one batched
        # scatter+matmul instead of a Python loop over individual windows —
        # that loop otherwise dominates runtime for sliding-window search.
        return best_sliding_match(candidate, lat, lon, time, recorded_fingerprint, duration_s, tree=tree, idx=idx)

    best_score = -1.0
    best_burst = (None, None)
    for fingerprint, burst_start, burst_end in build_fingerprints(candidate, lat, lon, time, tree=tree, idx=idx):
        score = similarity(recorded_fingerprint, fingerprint)
        if score > best_score:
            best_score = score
            best_burst = (burst_start, burst_end)

    return best_score, best_burst


def _best_of(lat, lon, time, tree, recorded_fingerprint, candidates, duration_s=None):
    best_score = -1.0
    best_outpost = None
    best_burst = (None, None)

    idx_per_candidate = _batch_query(tree, candidates)
    for (clat, clon), idx in zip(candidates, idx_per_candidate):
        candidate = Outpost(clat, clon)
        score, burst = _best_burst(lat, lon, time, tree, recorded_fingerprint, candidate, duration_s=duration_s, idx=idx)

        if score > best_score:
            best_score = score
            best_outpost = candidate
            best_burst = burst

    return best_outpost, best_burst, best_score


def _top_k(lat, lon, time, tree, recorded_fingerprint, candidates, k, min_separation_deg, duration_s=None):
    """Best-scoring candidates, skipping ones too close to an already-picked one.

    Without this, nearby coarse anchors that describe the same physical spot
    (e.g. (-15.1,-2.4) and (-15.2,-2.4)) can fill several of the k slots,
    crowding out a distinct, weaker-scoring region that a fine pass around
    it would have found.
    """
    scored = []
    idx_per_candidate = _batch_query(tree, candidates)
    for (clat, clon), idx in zip(candidates, idx_per_candidate):
        candidate = Outpost(clat, clon)
        score, burst = _best_burst(lat, lon, time, tree, recorded_fingerprint, candidate, duration_s=duration_s, idx=idx)
        scored.append((candidate, burst, score))

    scored.sort(key=lambda entry: entry[2], reverse=True)

    picked = []
    for candidate, burst, score in scored:
        if len(picked) >= k:
            break
        too_close = any(
            abs(candidate.lat - other.lat) < min_separation_deg
            and abs(candidate.lon - other.lon) < min_separation_deg
            for other, _, _ in picked
        )
        if not too_close:
            picked.append((candidate, burst, score))

    return picked
