"""Estimates an outpost location from a recorded fingerprint alone.

Never receives the true outpost coordinates — only the recorded
fingerprint and the flash database, same as a real localization task.
"""

from db import query_nearby
from fingerprint import build_fingerprint, similarity
from models import Outpost


def estimate_outpost(conn, recorded_fingerprint, refine_step=0.02, refine_radius=0.3, debug_fn=None):
    # Coarse pass: probe near actual flash clusters (deduped in SQL),
    # since the true outpost must sit within range of real activity.
    anchors = conn.execute(
        "SELECT DISTINCT ROUND(lat, 1), ROUND(lon, 1) FROM flashes"
    ).fetchall()
    coarse_best, coarse_score = _best_of(conn, recorded_fingerprint, anchors)
    if debug_fn:
        debug_fn(
            f"estimate_outpost: coarse anchors={len(anchors)} "
            f"coarse_best=({coarse_best.lat:.4f},{coarse_best.lon:.4f}) score={coarse_score:.6f}"
        )

    # Fine pass: local grid search around the coarse best guess.
    fine_candidates = _grid(coarse_best, refine_step, refine_radius)
    fine_best, fine_score = _best_of(conn, recorded_fingerprint, fine_candidates)
    if debug_fn:
        debug_fn(
            f"estimate_outpost: fine candidates={len(fine_candidates)} "
            f"fine_best=({fine_best.lat:.4f},{fine_best.lon:.4f}) score={fine_score:.6f}"
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


def _best_of(conn, recorded_fingerprint, candidates):
    best_score = -1.0
    best_outpost = None

    for lat, lon in candidates:
        candidate = Outpost(lat, lon)
        rows = query_nearby(conn, candidate)
        fingerprint = build_fingerprint(candidate, rows)
        score = similarity(recorded_fingerprint, fingerprint)

        if score > best_score:
            best_score = score
            best_outpost = candidate

    return best_outpost, best_score
