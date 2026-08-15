import numpy as np
from scipy.io import wavfile
from scipy.signal import spectrogram
from scipy.ndimage import uniform_filter1d


def wav_to_fingerprint(path):
    sample_rate, audio = wavfile.read(path)

    if audio.ndim > 1:
        audio = audio.mean(axis=1)

    frequencies, times, Sxx = spectrogram(
        audio,
        fs=sample_rate
    )

    mask = (frequencies >= 20) & (frequencies <= 500)
    low_freq = Sxx[mask]

    fingerprint = np.mean(low_freq, axis=0)

    fingerprint = (
        fingerprint - fingerprint.min()
    ) / (
        fingerprint.max() - fingerprint.min()
    )

    fingerprint = uniform_filter1d(
        fingerprint,
        size=100
    )

    return fingerprint