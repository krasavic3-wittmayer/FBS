import argparse
import random
import sys

from db import build_index, create_db, flash_arrays
from fingerprint import build_fingerprint
from generate import generate_flashes, generate_storms
from models import Outpost
from physics import distance_km
from solver import estimate_outpost

DEBUG = False


def debug(*args):
    if DEBUG:
        print(*args, file=sys.stderr)


def pick_true_outpost(lat, lon, time, tree, flashes, attempts=200, jitter_km=8.0):
    """Random outpost near real storm activity, jittered off any exact flash.

    Not guessable from the flash table alone; only used to build the
    recorded fingerprint and to report the error afterwards.
    """
    for attempt in range(attempts):
        anchor = random.choice(flashes)
        dlat = random.uniform(-jitter_km, jitter_km) / 111
        dlon = random.uniform(-jitter_km, jitter_km) / 111
        candidate = Outpost(anchor.lat + dlat, anchor.lon + dlon)

        fingerprint = build_fingerprint(candidate, lat, lon, time, tree=tree, min_flashes=5)
        if fingerprint is not None:
            debug(
                f"pick_true_outpost: attempt={attempt} anchor=({anchor.lat:.4f},{anchor.lon:.4f}) "
                f"candidate=({candidate.lat:.4f},{candidate.lon:.4f}) "
                f"fingerprint_nonzero_bins={int((fingerprint != 0).sum())} "
                f"fingerprint_sum={fingerprint.sum():.4f}"
            )
            return candidate, fingerprint
    raise RuntimeError("Could not find an outpost with enough nearby flashes.")


def main(seed=None):
    if seed is None:
        seed = random.randrange(2**32)
    random.seed(seed)
    print(f"seed={seed}")

    storms = generate_storms(24 * 60, 5)
    storm_radius_km = random.uniform(5, 20)
    flashes = generate_flashes(storms, storm_radius_km)
    create_db(flashes)  # persisted to flashes.db for inspection; not used for solving
    lat, lon, time = flash_arrays(flashes)
    tree = build_index(lat, lon)
    debug(f"storm_radius_km={storm_radius_km:.4f}")

    true_outpost, recorded_fingerprint = pick_true_outpost(lat, lon, time, tree, flashes)

    # Solver only ever sees recorded_fingerprint and the flash arrays, not true_outpost.
    calculated_outpost = estimate_outpost(lat, lon, time, tree, recorded_fingerprint, debug_fn=debug)

    error_km = distance_km(
        true_outpost.lat, true_outpost.lon,
        calculated_outpost.lat, calculated_outpost.lon,
    )

    print(f"{len(flashes)} flashes generated from {len(storms)} storms.\n")
    print(f"Expected outpost:   lat={true_outpost.lat:.4f}, lon={true_outpost.lon:.4f}")
    print(f"Calculated outpost: lat={calculated_outpost.lat:.4f}, lon={calculated_outpost.lon:.4f}")
    print(f"Error: {error_km:.2f} km")

    return error_km


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument("--debug", action="store_true")
    args = parser.parse_args()

    DEBUG = args.debug
    main(seed=args.seed)
