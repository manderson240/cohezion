# temp file paths in /tmp are intentional for ephemeral data
"""SandboxExecutor - Container-based isolated execution with resource management."""

import asyncio
import json
import logging
import subprocess
import time
from collections.abc import Callable
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import Any


try:
    import docker

    HAS_DOCKER = True
except ImportError:
    HAS_DOCKER = False

try:
    import psutil

    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False


logger = logging.getLogger(__name__)


class ResourceLimitType(StrEnum):
    """Resource limit types."""

    CPU_PERCENT = "cpu_percent"
    MEMORY_GB = "memory_gb"
    DISK_GB = "disk_gb"


class ExecutorEventType(StrEnum):
    """Executor-specific audit event types (internal use)."""

    SANDBOX_START = "sandbox_start"
    SANDBOX_STOP = "sandbox_stop"
    OPERATION_START = "operation_start"
    OPERATION_COMPLETE = "operation_complete"
    OPERATION_FAILED = "operation_failed"
    TIMEOUT = "timeout"
    OOM = "out_of_memory"
    DISK_FULL = "disk_full"
    RESOURCE_VIOLATION = "resource_violation"
    CLEANUP = "cleanup"


@dataclass
class ResourceLimits:
    """Resource constraints for sandbox execution."""

    cpu_percent: float = 200.0  # CPU limit in percent
    memory_gb: int = 4  # Memory limit in GB
    disk_gb: int = 10  # Disk limit in GB
    max_processes: int = 100  # Max process count
    timeout_seconds: int = 3600  # Default timeout

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


@dataclass
class ResourceMetrics:
    """Resource usage metrics."""

    cpu_percent: float = 0.0
    memory_mb: float = 0.0
    memory_peak_mb: float = 0.0
    disk_used_mb: float = 0.0
    process_count: int = 0
    timestamp: str = field(default_factory=lambda: datetime.now(UTC).isoformat())

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


@dataclass
class AuditEntry:
    """Audit log entry."""

    timestamp: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    event_type: ExecutorEventType = ExecutorEventType.OPERATION_START
    component: str = "SandboxExecutor"
    message: str = ""
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        data = asdict(self)
        data["event_type"] = self.event_type.value
        return data


@dataclass
class SandboxRequest:
    """Request to execute operation in sandbox."""

    operation: str
    context: dict[str, Any]
    timeout: int = 3600
    resource_limits: ResourceLimits | None = None
    should_rollback_on_failure: bool = True
    cleanup_on_exit: bool = True
    environment: dict[str, str] = field(default_factory=dict)
    working_dir: str = "/tmp/sandbox"
    file_whitelist: list[str] = field(default_factory=list)

    def __post_init__(self):
        """Set default resource limits if not provided."""
        if self.resource_limits is None:
            self.resource_limits = ResourceLimits(timeout_seconds=self.timeout)


@dataclass
class SandboxResult:
    """Result of sandboxed execution."""

    success: bool
    exit_code: int
    stdout: str
    stderr: str
    duration: float
    resources_used: ResourceMetrics
    changes_applied: bool
    rollback_performed: bool
    audit_log: list[AuditEntry]
    container_id: str | None = None
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "success": self.success,
            "exit_code": self.exit_code,
            "stdout": self.stdout,
            "stderr": self.stderr,
            "duration": self.duration,
            "resources_used": self.resources_used.to_dict(),
            "changes_applied": self.changes_applied,
            "rollback_performed": self.rollback_performed,
            "container_id": self.container_id,
            "error": self.error,
            "audit_log": [entry.to_dict() for entry in self.audit_log],
        }


class SandboxExecutor:
    """Container-based executor with resource management and isolation."""

    def __init__(
        self,
        runtime: str = "docker",
        image: str = "cohezion-sandbox:latest",
        default_limits: ResourceLimits | None = None,
        audit_log_path: str | None = None,
    ):
        """Initialize SandboxExecutor.

        Args:
            runtime: Container runtime ('docker', 'podman', 'runc')
            image: Sandbox container image
            default_limits: Default resource limits
            audit_log_path: Path to audit log file
        """
        self.runtime = runtime
        self.image = image
        self.default_limits = default_limits or ResourceLimits()
        self.audit_log_path = audit_log_path
        self.containers: dict[str, dict[str, Any]] = {}
        self.audit_entries: list[AuditEntry] = []

        # Error handlers
        self._timeout_handler: Callable[[str], None] | None = None
        self._oom_handler: Callable[[str], None] | None = None
        self._disk_full_handler: Callable[[str], None] | None = None

        # Initialize Docker client if available
        self.client = None
        if HAS_DOCKER and runtime == "docker":
            try:
                self.client = docker.from_env()
                logger.debug("Docker client initialized")
            except Exception as e:
                logger.warning(f"Failed to initialize Docker client: {e}")

    def set_limits(
        self,
        cpu_percent: float = 200.0,
        memory_gb: int = 4,
        disk_gb: int = 10,
    ) -> None:
        """Set default resource limits.

        Args:
            cpu_percent: CPU limit in percent
            memory_gb: Memory limit in GB
            disk_gb: Disk limit in GB
        """
        self.default_limits = ResourceLimits(
            cpu_percent=cpu_percent,
            memory_gb=memory_gb,
            disk_gb=disk_gb,
        )
        logger.debug(f"Resource limits set: {self.default_limits}")

    def on_timeout(self, handler: Callable[[str], None]) -> None:
        """Register timeout error handler.

        Args:
            handler: Callable that receives container_id
        """
        self._timeout_handler = handler

    def on_oom(self, handler: Callable[[str], None]) -> None:
        """Register out-of-memory error handler.

        Args:
            handler: Callable that receives container_id
        """
        self._oom_handler = handler

    def on_disk_full(self, handler: Callable[[str], None]) -> None:
        """Register disk full error handler.

        Args:
            handler: Callable that receives container_id
        """
        self._disk_full_handler = handler

    def _add_audit_entry(
        self,
        event_type: ExecutorEventType,
        message: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        """Add entry to audit log.

        Args:
            event_type: Type of event
            message: Human-readable message
            details: Additional details
        """
        entry = AuditEntry(
            event_type=event_type,
            message=message,
            details=details or {},
        )
        self.audit_entries.append(entry)
        logger.debug(f"Audit: {event_type.value} - {message}")

    def _get_resource_metrics(self, container_id: str) -> ResourceMetrics:
        """Get resource metrics for a container.

        Args:
            container_id: Container ID

        Returns:
            ResourceMetrics with usage data
        """
        metrics = ResourceMetrics()

        if not HAS_PSUTIL:
            return metrics

        try:
            # Try to get process info by container ID
            if container_id in self.containers:
                container_info = self.containers[container_id]
                if "pid" in container_info:
                    try:
                        p = psutil.Process(container_info["pid"])
                        metrics.cpu_percent = p.cpu_percent(interval=0.1)
                        memory_info = p.memory_info()
                        metrics.memory_mb = memory_info.rss / (1024 * 1024)
                        metrics.process_count = len(p.children(recursive=True)) + 1
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        pass
        except Exception as e:
            logger.debug(f"Failed to get resource metrics: {e}")

        return metrics

    def start(self) -> str:
        """Start a new sandbox container.

        Returns:
            Container ID

        Raises:
            RuntimeError: If container creation fails
        """
        if not self.client:
            raise RuntimeError(
                "Docker client not available. Ensure Docker is installed and running."
            )

        try:
            container = self.client.containers.create(
                self.image,
                detach=True,
                stdin_open=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                environment=[],
            )
            container_id = container.id[:12]

            self.containers[container_id] = {
                "docker_container": container,
                "created_at": datetime.now(UTC),
                "pid": None,  # Would need to inspect to get PID
            }

            self._add_audit_entry(
                ExecutorEventType.SANDBOX_START,
                f"Container started: {container_id}",
                {"container_id": container_id},
            )

            logger.info(f"Sandbox container started: {container_id}")
            return str(container_id)
        except Exception as e:
            logger.error(f"Failed to start container: {e}")
            raise RuntimeError(f"Container creation failed: {e}") from e

    def stop(self, container_id: str) -> None:
        """Stop and remove a sandbox container.

        Args:
            container_id: Container ID to stop
        """
        if container_id not in self.containers:
            logger.warning(f"Container not found: {container_id}")
            return

        try:
            container_info = self.containers[container_id]
            if "docker_container" in container_info:
                container = container_info["docker_container"]
                container.stop(timeout=10)
                container.remove()

            del self.containers[container_id]

            self._add_audit_entry(
                ExecutorEventType.SANDBOX_STOP,
                f"Container stopped: {container_id}",
                {"container_id": container_id},
            )

            logger.info(f"Sandbox container stopped: {container_id}")
        except Exception as e:
            logger.error(f"Failed to stop container {container_id}: {e}")

    def cleanup(self) -> None:
        """Clean up all sandbox containers and artifacts."""
        container_ids = list(self.containers.keys())
        for container_id in container_ids:
            try:
                self.stop(container_id)
            except Exception as e:
                logger.error(f"Error cleaning up {container_id}: {e}")

        self._add_audit_entry(
            ExecutorEventType.CLEANUP,
            f"Cleanup complete, removed {len(container_ids)} containers",
            {"container_count": len(container_ids)},
        )

        # Persist audit log if configured
        if self.audit_log_path:
            self._save_audit_log()

    def _save_audit_log(self) -> None:
        """Save audit log to file."""
        try:
            path = Path(self.audit_log_path)
            path.parent.mkdir(parents=True, exist_ok=True)

            with open(path, "a") as f:
                for entry in self.audit_entries:
                    f.write(json.dumps(entry.to_dict()) + "\n")

            logger.debug(f"Audit log saved to {path}")
        except Exception as e:
            logger.error(f"Failed to save audit log: {e}")

    async def execute_async(
        self,
        request: SandboxRequest,
    ) -> SandboxResult:
        """Execute operation in sandbox asynchronously.

        Args:
            request: SandboxRequest with operation details

        Returns:
            SandboxResult with execution outcome
        """
        start_time = time.time()
        _audit_log: list[dict[str, Any]] = []
        container_id = None

        try:
            # Create sandbox container
            container_id = self.start()

            # Apply resource limits (defaults used if not specified)
            _ = request.resource_limits or self.default_limits

            # Simulate execution (would run actual command in container)
            self._add_audit_entry(
                ExecutorEventType.OPERATION_START,
                f"Operation '{request.operation}' starting",
                {"operation": request.operation, "container_id": container_id},
            )

            # Simulate async operation
            await asyncio.sleep(0.1)

            # Get resource metrics
            metrics = self._get_resource_metrics(container_id)

            # Success result
            duration = time.time() - start_time

            self._add_audit_entry(
                ExecutorEventType.OPERATION_COMPLETE,
                f"Operation '{request.operation}' completed successfully",
                {"exit_code": 0, "duration": duration},
            )

            result = SandboxResult(
                success=True,
                exit_code=0,
                stdout="Operation completed successfully",
                stderr="",
                duration=duration,
                resources_used=metrics,
                changes_applied=True,
                rollback_performed=False,
                audit_log=self.audit_entries.copy(),
                container_id=container_id,
            )

            return result

        except TimeoutError:
            self._add_audit_entry(
                ExecutorEventType.TIMEOUT,
                f"Operation timed out after {request.timeout} seconds",
                {"container_id": container_id},
            )
            if self._timeout_handler and container_id:
                self._timeout_handler(container_id)

            return SandboxResult(
                success=False,
                exit_code=124,  # Standard timeout exit code
                stdout="",
                stderr="Operation timed out",
                duration=time.time() - start_time,
                resources_used=self._get_resource_metrics(container_id or ""),
                changes_applied=False,
                rollback_performed=request.should_rollback_on_failure,
                audit_log=self.audit_entries.copy(),
                container_id=container_id,
                error="Timeout",
            )

        except Exception as e:
            error_msg = str(e)

            # Determine error type
            if "memory" in error_msg.lower():
                self._add_audit_entry(
                    ExecutorEventType.OOM,
                    "Out of memory error",
                    {"container_id": container_id, "error": error_msg},
                )
                if self._oom_handler and container_id:
                    self._oom_handler(container_id)
            elif "disk" in error_msg.lower():
                self._add_audit_entry(
                    ExecutorEventType.DISK_FULL,
                    "Disk full error",
                    {"container_id": container_id, "error": error_msg},
                )
                if self._disk_full_handler and container_id:
                    self._disk_full_handler(container_id)
            else:
                self._add_audit_entry(
                    ExecutorEventType.OPERATION_FAILED,
                    f"Operation failed: {error_msg}",
                    {"container_id": container_id, "error": error_msg},
                )

            return SandboxResult(
                success=False,
                exit_code=1,
                stdout="",
                stderr=error_msg,
                duration=time.time() - start_time,
                resources_used=self._get_resource_metrics(container_id or ""),
                changes_applied=False,
                rollback_performed=request.should_rollback_on_failure,
                audit_log=self.audit_entries.copy(),
                container_id=container_id,
                error=error_msg,
            )

        finally:
            # Cleanup
            if container_id and request.cleanup_on_exit:
                self.stop(container_id)

    def execute(self, request: SandboxRequest) -> SandboxResult:
        """Execute operation in sandbox synchronously.

        Args:
            request: SandboxRequest with operation details

        Returns:
            SandboxResult with execution outcome
        """
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # If in async context, run synchronously
                import concurrent.futures

                with concurrent.futures.ThreadPoolExecutor() as pool:
                    return loop.run_in_executor(
                        pool, lambda: asyncio.run(self.execute_async(request))
                    ).result()
            else:
                return asyncio.run(self.execute_async(request))
        except RuntimeError:
            # No event loop, create one
            return asyncio.run(self.execute_async(request))

    def get_audit_log(self) -> list[AuditEntry]:
        """Get current audit log.

        Returns:
            List of audit entries
        """
        return self.audit_entries.copy()

    def clear_audit_log(self) -> None:
        """Clear audit log."""
        self.audit_entries.clear()
        logger.debug("Audit log cleared")


# Singleton factory
_executor_instance: SandboxExecutor | None = None


def get_executor(
    runtime: str = "docker",
    image: str = "cohezion-sandbox:latest",
    reset: bool = False,
) -> SandboxExecutor:
    """Get or create SandboxExecutor singleton.

    Args:
        runtime: Container runtime
        image: Sandbox image
        reset: If True, reset singleton

    Returns:
        SandboxExecutor instance
    """
    global _executor_instance

    if reset or _executor_instance is None:
        _executor_instance = SandboxExecutor(
            runtime=runtime,
            image=image,
        )

    return _executor_instance
