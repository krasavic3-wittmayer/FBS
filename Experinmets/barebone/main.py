import argparse
import random
import sys

from audio_input import load_audio
from db import build_index, create_db, flash_arrays, load_flashes_db
from fingerprint import bin_events, build_fingerprints
from flash_detect import detect_flashes
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
    recorded fingerprint and to report the error afterwards. Also returns
    the true burst window (the actual storm the "recording" came from),
    since the recording's time is just as unknown to the solver as its
    location.
    """
    for attempt in range(attempts):
        anchor = random.choice(flashes)
        dlat = random.uniform(-jitter_km, jitter_km) / 111
        dlon = random.uniform(-jitter_km, jitter_km) / 111
        candidate = Outpost(anchor.lat + dlat, anchor.lon + dlon)

        for fingerprint, burst_start, burst_end in build_fingerprints(candidate, lat, lon, time, tree=tree, min_flashes=5):
            if not (burst_start <= anchor.time <= burst_end):
                continue  # a different storm than the one anchor came from
            debug(
                f"pick_true_outpost: attempt={attempt} anchor=({anchor.lat:.4f},{anchor.lon:.4f}) "
                f"candidate=({candidate.lat:.4f},{candidate.lon:.4f}) burst=({burst_start:.1f},{burst_end:.1f}) "
                f"fingerprint_nonzero_bins={int((fingerprint != 0).sum())} "
                f"fingerprint_sum={fingerprint.sum():.4f}"
            )
            return candidate, fingerprint, burst_start, burst_end
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

    true_outpost, recorded_fingerprint, true_burst_start, true_burst_end = pick_true_outpost(lat, lon, time, tree, flashes)

    # Solver only ever sees recorded_fingerprint and the flash arrays, not
    # true_outpost or the true burst window — it has to find both.
    calculated_outpost, calc_burst_start, calc_burst_end = estimate_outpost(lat, lon, time, tree, recorded_fingerprint, debug_fn=debug)

    error_km = distance_km(
        true_outpost.lat, true_outpost.lon,
        calculated_outpost.lat, calculated_outpost.lon,
    )
    time_error_s = abs(calc_burst_start - true_burst_start) if calc_burst_start is not None else None

    print(f"{len(flashes)} flashes generated from {len(storms)} storms.\n")
    print(f"Expected outpost:    lat={true_outpost.lat:.4f}, lon={true_outpost.lon:.4f}, burst=({true_burst_start:.1f}s,{true_burst_end:.1f}s)")
    print(f"Calculated outpost:  lat={calculated_outpost.lat:.4f}, lon={calculated_outpost.lon:.4f}, burst=({calc_burst_start:.1f}s,{calc_burst_end:.1f}s)")
    print(f"Location error: {error_km:.2f} km")
    print(f"Time error: {time_error_s:.1f} s" if time_error_s is not None else "Time error: n/a")

    return error_km


def run_from_audio(path, db_path=None):
    samples, sample_rate = load_audio(path)
    duration_s = len(samples) / sample_rate
    print(f"Loaded audio: {path}")
    print(f"sample_rate={sample_rate} Hz, samples={len(samples)}, duration={duration_s:.2f}s")

    times, amplitudes = detect_flashes(samples, sample_rate)
    print(f"Detected {len(times)} flash events")
    for t, a in zip(times, amplitudes):
        debug(f"  t={t:.3f}s amplitude={a:.3f}")

    if len(times) == 0:
        print("No flash events detected — nothing to localize.")
        return

    recorded_fingerprint = bin_events(times, amplitudes, window_s=duration_s)
    debug(f"fingerprint nonzero_bins={int((recorded_fingerprint != 0).sum())}")

    flashes = load_flashes_db(db_path) if db_path else []
    if db_path and not flashes:
        print(f"Flash database is empty: {db_path} — falling back to synthetic data.")

    if flashes:
        print(f"Matching against flash database: {db_path} ({len(flashes)} flashes)")
    else:
        print("No flash database given — generating a synthetic one to match against.")
        storms = generate_storms(24 * 60, 5)
        storm_radius_km = random.uniform(5, 20)
        flashes = generate_flashes(storms, storm_radius_km)

    lat, lon, flash_time = flash_arrays(flashes)
    tree = build_index(lat, lon)

    calculated_outpost, calc_burst_start, calc_burst_end = estimate_outpost(
        lat, lon, flash_time, tree, recorded_fingerprint, duration_s=duration_s, debug_fn=debug
    )
    if calculated_outpost is None:
        print("Could not localize — no matching pattern found.")
        return

    print(f"Predicted location: lat={calculated_outpost.lat:.4f}, lon={calculated_outpost.lon:.4f}")
    print(f"Predicted recording window: {calc_burst_start:.1f}s - {calc_burst_end:.1f}s (arbitrary reference clock)")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument("--debug", action="store_true")
    parser.add_argument("--audio", type=str, default=None, help="Audio file to import (skips the menu)")
    parser.add_argument("--db", type=str, default=None, help="Flash SQLite db to match against (e.g. logger/live_flashes.db); omit for synthetic test data")
    args = parser.parse_args()

    DEBUG = args.debug

    if args.audio:
        run_from_audio(args.audio, db_path=args.db)
    else:
        choice = input("1) Import audio\n2) Random outpost\n> ").strip()
        if choice == "1":
            audio_path = input("Audio file path: ").strip()
            db_path = args.db or input("Flash database path (blank for synthetic): ").strip() or None
            run_from_audio(audio_path, db_path=db_path)
        else:
            main(seed=args.seed)
