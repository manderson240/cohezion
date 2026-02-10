"""Health monitoring for Kyutai services."""

import asyncio
import logging
from datetime import datetime
from typing import Any, Dict

from .base import KyutaiService

logger = logging.getLogger(__name__)


class HealthMonitor:
    """Monitor health of all Kyutai services."""

    def __init__(self, services: Dict[str, KyutaiService]):
        self.services = services
        self.last_check: Dict[str, bool] = {}
        self.check_history: Dict[str, list[bool]] = {
            name: [] for name in services.keys()
        }

    async def check_all(self) -> Dict[str, Any]:
        """Run health checks on all services.

        Returns:
            Dictionary with overall status and per-service details
        """
        status_dict = {
            "timestamp": datetime.now().isoformat(),
            "services": {},
            "overall_status": "healthy",
        }

        for service_name, service in self.services.items():
            try:
                is_healthy = await service.health_check()
                self.last_check[service_name] = is_healthy

                # Keep history (last 100 checks)
                history = self.check_history[service_name]
                history.append(is_healthy)
                if len(history) > 100:
                    history.pop(0)

                # Calculate uptime percentage
                uptime_percent = (
                    (sum(history) / len(history) * 100) if history else 0
                )

                status_dict["services"][service_name] = {
                    "available": service.config.enabled and is_healthy,
                    "enabled": service.config.enabled,
                    "status": "healthy" if is_healthy else "offline",
                    "uptime_percent": uptime_percent,
                    "request_count": service.request_count,
                    "error_count": service.error_count,
                    "error_rate": (
                        service.error_count / service.request_count
                        if service.request_count > 0
                        else 0
                    ),
                    "last_error": service.last_error,
                    "last_latency_ms": service.last_latency_ms,
                    "last_success": (
                        service.last_success.isoformat()
                        if service.last_success
                        else None
                    ),
                }

                # Update overall status
                if not is_healthy and service.config.enabled:
                    status_dict["overall_status"] = "degraded"

            except Exception as e:
                logger.error(f"Health check failed for {service_name}: {e}")
                status_dict["services"][service_name] = {
                    "available": False,
                    "status": "offline",
                    "error": str(e),
                }
                status_dict["overall_status"] = "degraded"

        return status_dict

    async def start_monitoring(self, interval_seconds: int = 60):
        """Start continuous monitoring loop.

        Args:
            interval_seconds: Interval between health checks
        """
        logger.info(f"Starting health monitoring (interval: {interval_seconds}s)")

        while True:
            try:
                status = await self.check_all()
                logger.debug(f"Health check complete: {status['overall_status']}")

            except Exception as e:
                logger.error(f"Monitoring cycle failed: {e}")

            await asyncio.sleep(interval_seconds)

    def get_status(self) -> Dict[str, Any]:
        """Get last known status without running checks."""
        return {
            "timestamp": datetime.now().isoformat(),
            "services": {
                name: service.status for name, service in self.services.items()
            },
        }
