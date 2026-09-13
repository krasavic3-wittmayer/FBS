"""Estimates an outpost location from a recorded fingerprint alone.

Never receives the true outpost coordinates — only the recorded
fingerprint and the flash arrays, same as a real localization task.
"""

import numpy as np

from fingerprint import build_fingerprint, similarity
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
            + ", ".join(f"({o.lat:.4f},{o.lon:.4f})={s:.6f}" for o, s in coarse_top)
        )

    # Fine pass: local grid search around each retained coarse candidate,
    # keeping the best result across all of them.
    fine_best, fine_score = None, -1.0
    for coarse_outpost, _ in coarse_top:
        fine_candidates = _grid(coarse_outpost, refine_step, refine_radius)
        candidate_best, candidate_score = _best_of(lat, lon, time, tree, recorded_fingerprint, fine_candidates)
        if candidate_score > fine_score:
            fine_best, fine_score = candidate_best, candidate_score

    if debug_fn:
        debug_fn(
            f"estimate_outpost: fine_best=({fine_best.lat:.4f},{fine_best.lon:.4f}) score={fine_score:.6f}"
        )
    return fine_best


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


def _best_of(lat, lon, time, tree, recorded_fingerprint, candidates):
    best_score = -1.0
    best_outpost = None

    for clat, clon in candidates:
        candidate = Outpost(clat, clon)
        fingerprint = build_fingerprint(candidate, lat, lon, time, tree=tree)
        score = similarity(recorded_fingerprint, fingerprint)

        if score > best_score:
            best_score = score
            best_outpost = candidate

    return best_outpost, best_score


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
        fingerprint = build_fingerprint(candidate, lat, lon, time, tree=tree)
        score = similarity(recorded_fingerprint, fingerprint)
        scored.append((candidate, score))

    scored.sort(key=lambda pair: pair[1], reverse=True)

    picked = []
    for candidate, score in scored:
        if len(picked) >= k:
            break
        too_close = any(
            abs(candidate.lat - other.lat) < min_separation_deg
            and abs(candidate.lon - other.lon) < min_separation_deg
            for other, _ in picked
        )
        if not too_close:
            picked.append((candidate, score))

    return picked
