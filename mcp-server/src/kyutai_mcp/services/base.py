"""Base service class for all Kyutai services."""

import logging
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, Optional

from ..config import ServiceConfig
from ..utils.errors import ServiceError

logger = logging.getLogger(__name__)


class KyutaiService(ABC):
    """Abstract base class for all Kyutai services."""

    def __init__(self, config: ServiceConfig, service_name: str):
        self.config = config
        self.service_name = service_name
        self.last_error: Optional[str] = None
        self.last_success: Optional[datetime] = None
        self.request_count = 0
        self.error_count = 0
        self.last_latency_ms = 0

    @property
    def is_healthy(self) -> bool:
        """Check if service is operational."""
        if not self.config.enabled:
            return False
        # Consider unhealthy if last 5+ requests failed
        if self.request_count > 0 and self.error_count >= 5:
            return False
        return True

    @property
    def status(self) -> Dict[str, Any]:
        """Get service status for reporting."""
        return {
            "available": self.config.enabled and self.is_healthy,
            "enabled": self.config.enabled,
            "error_count": self.error_count,
            "request_count": self.request_count,
            "error_rate": (
                self.error_count / self.request_count if self.request_count > 0 else 0
            ),
            "last_error": self.last_error,
            "last_success": self.last_success.isoformat() if self.last_success else None,
            "last_latency_ms": self.last_latency_ms,
        }

    @abstractmethod
    async def health_check(self) -> bool:
        """Implement service-specific health check.

        Returns:
            True if service is healthy, False otherwise
        """
        pass

    def record_success(self, latency_ms: int = 0):
        """Record successful request."""
        self.request_count += 1
        self.last_success = datetime.now()
        self.last_latency_ms = latency_ms

    def record_error(self, error: str):
        """Record failed request."""
        self.request_count += 1
        self.error_count += 1
        self.last_error = error
        logger.warning(f"{self.service_name}: {error}")

    def reset_errors(self):
        """Reset error count (called after successful recovery)."""
        self.error_count = 0
