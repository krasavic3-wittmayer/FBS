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

from fingerprint import build_fingerprints, similarity
from models import Outpost


def estimate_outpost(lat, lon, time, tree, recorded_fingerprint, refine_step=0.02, refine_radius=0.3, coarse_k=20, debug_fn=None):
    # Coarse pass: probe near actual flash clusters, since the true outpost
    # must sit within range of real activity.
    #
    # similarity() decays to a noise floor within a few km, well inside the
    # ~11km coarse anchor spacing, so the single best coarse anchor is often
    # not the true outpost's cell. Keep the top-k anchors and refine all of
    # them, instead of committing to just the single best one.
    anchors = np.unique(np.round(np.stack([lat, lon], axis=1), 1), axis=0)
    coarse_top = _top_k(lat, lon, time, tree, recorded_fingerprint, anchors, coarse_k, min_separation_deg=2 * refine_radius)
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
        candidate_best, candidate_burst, candidate_score = _best_of(lat, lon, time, tree, recorded_fingerprint, fine_candidates)
        if candidate_score > fine_score:
            fine_best, fine_burst, fine_score = candidate_best, candidate_burst, candidate_score

    if debug_fn:
        debug_fn(
            f"estimate_outpost: fine_best=({fine_best.lat:.4f},{fine_best.lon:.4f}) "
            f"burst=({fine_burst[0]},{fine_burst[1]}) score={fine_score:.6f}"
        )
    return fine_best, fine_burst[0], fine_burst[1]


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


def _best_burst(lat, lon, time, tree, recorded_fingerprint, candidate):
    """Best-scoring time-burst for one candidate location."""
    best_score = -1.0
    best_burst = (None, None)

    for fingerprint, burst_start, burst_end in build_fingerprints(candidate, lat, lon, time, tree=tree):
        score = similarity(recorded_fingerprint, fingerprint)
        if score > best_score:
            best_score = score
            best_burst = (burst_start, burst_end)

    return best_score, best_burst


def _best_of(lat, lon, time, tree, recorded_fingerprint, candidates):
    best_score = -1.0
    best_outpost = None
    best_burst = (None, None)

    for clat, clon in candidates:
        candidate = Outpost(clat, clon)
        score, burst = _best_burst(lat, lon, time, tree, recorded_fingerprint, candidate)

        if score > best_score:
            best_score = score
            best_outpost = candidate
            best_burst = burst

    return best_outpost, best_burst, best_score


def _top_k(lat, lon, time, tree, recorded_fingerprint, candidates, k, min_separation_deg):
    """Best-scoring candidates, skipping ones too close to an already-picked one.

    Without this, nearby coarse anchors that describe the same physical spot
    (e.g. (-15.1,-2.4) and (-15.2,-2.4)) can fill several of the k slots,
    crowding out a distinct, weaker-scoring region that a fine pass around
    it would have found.
    """
    scored = []
    for clat, clon in candidates:
        candidate = Outpost(clat, clon)
        score, burst = _best_burst(lat, lon, time, tree, recorded_fingerprint, candidate)
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
