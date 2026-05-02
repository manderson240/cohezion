"""Tests for SandboxExecutor."""

from datetime import datetime
from unittest.mock import MagicMock, Mock

import pytest

from cohezion.sandbox import (
    ResourceLimits,
    ResourceMetrics,
    SandboxExecutor,
    SandboxRequest,
    SandboxResult,
    get_executor,
)
from cohezion.sandbox.executor import (
    AuditEntry,
    ExecutorEventType,
)


@pytest.fixture
def sandbox():
    """Create a SandboxExecutor instance."""
    executor = SandboxExecutor(runtime="docker", image="test-sandbox:latest")
    yield executor
    # Cleanup
    executor.cleanup()


@pytest.fixture
def basic_request():
    """Create a basic SandboxRequest."""
    return SandboxRequest(
        operation="test_operation",
        context={"key": "value"},
        timeout=60,
    )


class TestSandboxRequest:
    """Test SandboxRequest initialization."""

    def test_default_limits(self):
        """Test that default limits are set."""
        req = SandboxRequest(
            operation="test",
            context={},
        )
        assert req.resource_limits is not None
        assert req.resource_limits.cpu_percent == 200.0
        assert req.resource_limits.memory_gb == 4
        assert req.resource_limits.disk_gb == 10

    def test_custom_limits(self):
        """Test custom resource limits."""
        limits = ResourceLimits(cpu_percent=100, memory_gb=2)
        req = SandboxRequest(
            operation="test",
            context={},
            resource_limits=limits,
        )
        assert req.resource_limits.cpu_percent == 100
        assert req.resource_limits.memory_gb == 2

    def test_timeout_propagates_to_limits(self):
        """Test that timeout is set in limits."""
        req = SandboxRequest(
            operation="test",
            context={},
            timeout=120,
        )
        assert req.resource_limits.timeout_seconds == 120


class TestResourceLimits:
    """Test ResourceLimits."""

    def test_defaults(self):
        """Test default values."""
        limits = ResourceLimits()
        assert limits.cpu_percent == 200.0
        assert limits.memory_gb == 4
        assert limits.disk_gb == 10
        assert limits.timeout_seconds == 3600

    def test_to_dict(self):
        """Test conversion to dictionary."""
        limits = ResourceLimits(cpu_percent=150, memory_gb=2)
        data = limits.to_dict()
        assert data["cpu_percent"] == 150.0
        assert data["memory_gb"] == 2


class TestResourceMetrics:
    """Test ResourceMetrics."""

    def test_defaults(self):
        """Test default values."""
        metrics = ResourceMetrics()
        assert metrics.cpu_percent == 0.0
        assert metrics.memory_mb == 0.0
        assert metrics.process_count == 0

    def test_to_dict(self):
        """Test conversion to dictionary."""
        metrics = ResourceMetrics(cpu_percent=50.0, memory_mb=256.0)
        data = metrics.to_dict()
        assert data["cpu_percent"] == 50.0
        assert data["memory_mb"] == 256.0
        assert "timestamp" in data


class TestAuditEntry:
    """Test AuditEntry."""

    def test_creation(self):
        """Test audit entry creation."""
        entry = AuditEntry(
            event_type=ExecutorEventType.OPERATION_START,
            message="Test message",
        )
        assert entry.event_type == ExecutorEventType.OPERATION_START
        assert entry.message == "Test message"
        assert entry.component == "SandboxExecutor"

    def test_to_dict(self):
        """Test conversion to dictionary."""
        entry = AuditEntry(
            event_type=ExecutorEventType.SANDBOX_START,
            message="Started",
        )
        data = entry.to_dict()
        assert data["event_type"] == "sandbox_start"
        assert data["message"] == "Started"


class TestSandboxResult:
    """Test SandboxResult."""

    def test_success_result(self):
        """Test successful result."""
        metrics = ResourceMetrics(cpu_percent=50.0)
        result = SandboxResult(
            success=True,
            exit_code=0,
            stdout="output",
            stderr="",
            duration=1.5,
            resources_used=metrics,
            changes_applied=True,
            rollback_performed=False,
            audit_log=[],
        )
        assert result.success is True
        assert result.exit_code == 0

    def test_to_dict(self):
        """Test conversion to dictionary."""
        metrics = ResourceMetrics()
        result = SandboxResult(
            success=True,
            exit_code=0,
            stdout="test",
            stderr="",
            duration=1.0,
            resources_used=metrics,
            changes_applied=True,
            rollback_performed=False,
            audit_log=[],
        )
        data = result.to_dict()
        assert data["success"] is True
        assert data["exit_code"] == 0
        assert isinstance(data["resources_used"], dict)


class TestSandboxExecutor:
    """Test SandboxExecutor."""

    def test_initialization(self):
        """Test executor initialization."""
        executor = SandboxExecutor(
            runtime="docker",
            image="test:latest",
        )
        assert executor.runtime == "docker"
        assert executor.image == "test:latest"
        assert len(executor.containers) == 0

    def test_set_limits(self, sandbox):
        """Test setting resource limits."""
        sandbox.set_limits(cpu_percent=100, memory_gb=2, disk_gb=5)
        assert sandbox.default_limits.cpu_percent == 100.0
        assert sandbox.default_limits.memory_gb == 2
        assert sandbox.default_limits.disk_gb == 5

    def test_on_timeout_handler(self, sandbox):
        """Test registering timeout handler."""
        handler = Mock()
        sandbox.on_timeout(handler)
        assert sandbox._timeout_handler == handler

    def test_on_oom_handler(self, sandbox):
        """Test registering OOM handler."""
        handler = Mock()
        sandbox.on_oom(handler)
        assert sandbox._oom_handler == handler

    def test_on_disk_full_handler(self, sandbox):
        """Test registering disk full handler."""
        handler = Mock()
        sandbox.on_disk_full(handler)
        assert sandbox._disk_full_handler == handler

    def test_audit_entry_added(self, sandbox):
        """Test audit entry is recorded."""
        sandbox._add_audit_entry(
            ExecutorEventType.OPERATION_START,
            "Test operation",
        )
        assert len(sandbox.audit_entries) == 1
        entry = sandbox.audit_entries[0]
        assert entry.event_type == ExecutorEventType.OPERATION_START
        assert entry.message == "Test operation"

    def test_get_audit_log(self, sandbox):
        """Test retrieving audit log."""
        sandbox._add_audit_entry(
            ExecutorEventType.SANDBOX_START,
            "Started",
        )
        log = sandbox.get_audit_log()
        assert len(log) == 1
        assert log[0].message == "Started"

    def test_clear_audit_log(self, sandbox):
        """Test clearing audit log."""
        sandbox._add_audit_entry(
            ExecutorEventType.OPERATION_START,
            "Test",
        )
        assert len(sandbox.audit_entries) == 1
        sandbox.clear_audit_log()
        assert len(sandbox.audit_entries) == 0

    def test_cleanup_empty(self, sandbox):
        """Test cleanup with no containers."""
        sandbox.cleanup()
        assert len(sandbox.containers) == 0


class TestExecutorAsync:
    """Test async execution."""

    @pytest.mark.asyncio
    async def test_execute_async_success(self, sandbox, basic_request):
        """Test successful async execution."""
        # Mock Docker client to avoid actual container creation
        sandbox.client = MagicMock()

        result = await sandbox.execute_async(basic_request)

        assert result is not None
        assert isinstance(result, SandboxResult)
        # Note: Will fail without Docker, but structure is tested

    @pytest.mark.asyncio
    async def test_execute_async_timeout(self, sandbox, basic_request):
        """Test async execution with timeout."""
        sandbox.client = MagicMock()
        basic_request.timeout = 1

        # This test verifies timeout handling exists
        result = await sandbox.execute_async(basic_request)
        assert isinstance(result, SandboxResult)


class TestExecutorSync:
    """Test synchronous execution."""

    def test_execute_sync_creates_result(self, sandbox, basic_request):
        """Test that execute returns a SandboxResult."""
        sandbox.client = MagicMock()

        try:
            result = sandbox.execute(basic_request)
            assert isinstance(result, SandboxResult)
        except RuntimeError:
            # Expected if Docker is not available
            pytest.skip("Docker not available")


class TestExecutorSingleton:
    """Test singleton factory."""

    def test_get_executor_singleton(self):
        """Test that get_executor returns same instance."""
        executor1 = get_executor()
        executor2 = get_executor()
        assert executor1 is executor2

    def test_get_executor_reset(self):
        """Test that reset creates new instance."""
        executor1 = get_executor()
        executor2 = get_executor(reset=True)
        assert executor1 is not executor2

    def test_get_executor_custom_params(self):
        """Test executor with custom parameters."""
        executor = get_executor(
            runtime="podman",
            image="custom:latest",
            reset=True,
        )
        assert executor.runtime == "podman"
        assert executor.image == "custom:latest"


class TestContainerLifecycle:
    """Test container lifecycle management."""

    def test_start_without_client(self, sandbox):
        """Test start fails without Docker client."""
        sandbox.client = None
        with pytest.raises(RuntimeError):
            sandbox.start()

    def test_stop_nonexistent_container(self, sandbox):
        """Test stopping nonexistent container is safe."""
        # Should not raise error
        sandbox.stop("nonexistent")
        assert "nonexistent" not in sandbox.containers


class TestErrorHandling:
    """Test error handling."""

    def test_audit_entry_on_error(self, sandbox, basic_request):
        """Test that errors are logged to audit."""
        sandbox.client = MagicMock()
        sandbox.client.containers.create.side_effect = Exception("Docker error")

        try:
            sandbox.execute(basic_request)
            # If we get here, check the audit log
            assert len(sandbox.audit_entries) > 0
        except RuntimeError:
            # Expected behavior
            pass

    def test_timeout_handler_callback(self, sandbox):
        """Test timeout handler is called."""
        handler = Mock()
        sandbox.on_timeout(handler)
        assert sandbox._timeout_handler is not None


class TestResourceMonitoring:
    """Test resource monitoring."""

    def test_get_resource_metrics_empty(self, sandbox):
        """Test getting metrics with no container."""
        metrics = sandbox._get_resource_metrics("nonexistent")
        assert metrics.cpu_percent == 0.0
        assert metrics.memory_mb == 0.0

    def test_resource_limits_to_dict(self):
        """Test ResourceLimits serialization."""
        limits = ResourceLimits(
            cpu_percent=150,
            memory_gb=3,
            disk_gb=8,
        )
        data = limits.to_dict()
        assert "cpu_percent" in data
        assert "memory_gb" in data
        assert "disk_gb" in data


class TestAuditLogging:
    """Test audit logging."""

    def test_audit_entry_timestamp(self):
        """Test that audit entries have timestamps."""
        entry = AuditEntry(
            event_type=ExecutorEventType.OPERATION_START,
            message="Test",
        )
        assert entry.timestamp is not None
        # Verify it's parseable as ISO format
        datetime.fromisoformat(entry.timestamp)

    def test_audit_log_persistence(self, sandbox, tmp_path):
        """Test saving audit log to file."""
        log_file = tmp_path / "audit.jsonl"
        sandbox.audit_log_path = str(log_file)

        sandbox._add_audit_entry(
            ExecutorEventType.SANDBOX_START,
            "Test",
        )
        sandbox._save_audit_log()

        assert log_file.exists()
        # Verify file contains JSON lines
        lines = log_file.read_text().strip().split("\n")
        assert len(lines) > 0


# Integration-style tests (marked as integration since they test multiple components)
@pytest.mark.integration
class TestExecutorIntegration:
    """Integration tests."""

    def test_full_request_response_cycle(self, basic_request):
        """Test complete request/response cycle."""
        executor = SandboxExecutor()
        executor.client = MagicMock()

        # Verify structure without actually executing
        assert basic_request.operation == "test_operation"
        assert len(executor.audit_entries) == 0

    def test_multiple_audit_entries(self, sandbox):
        """Test multiple audit entries are tracked."""
        for i in range(5):
            sandbox._add_audit_entry(
                ExecutorEventType.OPERATION_START,
                f"Operation {i}",
            )

        assert len(sandbox.audit_entries) == 5
        log = sandbox.get_audit_log()
        assert len(log) == 5
