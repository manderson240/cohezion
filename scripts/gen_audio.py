import struct
import wave

import numpy as np


def generate_stability_tone(duration=2.0, freq=432.0, output_path="src/cohezion/api/static/stability_pulse.wav"):
    sample_rate = 44100
    n_samples = int(duration * sample_rate)
    t = np.linspace(0, duration, n_samples)

    # Generate a smooth sine wave with a subtle modulation
    wave_data = 0.5 * np.sin(2 * np.pi * freq * t) * (1 + 0.1 * np.sin(2 * np.pi * 2 * t))

    # Convert to 16-bit PCM
    wave_data = (wave_data * 32767).astype(np.int16)

    with wave.open(output_path, "w") as f:
        f.setnchannels(1)
        f.setsampwidth(2)
        f.setframerate(sample_rate)
        for s in wave_data:
            f.writeframes(struct.pack("h", s))
    print(f"Generated tone at {output_path}")


if __name__ == "__main__":
    generate_stability_tone()
