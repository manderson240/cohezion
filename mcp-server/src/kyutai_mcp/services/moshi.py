"""Moshi Service - Full-duplex dialogue (Phase 3+)."""

import logging
from typing import Any, Dict

from ..config import ServiceConfig
from .base import KyutaiService

logger = logging.getLogger(__name__)


class MoshiService(KyutaiService):
    """Moshi (Phase 3+): Full-duplex conversational AI."""

    def __init__(self, config: ServiceConfig):
        super().__init__(config, "Moshi")
        logger.info("Moshi service initialized (Phase 3 stub)")

    async def health_check(self) -> bool:
        """Check if Moshi is responsive."""
        if not self.config.enabled:
            return False

        logger.debug("Moshi health check (Phase 3 stub)")
        return False  # Not implemented yet

    def get_model_info(self) -> Dict[str, Any]:
        """Get detailed model information."""
        return {
            "id": "moshi",
            "name": "Moshi",
            "category": "dialogue",
            "parameters": 7_000_000_000,  # ~7B parameters
            "model_size_gb": 14.0,
            "languages": ["en", "fr"],
            "input_modality": ["audio", "text"],
            "output_modality": ["audio", "text"],
            "local_available": False,  # Requires GPU + separate service
            "hardware_required": "gpu",
            "deployment_pattern": "websocket",
            "latency_ms": 200,  # Real-time capable
            "max_concurrent": 4,  # GPU-bound
            "config_required": True,  # Requires WebSocket URL
        }
