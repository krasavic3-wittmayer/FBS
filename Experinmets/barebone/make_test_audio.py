"""Synthesizes a test .wav as if recorded at a random real outpost.

Picks a location near real storm activity, takes the actual sound-arrival
timing/amplitude physics for the flashes it would have heard, renders that
as audio (clap transients + background noise), and writes a .wav.

Deliberately carries no timestamp anywhere — no WAV metadata chunk, no
absolute clock reference in the samples themselves. The whole point is
solving the recording's own time as an unknown (see solver.py), so the
test fixture can't leak it.
"""

import argparse
import random

import numpy as np
from scipy.io import wavfile

from db import build_index, flash_arrays
from fingerprint import nearby_bursts
from generate import generate_flashes, generate_storms
from models import Outpost

SAMPLE_RATE = 44100


def synth_clap(rng, amplitude, sample_rate, decay_s=0.35):
    """One thunder-clap-like transient: filtered noise burst, sharp attack, exponential decay."""
    n = int(decay_s * sample_rate)
    noise = rng.normal(0.0, 1.0, n)
    envelope = np.exp(-np.linspace(0, 6, n))
    return amplitude * noise * envelope


def pick_recording(lat, lon, time, tree, flashes, duration_s, rng, attempts=200, min_events=3):
    """Random outpost near real storm activity, with a duration_s-long
    window that captures at least min_events flashes.

    Retries with a fresh random location (and a fresh assumed "first
    captured event") until one works — same "keep trying near real
    activity" approach as pick_true_outpost.

    The window is anchored to a real event's arrival time (the recording's
    first captured flash must be one of the real events) — the same
    convention solver.sliding_fingerprints searches over, so the true
    window is one it can actually find, and window_start is directly
    comparable to the solver's answer (both are arrival-time based).

    Returns (candidate, rel_times, amplitudes, window_start).
    """
    for _ in range(attempts):
        anchor = flashes[rng.integers(len(flashes))]
        dlat = rng.uniform(-8.0, 8.0) / 111
        dlon = rng.uniform(-8.0, 8.0) / 111
        candidate = Outpost(anchor.lat + dlat, anchor.lon + dlon)

        for _, arrival_time, amplitude, _, _ in nearby_bursts(candidate, lat, lon, time, tree=tree, min_flashes=min_events):
            window_start = arrival_time[rng.integers(len(arrival_time))]
            window_mask = (arrival_time >= window_start) & (arrival_time < window_start + duration_s)
            if window_mask.sum() >= min_events:
                return candidate, arrival_time[window_mask] - window_start, amplitude[window_mask], window_start

    raise RuntimeError("Could not find a recordable outpost near storm activity.")


def render_audio(rel_times, amplitudes, duration_s, sample_rate, rng, noise_level):
    n_samples = int(duration_s * sample_rate)
    audio = rng.normal(0.0, noise_level, n_samples)

    for t, amplitude in zip(rel_times, amplitudes):
        clap = synth_clap(rng, amplitude, sample_rate)
        start = int(t * sample_rate)
        end = min(start + len(clap), n_samples)
        if start < n_samples:
            audio[start:end] += clap[: end - start]

    peak = np.abs(audio).max()
    if peak > 0:
        audio = audio / peak * 0.9

    return (audio * 32767).astype(np.int16)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", type=int, default=None)
    # 60s captures too few flashes for the solver to reliably localize
    # against (see test_end_to_end.py) — 600s is a more realistic default.
    parser.add_argument("--duration", type=float, default=600.0, help="Recording length in seconds")
    parser.add_argument("--noise", type=float, default=0.02, help="Background noise amplitude")
    parser.add_argument("--out", type=str, default="test_recording.wav")
    args = parser.parse_args()

    seed = args.seed if args.seed is not None else random.randrange(2**32)
    random.seed(seed)  # generate.py uses the stdlib random module
    rng = np.random.default_rng(seed)

    storms = generate_storms(24 * 60, 5)
    storm_radius_km = random.uniform(5, 20)
    flashes = generate_flashes(storms, storm_radius_km)
    lat, lon, time = flash_arrays(flashes)
    tree = build_index(lat, lon)

    candidate, rel_times, amplitudes, window_start = pick_recording(lat, lon, time, tree, flashes, args.duration, rng)
    audio = render_audio(rel_times, amplitudes, args.duration, SAMPLE_RATE, rng, args.noise)

    wavfile.write(args.out, SAMPLE_RATE, audio)  # plain RIFF/fmt/data only — no metadata chunk

    print(f"seed={seed}")
    print(f"Wrote {args.out}: duration={args.duration}s, {len(rel_times)} flash events, sample_rate={SAMPLE_RATE}")
    print(
        "(ground truth for testing only, not stored in the file) "
        f"true outpost: lat={candidate.lat:.4f}, lon={candidate.lon:.4f}, "
        f"recording_start={window_start:.1f}s"
    )


if __name__ == "__main__":
    main()
