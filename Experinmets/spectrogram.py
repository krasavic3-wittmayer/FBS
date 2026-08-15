import numpy as np
import matplotlib.pyplot as plt
from scipy.io import wavfile
from scipy.signal import spectrogram
from scipy.ndimage import uniform_filter1d

sample_rate, audio = wavfile.read("./Experinmets/flash.wav")

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
) / (fingerprint.max() - fingerprint.min())

fingerprint_smoothed = uniform_filter1d(fingerprint, size=100)

a = fingerprint_smoothed
b = np.roll(a, 50)

similarity = np.dot(a, b) / (
    np.linalg.norm(a) * np.linalg.norm(b)
)

similarity = np.dot(a, b) / (
    np.linalg.norm(a) * np.linalg.norm(b)
)

print(similarity)
plt.plot(times, fingerprint_smoothed)
plt.show()

for shift in [0, 50, 100, 200, 500]:
    b = np.roll(a, shift)

    similarity = np.dot(a, b) / (
        np.linalg.norm(a) * np.linalg.norm(b)
    )

    print(shift, similarity)