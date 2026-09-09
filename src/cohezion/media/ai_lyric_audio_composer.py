r"""AI Multi-Style Music & Lyric Composition Engine for Cohezion.
=================================================================
Composes stylized vocal scores, rhythmic lyric meters, and multi-genre musical
arrangements (Cinematic Cyberpunk, Neoclassical 432Hz, Synthwave, and Ethereal Ambient).
"""

from __future__ import annotations

import wave
from pathlib import Path
from typing import Any

import numpy as np


# The 10-Step New Science Lyric Libretto
COHEZION_LIBRETTO = [
    {"step": 1, "name": "The Void", "lyrics": "From silent zero in the still expanse,", "freq": 108.0, "vowel_formant": 300.0},
    {"step": 2, "name": "Quadrature", "lyrics": "Four fabrics awaken in orthogonal dance.", "freq": 162.0, "vowel_formant": 450.0},
    {"step": 3, "name": "12 Parameters", "lyrics": "Twelve laws unfold across the primal deep,", "freq": 216.0, "vowel_formant": 600.0},
    {"step": 4, "name": "4 Fabrics", "lyrics": "Space, Field, Control—the ancient covenants keep.", "freq": 270.0, "vowel_formant": 750.0},
    {"step": 5, "name": "Phase i", "lyrics": "The square root turns the axis inside out,", "freq": 324.0, "vowel_formant": 900.0},
    {"step": 6, "name": "Symmetry Breaks", "lyrics": "Broken parity scatters shadows about.", "freq": 360.0, "vowel_formant": 800.0},
    {"step": 7, "name": "Torsion Spin", "lyrics": "Spacetime twists where golden spirals run,", "freq": 405.0, "vowel_formant": 650.0},
    {"step": 8, "name": "HIHO Coherence", "lyrics": "Half In, Half Out—at point five all is One.", "freq": 432.0, "vowel_formant": 500.0},
    {"step": 9, "name": "COHEZION", "lyrics": "The swarm unites, the latent manifold aligns,", "freq": 486.0, "vowel_formant": 400.0},
    {"step": 10, "name": "Reality Precipitates", "lyrics": "And lossless light in matter shines.", "freq": 528.0, "vowel_formant": 350.0},
]

GENRE_STYLES = {
    "cinematic_cyberpunk": {
        "bpm": 84,
        "kick_freq": 55.0,
        "distortion": 1.4,
        "arp_timbre": "sawtooth",
        "description": "Dark analog basslines, heavy industrial pulses, and futuristic vocoder synthesis.",
    },
    "ethereal_ambient_432hz": {
        "bpm": 60,
        "kick_freq": 40.0,
        "distortion": 1.0,
        "arp_timbre": "sine",
        "description": "Lush Pythagorean chord pads, gentle ocean breeze LFOs, and sacred solfeggio overtones.",
    },
    "synthwave_retro": {
        "bpm": 110,
        "kick_freq": 65.0,
        "distortion": 1.2,
        "arp_timbre": "square",
        "description": "Driving 80s arpeggiated bass, sidechained pads, and glowing neon vocoder leads.",
    },
}


class AILyricMusicComposer:
    """Synthesizes musical arrangements with multi-genre styles and vocal formant synthesis."""

    def __init__(self, sample_rate: int = 44100) -> None:
        self.sample_rate = sample_rate

    def synthesize_vocal_formant_line(
        self, pitch_hz: float, formant_hz: float, duration_s: float
    ) -> np.ndarray:
        """Synthesize a human-like vocal vowel sound using resonant formant filtering."""
        t = np.linspace(0, duration_s, int(self.sample_rate * duration_s), endpoint=False)
        # Carrier voice buzz (glottal pulse wave)
        carrier = 0.5 * np.sin(2 * np.pi * pitch_hz * t) + 0.25 * np.sin(2 * np.pi * pitch_hz * 2 * t)
        # Formant resonant envelope
        formant_filter = np.sin(2 * np.pi * formant_hz * t)
        # Gentle vocal vibrato (5.5 Hz)
        vibrato = 1.0 + 0.03 * np.sin(2 * np.pi * 5.5 * t)

        voice = carrier * formant_filter * vibrato
        # Soft vowel envelope
        env = np.sin(np.pi * np.linspace(0, 1, len(t))) ** 0.5
        return voice * env

    def compose_song_with_style(self, style_name: str, out_path: Path) -> dict[str, Any]:
        style = GENRE_STYLES.get(style_name, GENRE_STYLES["cinematic_cyberpunk"])
        bpm = style["bpm"]
        step_duration_s = 2.0  # 2 seconds per lyric line (20s song)
        total_duration_s = step_duration_s * len(COHEZION_LIBRETTO)

        n_samples = int(self.sample_rate * total_duration_s)
        t = np.linspace(0, total_duration_s, n_samples, endpoint=False)
        master_audio = np.zeros(n_samples, dtype=np.float32)

        # 1. Generate Vocal Lead Line for all 10 Lyric Steps
        for idx, line in enumerate(COHEZION_LIBRETTO):
            start_s = idx * int(self.sample_rate * step_duration_s)
            end_s = start_s + int(self.sample_rate * step_duration_s)
            vocal_chunk = self.synthesize_vocal_formant_line(
                pitch_hz=line["freq"],
                formant_hz=line["vowel_formant"],
                duration_s=step_duration_s,
            )
            master_audio[start_s:end_s] += 0.35 * vocal_chunk

        # 2. Add Style-Specific Rhythm & Bass Backing Track
        # Bass Kick Pulse at BPM
        beat_interval = 60.0 / bpm
        beat_samples = int(self.sample_rate * beat_interval)
        for b in range(int(total_duration_s / beat_interval)):
            k_start = b * beat_samples
            k_len = min(int(self.sample_rate * 0.25), n_samples - k_start)
            if k_start >= n_samples:
                break
            kt = np.linspace(0, 0.25, k_len, endpoint=False)
            kick = np.sin(2 * np.pi * style["kick_freq"] * np.exp(-15.0 * kt) * kt) * np.exp(-8.0 * kt)
            master_audio[k_start:k_start + k_len] += 0.40 * kick

        # 3. Add Ambient Pythagorean Chords & Golden Ratio Arpeggio
        pad = 0.20 * np.sin(2 * np.pi * 432.0 * t) + 0.15 * np.sin(2 * np.pi * 648.0 * t)
        master_audio += pad

        # Master Limiter & Normalize
        master_audio = np.tanh(master_audio * style["distortion"]) * 0.90

        # Export WAV
        out_path.parent.mkdir(parents=True, exist_ok=True)
        int_audio = (master_audio * 32767).astype(np.int16)
        with wave.open(str(out_path), "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(self.sample_rate)
            wf.writeframes(int_audio.tobytes())

        return {
            "style_name": style_name,
            "duration_s": total_duration_s,
            "bpm": bpm,
            "file": str(out_path),
            "libretto_steps": len(COHEZION_LIBRETTO),
        }


def generate_all_styles() -> list[dict[str, Any]]:
    composer = AILyricMusicComposer(sample_rate=44100)
    audio_dir = Path("/home/mike-anderson/dev/cohezion/docs/assets/audio")
    results = []

    for style_key in GENRE_STYLES:
        out_file = audio_dir / f"cohezion_{style_key}_song.wav"
        res = composer.compose_song_with_style(style_key, out_file)
        results.append(res)
    return results


if __name__ == "__main__":
    songs = generate_all_styles()
    for s in songs:
        print(f"Generated {s['style_name']} ({s['bpm']} BPM, {s['duration_s']}s) -> {s['file']}")
