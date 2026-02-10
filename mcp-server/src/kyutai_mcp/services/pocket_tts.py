"""Pocket TTS Service - Local, CPU-based text-to-speech."""

import asyncio
import logging
import os
import time
from datetime import datetime
from typing import Any, Dict, Optional

from ..config import ServiceConfig
from ..utils.audio import audio_to_base64, get_audio_duration_ms, save_audio_file
from ..utils.errors import ModelError, ServiceError
from .base import KyutaiService

logger = logging.getLogger(__name__)


class PocketTTSService(KyutaiService):
    """Pocket TTS (Phase 1): Local, CPU-based TTS."""

    def __init__(self, config: ServiceConfig):
        super().__init__(config, "PocketTTS")
        self.model = None
        self.voices: Dict[str, Any] = {}
        self.sample_rate = 24000  # Pocket TTS sample rate
        self._init_model()

    def _init_model(self):
        """Load Pocket TTS model on init."""
        try:
            from pocket_tts import TTSModel

            logger.info(f"Loading Pocket TTS model with config: {self.config.default_model}")
            self.model = TTSModel.load_model(config=self.config.default_model)
            self.last_success = datetime.now()
            logger.info("Pocket TTS model loaded successfully")
        except ImportError:
            error = "pocket_tts package not installed. Install with: pip install pocket-tts"
            self.last_error = error
            logger.error(error)
            raise ServiceError(error)
        except Exception as e:
            self.last_error = str(e)
            logger.error(f"Failed to load Pocket TTS model: {e}")
            raise ServiceError(f"Failed to load Pocket TTS model: {e}")

    def _load_voice_sample(self, voice_path: str) -> Optional[str]:
        """Load and validate voice sample file."""
        if not os.path.exists(voice_path):
            logger.warning(f"Voice sample not found: {voice_path}")
            return None

        try:
            from pocket_tts import TTSModel

            # Load voice state from audio file
            voice_state = self.model.get_state_for_audio_prompt(voice_path)
            logger.debug(f"Loaded voice sample: {voice_path}")
            return voice_state
        except Exception as e:
            logger.warning(f"Failed to load voice sample {voice_path}: {e}")
            return None

    def set_voice(
        self,
        voice_name: str,
        audio_sample_path: str,
        description: str = "",
        language: str = "en",
    ) -> Dict[str, Any]:
        """Register a voice from an audio sample.

        Args:
            voice_name: Identifier for this voice
            audio_sample_path: Path to reference audio file
            description: Human-readable description
            language: Language hint (en, fr, etc.)

        Returns:
            Dictionary with voice configuration
        """
        try:
            # Validate file exists
            if not os.path.exists(audio_sample_path):
                return {
                    "status": "error",
                    "error": f"Audio file not found: {audio_sample_path}",
                }

            # Load and validate voice
            voice_state = self._load_voice_sample(audio_sample_path)
            if voice_state is None:
                return {
                    "status": "error",
                    "error": f"Failed to load voice sample: {audio_sample_path}",
                }

            # Store voice reference
            self.voices[voice_name] = {
                "path": audio_sample_path,
                "state": voice_state,
                "description": description,
                "language": language,
            }

            return {
                "status": "success",
                "voice_id": voice_name,
                "voice_name": voice_name,
                "language": language,
                "storage_path": audio_sample_path,
                "available_for": ["pocket-tts"],
            }

        except Exception as e:
            error_msg = f"Failed to set voice: {e}"
            self.record_error(error_msg)
            return {"status": "error", "error": error_msg}

    async def speak(
        self,
        text: str,
        voice_id: str = "default",
        speed: float = 1.0,
        output_format: str = "wav",
    ) -> Dict[str, Any]:
        """Generate audio from text.

        Args:
            text: Text to synthesize (1-4096 chars)
            voice_id: Voice sample ID (default: "default")
            speed: Playback speed (0.5-2.0, default: 1.0)
            output_format: Audio format (wav, mp3, ogg)

        Returns:
            Dictionary with audio path and metadata
        """
        try:
            start_time = time.time()

            # Validate input
            if len(text) > 4096:
                error = f"Text too long ({len(text)}/4096 chars). Please split into smaller chunks."
                self.record_error(error)
                return {"status": "error", "error": error}

            if not text.strip():
                error = "Text cannot be empty"
                self.record_error(error)
                return {"status": "error", "error": error}

            # Get voice state
            if voice_id not in self.voices:
                if voice_id != "default":
                    logger.warning(f"Voice not found: {voice_id}. Using default.")
                voice_id = "default"

            # For now, generate without voice cloning (Phase 1 MVP)
            # Phase 2 will add voice cloning support
            logger.debug(f"Generating audio for text (length: {len(text)}) with voice: {voice_id}")

            # Generate audio using Pocket TTS
            # Note: This is a synchronous operation, so we run it in executor
            audio_tensor = await asyncio.to_thread(
                self.model.generate_audio, text=text
            )

            # Convert tensor to bytes if needed
            if hasattr(audio_tensor, "numpy"):
                audio_data = audio_tensor.numpy().astype("int16").tobytes()
            else:
                audio_data = audio_tensor.tobytes() if hasattr(audio_tensor, "tobytes") else audio_tensor

            # Save audio file
            audio_path = save_audio_file(audio_data, output_format)
            duration_ms = get_audio_duration_ms(audio_data, self.sample_rate)

            # Try to generate base64 for Obsidian playback
            try:
                audio_base64 = audio_to_base64(audio_path)
            except Exception as e:
                logger.warning(f"Failed to generate base64: {e}")
                audio_base64 = None

            latency_ms = int((time.time() - start_time) * 1000)
            self.record_success(latency_ms)

            result = {
                "status": "success",
                "audio_path": audio_path,
                "duration_ms": duration_ms,
                "model_used": "pocket-tts",
                "latency_ms": latency_ms,
                "voice_id": voice_id,
                "text_length": len(text),
            }

            if audio_base64:
                result["audio_base64"] = audio_base64

            return result

        except Exception as e:
            error_msg = f"Failed to generate audio: {e}"
            self.record_error(error_msg)
            return {
                "status": "error",
                "error": error_msg,
                "error_type": type(e).__name__,
            }

    async def health_check(self) -> bool:
        """Check if Pocket TTS is responsive."""
        try:
            # Quick inference test with minimal text
            test_text = "test"
            logger.debug("Running Pocket TTS health check...")

            audio_tensor = await asyncio.to_thread(
                self.model.generate_audio, text=test_text
            )

            is_healthy = audio_tensor is not None and len(str(audio_tensor)) > 0
            if is_healthy:
                logger.debug("Pocket TTS health check passed")
            return is_healthy
        except Exception as e:
            logger.warning(f"Pocket TTS health check failed: {e}")
            self.last_error = str(e)
            return False

    def get_model_info(self) -> Dict[str, Any]:
        """Get detailed model information."""
        return {
            "id": "pocket-tts",
            "name": "Pocket TTS",
            "category": "tts",
            "parameters": 100_000_000,  # ~100M parameters
            "model_size_gb": 0.5,
            "languages": ["en", "fr", "es", "de", "ja", "zh"],
            "input_modality": ["text"],
            "output_modality": ["audio"],
            "local_available": True,
            "hardware_required": "cpu",
            "deployment_pattern": "local-cpu",
            "latency_ms": 100,  # Estimated
            "max_concurrent": 1,  # CPU-bound, single inference
            "config_required": False,
        }
