from pathlib import Path
import wave
import numpy as np

sample_rate = 48_000
duration = 3.0

t = np.arange(int(sample_rate * duration)) / sample_rate

# Impulse
flash = (
    1.0 * np.exp(-t / 0.015)
    - 0.35 * np.exp(-t / 0.08)
)

# Normalize
flash /= np.max(np.abs(flash))

audio = np.int16(flash * 32767)

output = Path("~/Projects/FBS/Experinmets/flash.wav").expanduser()

with wave.open(str(output), "wb") as wav:
    wav.setnchannels(1)
    wav.setsampwidth(2)
    wav.setframerate(sample_rate)
    wav.writeframes(audio.tobytes())