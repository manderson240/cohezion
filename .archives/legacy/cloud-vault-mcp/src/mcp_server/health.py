"""Health check module for monitoring MCP dependencies."""

import asyncio
import logging
import shutil
import time
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path

import httpx
import psutil


logger = logging.getLogger(__name__)


@dataclass
class HealthStatus:
    """Overall health status with timestamp and individual check results."""

    status: str  # "healthy", "degraded", "unhealthy"
    timestamp: str
    checks: dict[str, dict]

    def to_dict(self):
        """Convert to dictionary for JSON serialization."""
        return asdict(self)


class HealthChecker:
    """Check health of all MCP dependencies."""

    def __init__(
        self,
        vault_path: str,
        surrealdb_url: str = "http://localhost:8001",
        sheets_bridge=None,
        ollama_url: str = "http://localhost:11434",
        sheets_research_daemon=None,
    ):
        """Initialize health checker with dependency URLs and paths.

        Args:
            vault_path: Path to vault directory
            surrealdb_url: URL for SurrealDB server
            sheets_bridge: Optional SheetsBridge instance for Sheets API testing
            ollama_url: URL for Ollama service
            sheets_research_daemon: Optional SheetsResearchDaemon instance for pipeline monitoring
        """
        self.vault_path = Path(vault_path)
        self.surrealdb_url = surrealdb_url
        self.sheets_bridge = sheets_bridge
        self.ollama_url = ollama_url
        self.sheets_research_daemon = sheets_research_daemon
        self.last_check_time: float | None = None
        self.last_check_result: HealthStatus | None = None
        self.cache_ttl = 60  # Cache results for 60 seconds

    async def check_vault(self) -> dict:
        """Check if vault directory is accessible and writable.

        Returns:
            {status: "ok"|"error", latency_ms: X, path_accessible: bool}
        """
        start = time.time()
        try:
            # Check if path exists and is readable
            if not self.vault_path.exists():
                return {
                    "status": "error",
                    "latency_ms": int((time.time() - start) * 1000),
                    "path_accessible": False,
                    "message": "Vault path does not exist",
                }

            if not self.vault_path.is_dir():
                return {
                    "status": "error",
                    "latency_ms": int((time.time() - start) * 1000),
                    "path_accessible": False,
                    "message": "Vault path is not a directory",
                }

            # Test read access
            list(self.vault_path.iterdir())

            # Test write access with a temporary file
            test_file = self.vault_path / ".health_check_test"
            try:
                test_file.write_text("test")
                test_file.unlink()
                writable = True
            except OSError:
                writable = False

            latency_ms = int((time.time() - start) * 1000)
            return {
                "status": "ok",
                "latency_ms": latency_ms,
                "path_accessible": True,
                "writable": writable,
            }
        except Exception as e:
            latency_ms = int((time.time() - start) * 1000)
            logger.error(f"Vault health check failed: {e}")
            return {
                "status": "error",
                "latency_ms": latency_ms,
                "path_accessible": False,
                "message": str(e),
            }

    async def check_surrealdb(self) -> dict:
        """Test SurrealDB connection and basic query.

        Returns:
            {status: "ok"|"error", latency_ms: X, connected: bool}
        """
        start = time.time()
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{self.surrealdb_url}/health")
                latency_ms = int((time.time() - start) * 1000)

                if response.status_code == 200:
                    return {
                        "status": "ok",
                        "latency_ms": latency_ms,
                        "connected": True,
                    }
                else:
                    return {
                        "status": "error",
                        "latency_ms": latency_ms,
                        "connected": False,
                        "message": f"HTTP {response.status_code}",
                    }
        except httpx.ConnectError as e:
            latency_ms = int((time.time() - start) * 1000)
            logger.error(f"SurrealDB connection failed: {e}")
            return {
                "status": "error",
                "latency_ms": latency_ms,
                "connected": False,
                "message": "Connection refused",
            }
        except httpx.TimeoutException:
            latency_ms = int((time.time() - start) * 1000)
            return {
                "status": "error",
                "latency_ms": latency_ms,
                "connected": False,
                "message": "Connection timeout",
            }
        except Exception as e:
            latency_ms = int((time.time() - start) * 1000)
            logger.error(f"SurrealDB health check failed: {e}")
            return {
                "status": "error",
                "latency_ms": latency_ms,
                "connected": False,
                "message": str(e),
            }

    async def check_sheets_api(self) -> dict:
        """Test Google Sheets API authentication and access.

        Returns:
            {status: "ok"|"error"|"disabled", latency_ms: X, authenticated: bool}
        """
        if not self.sheets_bridge:
            return {
                "status": "disabled",
                "latency_ms": 0,
                "authenticated": False,
                "message": "Sheets Bridge not configured",
            }

        start = time.time()
        try:
            # Try to read the first row to test authentication
            await asyncio.to_thread(self.sheets_bridge.get_all_rows)
            latency_ms = int((time.time() - start) * 1000)
            return {
                "status": "ok",
                "latency_ms": latency_ms,
                "authenticated": True,
            }
        except Exception as e:
            latency_ms = int((time.time() - start) * 1000)
            logger.error(f"Sheets API health check failed: {e}")
            return {
                "status": "error",
                "latency_ms": latency_ms,
                "authenticated": False,
                "message": str(e),
            }

    async def check_ollama(self) -> dict:
        """Test Ollama service and count loaded models.

        Returns:
            {status: "ok"|"error"|"disabled", latency_ms: X, models_loaded: int}
        """
        start = time.time()
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{self.ollama_url}/api/tags")
                latency_ms = int((time.time() - start) * 1000)

                if response.status_code == 200:
                    data = response.json()
                    models = data.get("models", [])
                    return {
                        "status": "ok",
                        "latency_ms": latency_ms,
                        "models_loaded": len(models),
                    }
                else:
                    return {
                        "status": "error",
                        "latency_ms": latency_ms,
                        "models_loaded": 0,
                        "message": f"HTTP {response.status_code}",
                    }
        except httpx.ConnectError:
            latency_ms = int((time.time() - start) * 1000)
            return {
                "status": "error",
                "latency_ms": latency_ms,
                "models_loaded": 0,
                "message": "Connection refused",
            }
        except httpx.TimeoutException:
            latency_ms = int((time.time() - start) * 1000)
            return {
                "status": "error",
                "latency_ms": latency_ms,
                "models_loaded": 0,
                "message": "Connection timeout",
            }
        except Exception as e:
            latency_ms = int((time.time() - start) * 1000)
            logger.error(f"Ollama health check failed: {e}")
            return {
                "status": "error",
                "latency_ms": latency_ms,
                "models_loaded": 0,
                "message": str(e),
            }

    async def check_disk_space(self) -> dict:
        """Check disk space on vault path.

        Returns:
            {status: "ok"|"warning"|"critical", free_gb: X, threshold_gb: Y}
        """
        try:
            usage = shutil.disk_usage(self.vault_path)
            free_gb = usage.free / (1024**3)
            threshold_gb = 10

            if free_gb < threshold_gb:
                return {
                    "status": "critical",
                    "free_gb": round(free_gb, 2),
                    "threshold_gb": threshold_gb,
                    "message": "Disk space critically low",
                }
            elif free_gb < threshold_gb * 2:
                return {
                    "status": "warning",
                    "free_gb": round(free_gb, 2),
                    "threshold_gb": threshold_gb,
                    "message": "Disk space low",
                }
            else:
                return {
                    "status": "ok",
                    "free_gb": round(free_gb, 2),
                    "threshold_gb": threshold_gb,
                }
        except Exception as e:
            logger.error(f"Disk space check failed: {e}")
            return {
                "status": "error",
                "free_gb": 0,
                "threshold_gb": 10,
                "message": str(e),
            }

    async def check_memory(self) -> dict:
        """Check process memory usage.

        Returns:
            {status: "ok"|"warning", memory_percent: X, memory_mb: Y}
        """
        try:
            process = psutil.Process()
            mem_info = process.memory_info()
            memory_mb = mem_info.rss / (1024**2)
            memory_percent = process.memory_percent()

            if memory_percent > 80:
                return {
                    "status": "warning",
                    "memory_percent": round(memory_percent, 2),
                    "memory_mb": round(memory_mb, 2),
                    "message": "Memory usage high",
                }
            else:
                return {
                    "status": "ok",
                    "memory_percent": round(memory_percent, 2),
                    "memory_mb": round(memory_mb, 2),
                }
        except Exception as e:
            logger.error(f"Memory check failed: {e}")
            return {
                "status": "error",
                "memory_percent": 0,
                "memory_mb": 0,
                "message": str(e),
            }

    async def check_sheets_research_pipeline(self) -> dict:
        """Check Sheets research pipeline health.

        Returns:
            {status: "ok"|"warning"|"error"|"disabled", work_queue_size: X, dlq_size: Y, ...}
        """
        if not self.sheets_research_daemon:
            return {
                "status": "disabled",
                "message": "Sheets Research Pipeline not configured",
            }

        try:
            status = self.sheets_research_daemon.get_status()
            dlq_size = status.get("dlq_size", 0)

            # Determine overall status
            check_status = "ok"
            if dlq_size > 50:
                check_status = "warning"
            if dlq_size > 100:
                check_status = "error"

            return {
                "status": check_status,
                "daemon_status": status.get("status", "unknown"),
                "work_queue": status.get("work_queue", {}),
                "dlq_size": dlq_size,
                "rows_processed_today": status.get("rows_processed_today", 0),
            }
        except Exception as e:
            logger.error(f"Sheets research pipeline health check failed: {e}")
            return {
                "status": "error",
                "message": str(e),
            }

    async def run_all_checks(self, timeout: int = 5) -> HealthStatus:
        """Run all checks concurrently and aggregate results.

        Args:
            timeout: Timeout in seconds for all checks to complete

        Returns:
            HealthStatus with aggregated results from all checks
        """
        # Check cache
        if self.last_check_result and self.last_check_time:
            elapsed = time.time() - self.last_check_time
            if elapsed < self.cache_ttl:
                return self.last_check_result

        try:
            # Run all checks concurrently with timeout
            checks_task = asyncio.gather(
                self.check_vault(),
                self.check_surrealdb(),
                self.check_sheets_api(),
                self.check_ollama(),
                self.check_disk_space(),
                self.check_memory(),
                self.check_sheets_research_pipeline(),
                return_exceptions=True,
            )
            results = await asyncio.wait_for(checks_task, timeout=timeout)
        except TimeoutError:
            logger.error("Health check timed out")
            results = [{"status": "error", "message": "Check timed out"}] * 7

        # Extract individual results
        (
            vault_result,
            surrealdb_result,
            sheets_result,
            ollama_result,
            disk_result,
            memory_result,
            sheets_research_result,
        ) = results

        # Handle exceptions
        checks = {
            "vault": vault_result
            if isinstance(vault_result, dict)
            else {"status": "error", "message": str(vault_result)},
            "surrealdb": surrealdb_result
            if isinstance(surrealdb_result, dict)
            else {"status": "error", "message": str(surrealdb_result)},
            "sheets_api": sheets_result
            if isinstance(sheets_result, dict)
            else {"status": "error", "message": str(sheets_result)},
            "ollama": ollama_result
            if isinstance(ollama_result, dict)
            else {"status": "error", "message": str(ollama_result)},
            "disk_space": disk_result
            if isinstance(disk_result, dict)
            else {"status": "error", "message": str(disk_result)},
            "memory": memory_result
            if isinstance(memory_result, dict)
            else {"status": "error", "message": str(memory_result)},
            "sheets_research_pipeline": sheets_research_result
            if isinstance(sheets_research_result, dict)
            else {"status": "error", "message": str(sheets_research_result)},
        }

        # Determine overall status
        overall_status = self._aggregate_status(checks)

        timestamp = datetime.now(UTC).isoformat()
        health_status = HealthStatus(
            status=overall_status,
            timestamp=timestamp,
            checks=checks,
        )

        # Cache result
        self.last_check_result = health_status
        self.last_check_time = time.time()

        return health_status

    @staticmethod
    def _aggregate_status(checks: dict[str, dict]) -> str:
        """Determine overall status from individual checks.

        Rules:
        - If any check has status "error", overall is "unhealthy"
        - If any check has status "warning" or "critical", overall is "degraded"
        - If any check has status "disabled", ignore it
        - Otherwise, overall is "healthy"

        Args:
            checks: Dictionary of check results

        Returns:
            "healthy", "degraded", or "unhealthy"
        """
        has_error = False
        has_warning = False

        for check_result in checks.values():
            status = check_result.get("status", "unknown")
            if status == "error":
                has_error = True
            elif status in ("warning", "critical"):
                has_warning = True

        if has_error:
            return "unhealthy"
        elif has_warning:
            return "degraded"
        else:
            return "healthy"
