from pathlib import Path
import wave
import numpy as np

sample_rate = 48_000
duration = 10.0

t = np.arange(int(sample_rate * duration)) / sample_rate

flash = (
    1.0 * np.exp(-t / 0.03) +
    10.0 * np.exp(-t / 0.5) +
    16.0 * np.exp(-t / 2.0) +
    14.0 * np.exp(-t / 5.0) +
    10.0 * np.exp(-t / 10.0)
)

flash /= np.max(np.abs(flash))

# Normalize
flash /= np.max(np.abs(flash))

audio = np.int16(flash * 32767)

output = Path("~/Projects/FBS/Experinmets/flash.wav").expanduser()

with wave.open(str(output), "wb") as wav:
    wav.setnchannels(1)
    wav.setsampwidth(2)
    wav.setframerate(sample_rate)
    wav.writeframes(audio.tobytes())