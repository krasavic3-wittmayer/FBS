"""Detects thunder-clap-like transients in a raw audio recording.

Real arrival time already has sound-propagation delay baked in physically —
unlike the synthetic path, no delay() simulation is needed here.
"""

import numpy as np


def detect_flashes(samples, sample_rate, threshold_std=4.0, merge_gap_s=0.01):
    """One event per contiguous stretch of the envelope above a noise-floor
    threshold — not one event per local peak.

    A single clap's own decaying noise randomly re-crosses a fixed peak
    threshold many times as it fades, so peak-picking alone (previously via
    scipy.signal.find_peaks with a fixed minimum spacing) counted one real
    clap as several events; that spacing would either undercount close
    genuine flashes or overcount noisy ones depending on the clap's actual
    decay length, which varies. Grouping by contiguous above-threshold runs
    instead ties event boundaries to the recording's own loudness, so it
    doesn't depend on guessing a clap duration.

    merge_gap_s only bridges a threshold dip lasting a couple of samples in
    the middle of one continuous transient (noise hovering near the
    threshold) — real distinct flashes are separated by far more than that,
    so it doesn't merge genuinely separate events.

    amplitude is normalized to the loudest detected peak in this recording
    (0-1), matching the scale build_fingerprint's amplitude() uses for the
    synthetic path.
    """
    envelope = np.abs(samples)

    smoothing_window = max(1, int(0.002 * sample_rate))  # ~2ms
    if smoothing_window > 1:
        kernel = np.ones(smoothing_window) / smoothing_window
        envelope = np.convolve(envelope, kernel, mode="same")

    threshold = np.median(envelope) + threshold_std * np.std(envelope)
    above = envelope > threshold

    if not np.any(above):
        return np.array([]), np.array([])

    edges = np.diff(above.astype(np.int8))
    starts = list(np.where(edges == 1)[0] + 1)
    ends = list(np.where(edges == -1)[0] + 1)
    if above[0]:
        starts.insert(0, 0)
    if above[-1]:
        ends.append(len(above))

    merge_gap = max(1, int(merge_gap_s * sample_rate))
    merged_starts, merged_ends = [starts[0]], [ends[0]]
    for s, e in zip(starts[1:], ends[1:]):
        if s - merged_ends[-1] <= merge_gap:
            merged_ends[-1] = e
        else:
            merged_starts.append(s)
            merged_ends.append(e)

    times = []
    amplitudes = []
    for s, e in zip(merged_starts, merged_ends):
        peak_index = s + int(np.argmax(envelope[s:e]))
        times.append(peak_index / sample_rate)
        amplitudes.append(envelope[peak_index])

    times = np.array(times)
    amplitudes = np.array(amplitudes)
    peak_max = amplitudes.max() if len(amplitudes) > 0 else 0.0
    if peak_max > 0:
        amplitudes = amplitudes / peak_max

    return times, amplitudes
