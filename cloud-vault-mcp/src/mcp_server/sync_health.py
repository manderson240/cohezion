"""
Health check endpoints for sync daemon monitoring.

Provides HTTP endpoints for daemon health, metrics, and status checks.
"""

from typing import Dict, Any, Optional
from datetime import datetime
from pydantic import BaseModel
from fastapi import FastAPI, HTTPException, status
from fastapi.responses import JSONResponse
import logging

logger = logging.getLogger(__name__)


class HealthStatus(BaseModel):
    """Health check response model."""
    status: str  # "healthy", "degraded", "unhealthy"
    timestamp: str
    uptime_seconds: float
    checks: Dict[str, Any]


class MetricsResponse(BaseModel):
    """Metrics response model."""
    daemon_stats: Dict[str, Any]
    queue_stats: Dict[str, Any]
    entire_api_health: Dict[str, Any]
    timestamp: str


def create_health_app(
    daemon_getter: callable,
    queue_getter: callable,
    entire_client_getter: callable
) -> FastAPI:
    """
    Create FastAPI app with health check endpoints.

    Args:
        daemon_getter: Function that returns SyncDaemon instance
        queue_getter: Function that returns WorkQueue instance
        entire_client_getter: Function that returns EntireOpsClient instance

    Returns:
        FastAPI application with health endpoints
    """
    app = FastAPI(title="Sync Daemon Health API", version="1.0.0")

    @app.get("/health", response_model=HealthStatus)
    async def health_check():
        """
        Overall health check endpoint.

        Returns 200 if healthy, 503 if degraded/unhealthy.
        """
        try:
            daemon = daemon_getter()
            queue = queue_getter()
            entire_client = entire_client_getter()

            # Collect health checks
            checks = {}

            # Daemon health
            daemon_running = daemon.is_running() if daemon else False
            checks["daemon_running"] = daemon_running

            # Queue health
            if queue:
                queue_stats = queue.get_stats()
                queue_healthy = (
                    queue_stats["running"] and
                    queue_stats["queue_size"] < queue.max_queue_size * 0.9
                )
                checks["queue_healthy"] = queue_healthy
                checks["queue_size"] = queue_stats["queue_size"]
                checks["queue_in_progress"] = queue_stats["in_progress"]
            else:
                checks["queue_healthy"] = False

            # Entire.io API health
            if entire_client:
                api_health = await entire_client.health_check()
                checks["entire_api_healthy"] = api_health["status"] == "healthy"
                checks["entire_api_latency_ms"] = api_health["latency_ms"]
            else:
                checks["entire_api_healthy"] = False

            # Determine overall status
            if all([
                daemon_running,
                checks.get("queue_healthy", False),
                checks.get("entire_api_healthy", False)
            ]):
                overall_status = "healthy"
                status_code = status.HTTP_200_OK
            elif daemon_running:
                overall_status = "degraded"
                status_code = status.HTTP_200_OK
            else:
                overall_status = "unhealthy"
                status_code = status.HTTP_503_SERVICE_UNAVAILABLE

            # Calculate uptime
            uptime = 0.0
            if daemon and daemon._start_time:
                uptime = (datetime.utcnow() - daemon._start_time).total_seconds()

            response = HealthStatus(
                status=overall_status,
                timestamp=datetime.utcnow().isoformat() + "Z",
                uptime_seconds=uptime,
                checks=checks
            )

            return JSONResponse(
                status_code=status_code,
                content=response.model_dump()
            )

        except Exception as e:
            logger.error(f"Health check error: {e}", exc_info=True)
            return JSONResponse(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                content={
                    "status": "unhealthy",
                    "timestamp": datetime.utcnow().isoformat() + "Z",
                    "error": str(e)
                }
            )

    @app.get("/metrics", response_model=MetricsResponse)
    async def get_metrics():
        """
        Get detailed daemon metrics.

        Returns metrics for daemon, queue, and entire.io API.
        """
        try:
            daemon = daemon_getter()
            queue = queue_getter()
            entire_client = entire_client_getter()

            # Collect metrics
            daemon_stats = daemon.get_stats().model_dump() if daemon else {}
            queue_stats = queue.get_stats() if queue else {}
            api_health = await entire_client.health_check() if entire_client else {}

            return MetricsResponse(
                daemon_stats=daemon_stats,
                queue_stats=queue_stats,
                entire_api_health=api_health,
                timestamp=datetime.utcnow().isoformat() + "Z"
            )

        except Exception as e:
            logger.error(f"Metrics error: {e}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=str(e)
            )

    @app.get("/ready")
    async def readiness_check():
        """
        Readiness check for Kubernetes/load balancers.

        Returns 200 if ready to accept traffic, 503 otherwise.
        """
        try:
            daemon = daemon_getter()
            queue = queue_getter()

            if daemon and daemon.is_running() and queue and queue.is_running():
                return {"ready": True, "timestamp": datetime.utcnow().isoformat() + "Z"}
            else:
                return JSONResponse(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    content={"ready": False, "timestamp": datetime.utcnow().isoformat() + "Z"}
                )

        except Exception as e:
            logger.error(f"Readiness check error: {e}", exc_info=True)
            return JSONResponse(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                content={"ready": False, "error": str(e)}
            )

    @app.get("/live")
    async def liveness_check():
        """
        Liveness check for Kubernetes.

        Returns 200 if process is alive, 503 if it should be restarted.
        """
        return {"alive": True, "timestamp": datetime.utcnow().isoformat() + "Z"}

    return app


def run_health_server(
    daemon_getter: callable,
    queue_getter: callable,
    entire_client_getter: callable,
    host: str = "127.0.0.1",
    port: int = 8361
):
    """
    Run health check HTTP server.

    Args:
        daemon_getter: Function that returns SyncDaemon instance
        queue_getter: Function that returns WorkQueue instance
        entire_client_getter: Function that returns EntireOpsClient instance
        host: Server host (default: localhost)
        port: Server port (default: 8361)
    """
    import uvicorn

    app = create_health_app(daemon_getter, queue_getter, entire_client_getter)

    logger.info(f"Starting health check server on {host}:{port}")

    uvicorn.run(
        app,
        host=host,
        port=port,
        log_level="info"
    )
