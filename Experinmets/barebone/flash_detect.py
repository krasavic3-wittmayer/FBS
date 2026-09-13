"""Detects thunder-clap-like transients in a raw audio recording.

Real arrival time already has sound-propagation delay baked in physically —
unlike the synthetic path, no delay() simulation is needed here.
"""

import numpy as np
from scipy.signal import find_peaks


def detect_flashes(samples, sample_rate, min_separation_s=0.05, threshold_std=4.0):
    """Peaks in the smoothed envelope, above a noise-floor threshold.

    min_separation_s enforces a refractory period so one clap's crack and
    rumble aren't counted as separate events. amplitude is normalized to
    the loudest detected peak in this recording (0-1), matching the scale
    build_fingerprint's amplitude() uses for the synthetic path.
    """
    envelope = np.abs(samples)

    smoothing_window = max(1, int(0.002 * sample_rate))  # ~2ms
    if smoothing_window > 1:
        kernel = np.ones(smoothing_window) / smoothing_window
        envelope = np.convolve(envelope, kernel, mode="same")

    threshold = np.median(envelope) + threshold_std * np.std(envelope)
    min_distance = max(1, int(min_separation_s * sample_rate))

    peaks, properties = find_peaks(envelope, height=threshold, distance=min_distance)

    times = peaks / sample_rate
    amplitudes = properties["peak_heights"]
    peak_max = amplitudes.max() if len(amplitudes) > 0 else 0.0
    if peak_max > 0:
        amplitudes = amplitudes / peak_max

    return times, amplitudes
