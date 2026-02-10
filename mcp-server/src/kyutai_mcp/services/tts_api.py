"""TTS API Service - High-quality text-to-speech via OpenAI-compatible API (Phase 2+)."""

import logging
from typing import Any, Dict, Optional

from ..config import ServiceConfig
from ..utils.errors import ServiceError
from .base import KyutaiService

logger = logging.getLogger(__name__)


class TTSAPIService(KyutaiService):
    """TTS via OpenAI-compatible API (Phase 2+)."""

    def __init__(self, config: ServiceConfig):
        super().__init__(config, "TTS API")
        self.client = None
        if config.enabled:
            self._init_client()

    def _init_client(self):
        """Initialize OpenAI client for TTS API."""
        try:
            from openai import OpenAI

            logger.info(f"Initializing TTS API client for {self.config.url}")
            self.client = OpenAI(
                base_url=self.config.url,
                api_key=self.config.api_key or "dummy-key",
            )
            logger.info("TTS API client initialized")
        except ImportError:
            error = "openai package not installed. Install with: pip install openai"
            logger.error(error)
        except Exception as e:
            error = f"Failed to initialize TTS API client: {e}"
            self.last_error = error
            logger.error(error)

    async def speak(
        self,
        text: str,
        voice_id: str = "default",
        output_format: str = "wav",
    ) -> Dict[str, Any]:
        """Generate audio from text via TTS API.

        Args:
            text: Text to synthesize
            voice_id: Voice ID to use
            output_format: Audio format (wav, mp3, ogg)

        Returns:
            Dictionary with audio path and metadata
        """
        if not self.config.enabled:
            return {"status": "error", "error": "TTS API is not enabled"}

        if self.client is None:
            return {"status": "error", "error": "TTS API client not initialized"}

        try:
            import time
            from ..utils.audio import save_audio_file, get_audio_duration_ms

            start_time = time.time()

            # Validate input
            if len(text) > 4096:
                error = f"Text too long ({len(text)}/4096 chars)"
                self.record_error(error)
                return {"status": "error", "error": error}

            # Call TTS API
            response = self.client.audio.speech.create(
                model=self.config.default_model,
                text=text,
                voice=voice_id,
                response_format="wav" if output_format == "wav" else output_format,
            )

            # Save audio
            audio_path = save_audio_file(response.content, output_format)
            duration_ms = get_audio_duration_ms(response.content)

            latency_ms = int((time.time() - start_time) * 1000)
            self.record_success(latency_ms)

            return {
                "status": "success",
                "audio_path": audio_path,
                "duration_ms": duration_ms,
                "model_used": self.config.default_model,
                "latency_ms": latency_ms,
                "voice_id": voice_id,
            }

        except Exception as e:
            error_msg = f"TTS generation failed: {e}"
            self.record_error(error_msg)
            return {"status": "error", "error": error_msg}

    async def health_check(self) -> bool:
        """Check if TTS API is responsive."""
        if not self.config.enabled or self.client is None:
            return False

        try:
            logger.debug("Running TTS API health check...")
            models = self.client.models.list()
            is_healthy = len(models.data) > 0
            logger.debug(f"TTS API health check: {'passed' if is_healthy else 'failed'}")
            return is_healthy
        except Exception as e:
            logger.warning(f"TTS API health check failed: {e}")
            self.last_error = str(e)
            return False

    def get_model_info(self) -> Dict[str, Any]:
        """Get detailed model information."""
        return {
            "id": "tts-api",
            "name": "TTS API (OpenAI-compatible)",
            "category": "tts",
            "parameters": 1_600_000_000,  # ~1.6B parameters
            "model_size_gb": 3.0,
            "languages": ["en", "fr", "es", "de", "ja", "zh"],
            "input_modality": ["text"],
            "output_modality": ["audio"],
            "local_available": False,  # Requires separate API service
            "hardware_required": "gpu",
            "deployment_pattern": "api",
            "latency_ms": 200,  # Estimated
            "max_concurrent": 10,
            "config_required": True,  # Requires API URL
        }
