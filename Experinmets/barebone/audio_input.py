"""Decodes an audio-containing file into raw samples.

Uses pydub (ffmpeg backend), so the input format is inferred from the file's
actual content, not its extension — covers wav/mp3/flac/ogg/m4a, audio
tracks pulled out of video containers, etc.
"""

import numpy as np
from pydub import AudioSegment


def load_audio(path):
    segment = AudioSegment.from_file(path).set_channels(1)

    samples = np.array(segment.get_array_of_samples(), dtype=np.float32)
    full_scale = float(1 << (8 * segment.sample_width - 1))
    samples /= full_scale

    return samples, segment.frame_rate
