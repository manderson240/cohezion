"""Pocket TTS integration for text-to-speech synthesis.

This module provides text-to-speech synthesis using the Pocket TTS model
(100M parameter lightweight model). Follows the token-efficient pattern:
implementation first, then validation, then tests.
"""

import base64
import io
import logging
from typing import Any


logger = logging.getLogger(__name__)


class PocketTTSService:
    """Text-to-speech synthesis using Pocket TTS (100M param model)."""

    def __init__(self) -> None:
        """Initialize service with lazy loading."""
        self.model = None
        self.sample_rate = 24000
        self._initialized = False

    def initialize(self) -> None:
        """Load TTS model on first use (lazy initialization).

        Raises:
            RuntimeError: If pocket-tts not installed or model load fails
        """
        if self._initialized:
            return

        try:
            from pocket_tts import TTSModel

            self.model = TTSModel.load_model(
                config="b6369a24", temp=0.7, eos_threshold=-4.0
            )
            self.sample_rate = self.model.sample_rate
            self._initialized = True
            logger.info("Pocket TTS model loaded on %s", self.model.device)

        except ImportError as e:
            raise RuntimeError(
                "pocket-tts not installed: pip install pocket-tts"
            ) from e
        except Exception as e:
            raise RuntimeError(f"Failed to load TTS model: {e}") from e

    def speak(self, text: str) -> dict[str, Any]:
        """Synthesize text to speech.

        Args:
            text: Text to synthesize (max 4096 chars)

        Returns:
            Dictionary with:
            - status: "success" or "error"
            - audio_base64: Base64-encoded WAV audio (if success)
            - duration_ms: Audio duration in milliseconds (if success)
            - sample_rate: Sample rate in Hz (if success)
            - model: Model identifier (if success)
            - error: Error message (if error)
        """
        # Validate input first (before expensive model initialization)
        if not text or not text.strip():
            return {"status": "error", "error": "Text cannot be empty"}

        if len(text) > 4096:
            return {"status": "error", "error": "Text too long (max 4096 chars)"}

        # Initialize on first use
        if not self._initialized:
            try:
                self.initialize()
            except RuntimeError as e:
                return {"status": "error", "error": str(e)}

        try:
            import torch
            import torchaudio

            # Get default voice state (no voice cloning for MVP)
            # Using 1 second of random noise as default voice prompt
            voice_state = self.model.get_state_for_audio_prompt(torch.randn(24000))

            # Generate audio
            audio_tensor = self.model.generate_audio(voice_state, text, copy_state=True)

            # Convert to WAV bytes
            buffer = io.BytesIO()
            torchaudio.save(
                buffer,
                audio_tensor.unsqueeze(0),  # Add batch dimension
                self.sample_rate,
                format="wav",
            )
            audio_bytes = buffer.getvalue()

            # Calculate duration
            duration_ms = int(len(audio_tensor) / self.sample_rate * 1000)

            return {
                "status": "success",
                "audio_base64": base64.b64encode(audio_bytes).decode(),
                "duration_ms": duration_ms,
                "sample_rate": self.sample_rate,
                "model": "pocket-tts",
            }

        except Exception as e:
            logger.error("TTS synthesis failed: %s", e)
            return {"status": "error", "error": str(e)}
