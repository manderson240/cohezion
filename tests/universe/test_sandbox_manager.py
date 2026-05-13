"""Tests for sandbox manager."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from cohezion.universe.sandbox_backends import BackendResult
from cohezion.universe.sandbox_manager import (
    SYSTEM_MEMORY_BUDGET_MB,
    SandboxManager,
    get_sandbox_manager,
)
from cohezion.universe.sandbox_profiles import SandboxProfile, SandboxTier


@pytest.fixture(autouse=True)
def reset_manager():
    """Reset singleton and circuit breaker between tests."""
    SandboxManager.reset()
    yield
    SandboxManager.reset()
    # Reset the circuit breaker to prevent cross-test contamination
    from cohezion.reliability import _circuits

    _circuits.pop("sandbox_manager", None)


@pytest.fixture
def mock_backend():
    """Create a mock isolation backend."""
    backend = MagicMock()
    backend.execute = AsyncMock(
        return_value=BackendResult(
            success=True,
            exit_code=0,
            stdout="ok",
            stderr="",
            duration=0.5,
        )
    )
    backend.cleanup = AsyncMock()
    backend.is_available = MagicMock(return_value=True)
    return backend


class TestSandboxManagerSingleton:
    def test_singleton(self):
        m1 = get_sandbox_manager()
        m2 = get_sandbox_manager()
        assert m1 is m2

    def test_reset(self):
        m1 = get_sandbox_manager()
        SandboxManager.reset()
        m2 = get_sandbox_manager()
        assert m1 is not m2


class TestSandboxManagerStats:
    def test_initial_stats(self):
        manager = get_sandbox_manager()
        stats = manager.get_stats()
        assert stats["active_count"] == 0
        assert stats["allocated_memory_mb"] == 0
        assert stats["budget_remaining_mb"] == SYSTEM_MEMORY_BUDGET_MB

    def test_budget_remaining(self):
        manager = get_sandbox_manager()
        assert manager.budget_remaining_mb == SYSTEM_MEMORY_BUDGET_MB


class TestSandboxManagerExecution:
    @pytest.mark.anyio
    async def test_run_simulation_success(self, mock_backend):
        manager = get_sandbox_manager()
        manager._backend = mock_backend

        with patch(
            "cohezion.universe.sandbox_manager.SandboxManager._wait_for_backpressure",
            new_callable=AsyncMock,
        ):
            result = await manager.run_simulation("print('hello')", tier=SandboxTier.LIGHT)
        assert result.success
        assert result.stdout == "ok"

    @pytest.mark.anyio
    async def test_run_simulation_cleans_up(self, mock_backend):
        manager = get_sandbox_manager()
        manager._backend = mock_backend

        with patch(
            "cohezion.universe.sandbox_manager.SandboxManager._wait_for_backpressure",
            new_callable=AsyncMock,
        ):
            await manager.run_simulation("print('test')", tier=SandboxTier.LIGHT)

        # After execution completes, sandbox should be cleaned up
        assert manager.get_stats()["active_count"] == 0

    @pytest.mark.anyio
    async def test_run_simulation_with_custom_profile(self, mock_backend):
        manager = get_sandbox_manager()
        manager._backend = mock_backend

        profile = SandboxProfile(
            memory_limit_mb=2048,
            cpu_quota_percent=150,
            timeout_seconds=120,
        )

        with patch(
            "cohezion.universe.sandbox_manager.SandboxManager._wait_for_backpressure",
            new_callable=AsyncMock,
        ):
            result = await manager.run_simulation("print('custom')", profile=profile)
        assert result.success

    @pytest.mark.anyio
    async def test_memory_budget_exceeded(self, mock_backend):
        manager = get_sandbox_manager()
        manager._backend = mock_backend

        huge_profile = SandboxProfile(
            memory_limit_mb=SYSTEM_MEMORY_BUDGET_MB + 1024,
            cpu_quota_percent=100,
            timeout_seconds=60,
        )

        with (
            pytest.raises(RuntimeError, match="Memory budget exceeded"),
            patch(
                "cohezion.universe.sandbox_manager.SandboxManager._wait_for_backpressure",
                new_callable=AsyncMock,
            ),
        ):
            await manager.run_simulation("print('too big')", profile=huge_profile)

    @pytest.mark.anyio
    async def test_circuit_breaker_opens(self, mock_backend):
        manager = get_sandbox_manager()
        mock_backend.execute = AsyncMock(
            return_value=BackendResult(
                success=False,
                exit_code=1,
                stdout="",
                stderr="error",
                duration=0.1,
            )
        )
        manager._backend = mock_backend

        with patch(
            "cohezion.universe.sandbox_manager.SandboxManager._wait_for_backpressure",
            new_callable=AsyncMock,
        ):
            # Exhaust circuit breaker (threshold=3)
            for _ in range(3):
                await manager.run_simulation("fail", tier=SandboxTier.LIGHT)

            # Next call should be rejected by circuit breaker
            with pytest.raises(RuntimeError, match="circuit breaker is OPEN"):
                await manager.run_simulation("blocked", tier=SandboxTier.LIGHT)


class TestSandboxManagerIntegration:
    @pytest.mark.anyio
    async def test_subprocess_backend_integration(self):
        """Integration test using the real SubprocessBackend."""
        manager = get_sandbox_manager()
        # Force subprocess backend
        from cohezion.universe.sandbox_backends import SubprocessBackend

        manager._backend = SubprocessBackend()

        with patch(
            "cohezion.universe.sandbox_manager.SandboxManager._wait_for_backpressure",
            new_callable=AsyncMock,
        ):
            result = await manager.run_simulation("print('integration test')", tier=SandboxTier.LIGHT)
        assert result.success
        assert "integration test" in result.stdout
