"""End-to-end test: synthesize a test .wav for a random real outpost, then
feed ONLY that .wav through the real FBS solver and compare its guess
against ground truth.

No shortcuts past the audio: once the .wav is written, the pipeline is
exactly main.py's --audio path (load_audio -> detect_flashes -> bin_events
-> estimate_outpost). Location and recording time are both unknowns the
solver has to find; the detector is untouched (test only, per request).
"""

import argparse
import os
import random
import tempfile

import numpy as np
from scipy.io import wavfile

from audio_input import load_audio
from db import build_index, flash_arrays
from fingerprint import bin_events
from flash_detect import detect_flashes
from generate import generate_flashes, generate_storms
from make_test_audio import SAMPLE_RATE, pick_recording, render_audio
from physics import distance_km
from solver import estimate_outpost


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", type=int, default=None)
    # 60s is too sparse to reliably localize (only a handful of flashes;
    # sliding-window matching against so little signal is easily fooled by
    # chance alignment elsewhere) — 600s gives enough events to work.
    parser.add_argument("--duration", type=float, default=600.0, help="Recording length in seconds")
    parser.add_argument("--noise", type=float, default=0.02, help="Background noise amplitude")
    parser.add_argument("--debug", action="store_true")
    args = parser.parse_args()

    seed = args.seed if args.seed is not None else random.randrange(2**32)
    random.seed(seed)  # generate.py uses the stdlib random module
    rng = np.random.default_rng(seed)
    print(f"seed={seed}")

    storms = generate_storms(24 * 60, 5)
    storm_radius_km = random.uniform(5, 20)
    flashes = generate_flashes(storms, storm_radius_km)
    lat, lon, time = flash_arrays(flashes)
    tree = build_index(lat, lon)

    true_outpost, rel_times, amplitudes, window_start = pick_recording(
        lat, lon, time, tree, flashes, args.duration, rng
    )
    audio = render_audio(rel_times, amplitudes, args.duration, SAMPLE_RATE, rng, args.noise)

    fd, wav_path = tempfile.mkstemp(suffix=".wav")
    os.close(fd)
    try:
        wavfile.write(wav_path, SAMPLE_RATE, audio)

        # From here on, only the .wav file is used — same as `main.py --audio`.
        samples, sample_rate = load_audio(wav_path)
        detected_times, detected_amplitudes = detect_flashes(samples, sample_rate)
        # window_s=duration_s: bin width must match the actual recording
        # length, not the 1800s default sized for whole-burst matching —
        # otherwise a short recording collapses into 1-2 bins.
        recorded_fingerprint = bin_events(detected_times, detected_amplitudes, window_s=args.duration)
    finally:
        os.remove(wav_path)

    print(f"True flash count: {len(rel_times)}, detected from audio: {len(detected_times)}")

    if recorded_fingerprint is None:
        print("No events detected from audio — cannot solve.")
        return

    debug_fn = print if args.debug else None
    calc_outpost, calc_burst_start, calc_burst_end = estimate_outpost(
        lat, lon, time, tree, recorded_fingerprint, duration_s=args.duration, debug_fn=debug_fn
    )

    location_error_km = distance_km(true_outpost.lat, true_outpost.lon, calc_outpost.lat, calc_outpost.lon)
    time_error_s = abs(calc_burst_start - window_start) if calc_burst_start is not None else None

    print(f"True outpost:      lat={true_outpost.lat:.4f}, lon={true_outpost.lon:.4f}, recording_start={window_start:.1f}s")
    if calc_outpost is not None:
        print(
            f"Predicted outpost: lat={calc_outpost.lat:.4f}, lon={calc_outpost.lon:.4f}, "
            f"burst=({calc_burst_start:.1f}s,{calc_burst_end:.1f}s)"
        )
    else:
        print("Predicted outpost: none")

    print(f"Location error: {location_error_km:.2f} km")
    print(f"Time error: {time_error_s:.1f} s" if time_error_s is not None else "Time error: n/a")


if __name__ == "__main__":
    main()
