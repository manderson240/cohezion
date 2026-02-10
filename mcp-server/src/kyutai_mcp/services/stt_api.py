"""STT API Service - Speech-to-Text via OpenAI-compatible API (Phase 2+)."""

import logging
from typing import Any, Dict, Optional

from ..config import ServiceConfig
from ..utils.errors import ServiceError
from .base import KyutaiService

logger = logging.getLogger(__name__)


class STTAPIService(KyutaiService):
    """STT via OpenAI-compatible API (Phase 2+)."""

    def __init__(self, config: ServiceConfig):
        super().__init__(config, "STT API")
        self.client = None
        if config.enabled:
            self._init_client()

    def _init_client(self):
        """Initialize OpenAI client for STT API."""
        try:
            from openai import OpenAI

            logger.info(f"Initializing STT API client for {self.config.url}")
            self.client = OpenAI(
                base_url=self.config.url,
                api_key=self.config.api_key or "dummy-key",
            )
            logger.info("STT API client initialized")
        except ImportError:
            error = "openai package not installed. Install with: pip install openai"
            logger.error(error)
        except Exception as e:
            error = f"Failed to initialize STT API client: {e}"
            self.last_error = error
            logger.error(error)

    async def transcribe(self, audio_path: str, language: Optional[str] = None) -> Dict[str, Any]:
        """Transcribe audio to text.

        Args:
            audio_path: Path to audio file
            language: Language hint (en, fr, etc.)

        Returns:
            Dictionary with transcription result
        """
        if not self.config.enabled:
            return {"status": "error", "error": "STT API is not enabled"}

        if self.client is None:
            return {"status": "error", "error": "STT API client not initialized"}

        try:
            import os
            import time

            start_time = time.time()

            if not os.path.exists(audio_path):
                error = f"Audio file not found: {audio_path}"
                self.record_error(error)
                return {"status": "error", "error": error}

            with open(audio_path, "rb") as f:
                result = self.client.audio.transcriptions.create(
                    model=self.config.default_model,
                    file=f,
                    response_format="json",
                    language=language,
                )

            latency_ms = int((time.time() - start_time) * 1000)
            self.record_success(latency_ms)

            return {
                "status": "success",
                "text": result.text,
                "segments": getattr(result, "segments", []),
                "language": language or "auto",
                "model_used": self.config.default_model,
                "latency_ms": latency_ms,
            }
        except Exception as e:
            error_msg = f"Transcription failed: {e}"
            self.record_error(error_msg)
            return {"status": "error", "error": error_msg}

    async def health_check(self) -> bool:
        """Check if STT API is responsive."""
        if not self.config.enabled or self.client is None:
            return False

        try:
            logger.debug("Running STT API health check...")
            models = self.client.models.list()
            is_healthy = len(models.data) > 0
            logger.debug(f"STT API health check: {'passed' if is_healthy else 'failed'}")
            return is_healthy
        except Exception as e:
            logger.warning(f"STT API health check failed: {e}")
            self.last_error = str(e)
            return False

    def get_model_info(self) -> Dict[str, Any]:
        """Get detailed model information."""
        return {
            "id": "stt-api",
            "name": "STT API (OpenAI-compatible)",
            "category": "stt",
            "parameters": 1_000_000_000,  # ~1B parameters
            "model_size_gb": 2.0,
            "languages": ["en", "fr", "es", "de", "ja", "zh", "auto"],
            "input_modality": ["audio"],
            "output_modality": ["text"],
            "local_available": False,  # Requires separate API service
            "hardware_required": "gpu",
            "deployment_pattern": "api",
            "latency_ms": 500,  # Estimated with network
            "max_concurrent": 10,
            "config_required": True,  # Requires API URL
        }
