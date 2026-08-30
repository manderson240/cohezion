r"""Local Audio & Harmonic Music Synthesizer for Cohezion Storytelling.
======================================================================
Generates high-fidelity 432 Hz Pythagorean harmonic music, sonified HIHO field
transitions, and binaural cognitive resonance audio files directly via NumPy.
"""

from __future__ import annotations

import wave
from pathlib import Path

import numpy as np


class CohezionAudioSynthesizer:
    """Synthesizes high-quality audio tracks, narrative soundscapes, and sonifications."""

    def __init__(self, sample_rate: int = 44100) -> None:
        self.sample_rate = sample_rate

    def generate_hiho_harmonic_soundscape(
        self, duration_s: float = 6.0, base_freq: float = 432.0, coherence: float = 0.5
    ) -> np.ndarray:
        """Generate a 432 Hz Pythagorean harmonic overtone track with golden ratio modulation."""
        t = np.linspace(0, duration_s, int(self.sample_rate * duration_s), endpoint=False)

        fund = 0.40 * np.sin(2 * np.pi * base_freq * t)
        fifth = 0.25 * np.sin(2 * np.pi * (base_freq * 1.5) * t)
        octave = 0.15 * np.sin(2 * np.pi * (base_freq * 2.0) * t)
        phi_harmonic = 0.15 * np.sin(2 * np.pi * (base_freq * 1.6180339887) * t)

        dissonance_factor = abs(coherence - 0.5) * 2.0
        noise = dissonance_factor * 0.08 * np.random.normal(0, 0.1, len(t))

        envelope = np.ones_like(t)
        attack_len = int(self.sample_rate * 0.5)
        release_len = int(self.sample_rate * 1.0)
        envelope[:attack_len] = np.linspace(0, 1, attack_len)
        envelope[-release_len:] = np.linspace(1, 0, release_len)

        audio = (fund + fifth + octave + phi_harmonic + noise) * envelope
        return np.clip(audio, -1.0, 1.0)

    def save_wav(self, audio: np.ndarray, out_path: Path) -> None:
        """Save normalized float array to 16-bit PCM WAV file."""
        out_path.parent.mkdir(parents=True, exist_ok=True)
        int_audio = (audio * 32767).astype(np.int16)

        with wave.open(str(out_path), "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(self.sample_rate)
            wf.writeframes(int_audio.tobytes())


def generate_story_audio_assets() -> list[Path]:
    synth = CohezionAudioSynthesizer(sample_rate=44100)
    audio_dir = Path("/home/mike-anderson/dev/cohezion/docs/assets/audio")
    audio_dir.mkdir(parents=True, exist_ok=True)

    tracks = [
        ("01_nothingness_void.wav", 4.0, 108.0, 0.1),
        ("02_quadrature_field.wav", 5.0, 216.0, 0.3),
        ("03_hiho_perfect_coherence_432hz.wav", 6.0, 432.0, 0.5),
        ("04_reality_precipitation.wav", 6.0, 528.0, 0.5),
    ]

    saved_files = []
    for filename, dur, freq, coh in tracks:
        path = audio_dir / filename
        sig = synth.generate_hiho_harmonic_soundscape(duration_s=dur, base_freq=freq, coherence=coh)
        synth.save_wav(sig, path)
        saved_files.append(path)

    return saved_files


if __name__ == "__main__":
    files = generate_story_audio_assets()
    for f in files:
        print(f"Generated Audio Track: {f} ({f.stat().st_size} bytes)")
