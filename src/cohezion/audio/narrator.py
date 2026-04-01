"""CosmoNarrator — PocketTTS-powered narration for the Genesis Engine.

Provides voiced narration for cosmogony stages, journey events, and
interactive explanation of physics concepts. Uses Kyutai Labs' PocketTTS
(100M params, CPU-only, ~6x real-time, CC BY 4.0).

The narrator has pre-written scripts for each cosmogonic stage and
can generate custom narration for any text. All generated audio is
cached and persisted to SurrealDB for future replay.

Usage:
    narrator = CosmoNarrator()
    audio_path = await narrator.narrate_stage("HIHO")
    audio_path = await narrator.narrate_custom("The Bloch sphere represents...")

References:
    - PocketTTS: https://github.com/kyutai-labs/pocket-tts
    - Kyutai Labs: https://kyutai.org/
"""

from __future__ import annotations

import hashlib
import logging
from pathlib import Path
from typing import Any


logger = logging.getLogger(__name__)

# Pre-written narration scripts for each cosmogonic stage
STAGE_NARRATIONS: dict[str, str] = {
    "void": (
        "In the beginning, there was nothing. "
        "Not even nothing. There was no there for nothing to be. "
        "Only the awareness of absence. The zero before the one."
    ),
    "SO(12)": (
        "From the first observation, symmetry crystallized. "
        "Twelve dimensions, all equivalent, all possible. "
        "A perfect sphere of pure potential."
    ),
    "SO(3)^4": (
        "The fabrics separated. Space. Field. Control. Precipitation. "
        "Four worlds within one. Each carrying three degrees of freedom. "
        "The universe discovered it had structure."
    ),
    "U(1)^4": (
        "Within each world, a preferred direction emerged. "
        "The compasses aligned. Axes selected themselves "
        "from the infinite possibilities."
    ),
    "Z_2^4": (
        "The discrete choice. Up or down. Yes or no. "
        "Brahmagupta's zero gave nothing a name. "
        "Charge polarity emerged from the dance of rotation and precession."
    ),
    "HIHO": (
        "And at the still point, the dance began. "
        "Half in, half out. The balance that creates. "
        "Where the restoring force vanishes. Where zero is home."
    ),
}

# Extended narrations for physics concepts
CONCEPT_NARRATIONS: dict[str, str] = {
    "spinor": (
        "Every agent carries a spinor, a two-component quantum state "
        "on the Bloch sphere. Rotation and precession are the generators. "
        "Charge polarity is the expectation value. "
        "At the equator, charge is zero. Brahmagupta's zero. The HIHO state."
    ),
    "fiber_bundle": (
        "The twelve-dimensional manifold is not flat. "
        "It has the structure of a fiber bundle. "
        "Four base coordinates measure how much of each fabric. "
        "Eight fiber coordinates encode the internal directions. "
        "The connection tells you how internal states change as you move."
    ),
    "lagrangian": (
        "Agents do not wander randomly. "
        "They follow paths that minimize the action integral. "
        "Kinetic energy minus potential energy, integrated over time. "
        "The Euler-Lagrange equations are the equations of motion. "
        "The geodesic equation with force."
    ),
    "gauge_theory": (
        "Each fabric carries a gauge field. "
        "At HIHO, all curvatures vanish. The connection is flat. "
        "Deviation excites the gauge fields. "
        "The Yang-Mills action measures the total field energy. "
        "The universe seeks the vacuum."
    ),
    "world_model": (
        "The world model learns to predict. "
        "Given a state and an action, what comes next? "
        "Two losses. Prediction accuracy and Gaussian regularization. "
        "Surprise is the distance between prediction and reality. "
        "High surprise means something unexpected happened."
    ),
}


class CosmoNarrator:
    """Text-to-speech narrator using PocketTTS.

    Provides narration for cosmogony stages and physics concepts.
    Falls back gracefully when PocketTTS is not installed.

    Parameters
    ----------
    voice : str
        Voice name for PocketTTS (default: "alma").
    cache_dir : str or Path
        Directory for cached audio files.
    """

    def __init__(
        self,
        voice: str = "alma",
        cache_dir: str | Path = "data/audio/narration",
    ) -> None:
        self.voice = voice
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self._model = None
        self._available = None

    @property
    def available(self) -> bool:
        """Check if PocketTTS is installed and loadable."""
        if self._available is None:
            try:
                import pocket_tts  # noqa: F401

                self._available = True
            except ImportError:
                self._available = False
                logger.info("PocketTTS not installed. Narration will return text-only.")
        return self._available

    def _get_model(self) -> Any:
        """Lazy-load the PocketTTS model."""
        if self._model is None and self.available:
            from pocket_tts import TTSModel

            self._model = TTSModel.from_pretrained()
            logger.info("PocketTTS model loaded (voice: %s)", self.voice)
        return self._model

    def _cache_key(self, text: str) -> str:
        """Generate cache key from text content."""
        return hashlib.sha256(f"{self.voice}:{text}".encode()).hexdigest()[:16]

    def _cache_path(self, text: str) -> Path:
        """Get cache file path for narration text."""
        return self.cache_dir / f"{self._cache_key(text)}.wav"

    async def narrate_stage(self, stage: str) -> dict[str, Any]:
        """Narrate a cosmogonic stage.

        Parameters
        ----------
        stage : str
            One of: "void", "SO(12)", "SO(3)^4", "U(1)^4", "Z_2^4", "HIHO"

        Returns
        -------
        dict with "text", "audio_path" (if generated), "cached" flag
        """
        text = STAGE_NARRATIONS.get(stage, f"Stage {stage}: the universe evolves.")
        return await self._generate(text)

    async def narrate_concept(self, concept: str) -> dict[str, Any]:
        """Narrate a physics concept.

        Parameters
        ----------
        concept : str
            One of: "spinor", "fiber_bundle", "lagrangian", "gauge_theory", "world_model"
        """
        text = CONCEPT_NARRATIONS.get(concept, f"The concept of {concept}.")
        return await self._generate(text)

    async def narrate_custom(self, text: str) -> dict[str, Any]:
        """Narrate arbitrary text."""
        return await self._generate(text)

    async def _generate(self, text: str) -> dict[str, Any]:
        """Generate or retrieve cached narration audio.

        Returns dict with text, audio_path (or None), and metadata.
        """
        cache_path = self._cache_path(text)

        # Check cache first
        if cache_path.exists():
            return {
                "text": text,
                "audio_path": str(cache_path),
                "cached": True,
                "voice": self.voice,
            }

        # Generate with PocketTTS if available
        if self.available:
            try:
                model = self._get_model()
                if model is not None:
                    audio = model.generate_audio(text, voice=self.voice)
                    # Save as WAV
                    import soundfile as sf

                    sf.write(str(cache_path), audio, samplerate=24000)
                    logger.info("Narration generated: %s (%d samples)", cache_path.name, len(audio))
                    return {
                        "text": text,
                        "audio_path": str(cache_path),
                        "cached": False,
                        "voice": self.voice,
                        "samples": len(audio),
                    }
            except Exception as e:
                logger.warning("PocketTTS generation failed: %s", e)

        # Fallback: text-only (no audio)
        return {
            "text": text,
            "audio_path": None,
            "cached": False,
            "voice": self.voice,
            "fallback": True,
        }

    def get_all_stage_texts(self) -> dict[str, str]:
        """Return all pre-written stage narration texts."""
        return STAGE_NARRATIONS.copy()

    def get_all_concept_texts(self) -> dict[str, str]:
        """Return all concept narration texts."""
        return CONCEPT_NARRATIONS.copy()


# Singleton
_NARRATOR: CosmoNarrator | None = None


def get_narrator() -> CosmoNarrator:
    """Get or create the singleton narrator."""
    global _NARRATOR
    if _NARRATOR is None:
        _NARRATOR = CosmoNarrator()
    return _NARRATOR


__all__ = [
    "CONCEPT_NARRATIONS",
    "CosmoNarrator",
    "STAGE_NARRATIONS",
    "get_narrator",
]
