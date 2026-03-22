"""Tests for DynamicConcurrencyGate - Phase 1 Bottleneck #1."""

from unittest.mock import MagicMock

import pytest

from cohezion.swarm.dynamic_concurrency_gate import (
    ConcurrencyDecision,
    DynamicConcurrencyGate,
    get_concurrency_gate,
)


@pytest.fixture
def mock_metrics():
    """Create mock HardwareMetrics."""
    return MagicMock()


@pytest.fixture
def gate(mock_metrics):
    """Create DynamicConcurrencyGate with mocked metrics."""
    gate = DynamicConcurrencyGate(base_concurrency=4)
    gate.metrics = mock_metrics
    return gate


class TestConcurrencyDecision:
    """Test ConcurrencyDecision data class."""

    def test_decision_creation(self):
        """Test creating a concurrency decision."""
        decision = ConcurrencyDecision(
            safe_concurrency=8,
            reason="Test reason",
            vram_percent=50.0,
            thermal_percent=60.0,
            healthy=True,
        )
        assert decision.safe_concurrency == 8
        assert decision.reason == "Test reason"
        assert decision.vram_percent == 50.0
        assert decision.thermal_percent == 60.0
        assert decision.healthy is True


class TestDynamicConcurrencyGate:
    """Test DynamicConcurrencyGate initialization and configuration."""

    def test_initialization_default(self):
        """Test default initialization."""
        gate = DynamicConcurrencyGate()
        assert gate.base_concurrency == 4
        assert gate._adjustment_count == 0
        assert gate._last_decision is None

    def test_initialization_custom_base(self):
        """Test initialization with custom base concurrency."""
        gate = DynamicConcurrencyGate(base_concurrency=2)
        assert gate.base_concurrency == 2

    def test_get_stats_initial(self):
        """Test stats before any calculation."""
        gate = DynamicConcurrencyGate()
        stats = gate.get_stats()
        assert stats["current_concurrency"] == 4
        assert stats["base_concurrency"] == 4
        assert stats["adjustment_count"] == 0


class TestConcurrencyCalculation:
    """Test concurrency level calculation based on hardware state."""

    def test_plenty_of_headroom(self, gate, mock_metrics):
        """Test scaling to 12 with plenty of headroom."""
        # Create mock snapshot with low pressure
        snapshot = MagicMock()
        snapshot.is_healthy.return_value = True
        snapshot.memory.used_percent = 25.0
        snapshot.thermal.thermal_percent = 50.0
        mock_metrics.get_snapshot.return_value = snapshot

        concurrency = gate.get_safe_concurrency()
        assert concurrency == 12
        assert gate._last_decision.reason == "Plenty of headroom"

    def test_good_headroom(self, gate, mock_metrics):
        """Test scaling to 10 with good headroom."""
        snapshot = MagicMock()
        snapshot.is_healthy.return_value = True
        snapshot.memory.used_percent = 65.0  # Between 60-70
        snapshot.thermal.thermal_percent = 72.0
        mock_metrics.get_snapshot.return_value = snapshot

        concurrency = gate.get_safe_concurrency()
        assert concurrency == 10
        assert gate._last_decision.reason == "Good headroom"

    def test_moderate_headroom(self, gate, mock_metrics):
        """Test scaling to 8 with moderate headroom."""
        snapshot = MagicMock()
        snapshot.is_healthy.return_value = True
        snapshot.memory.used_percent = 75.0
        snapshot.thermal.thermal_percent = 78.0
        mock_metrics.get_snapshot.return_value = snapshot

        concurrency = gate.get_safe_concurrency()
        assert concurrency == 8
        assert gate._last_decision.reason == "Moderate headroom"

    def test_conservative_fallback_limited_headroom(self, gate, mock_metrics):
        """Test fallback to 4 under resource pressure."""
        snapshot = MagicMock()
        snapshot.is_healthy.return_value = True
        snapshot.memory.used_percent = 82.0
        snapshot.thermal.thermal_percent = 85.0
        mock_metrics.get_snapshot.return_value = snapshot

        concurrency = gate.get_safe_concurrency()
        assert concurrency == 4
        assert "conservative fallback" in gate._last_decision.reason.lower()

    def test_unhealthy_system(self, gate, mock_metrics):
        """Test fallback when system is unhealthy."""
        snapshot = MagicMock()
        snapshot.is_healthy.return_value = False
        snapshot.memory.used_percent = 90.0
        snapshot.thermal.thermal_percent = 92.0
        mock_metrics.get_snapshot.return_value = snapshot

        concurrency = gate.get_safe_concurrency()
        assert concurrency == 4
        assert "unhealthy" in gate._last_decision.reason.lower()
        assert gate._last_decision.healthy is False


class TestErrorHandling:
    """Test error handling and graceful degradation."""

    def test_metrics_collection_error(self, gate, mock_metrics):
        """Test graceful handling when metrics collection fails."""
        mock_metrics.get_snapshot.side_effect = Exception("Metrics error")

        concurrency = gate.get_safe_concurrency()
        assert concurrency == 4  # Falls back to base
        assert gate._last_decision.healthy is False
        assert "Error" in gate._last_decision.reason


class TestMonitoring:
    """Test monitoring and statistics collection."""

    def test_get_last_decision(self, gate, mock_metrics):
        """Test retrieving last decision."""
        snapshot = MagicMock()
        snapshot.is_healthy.return_value = True
        snapshot.memory.used_percent = 40.0
        snapshot.thermal.thermal_percent = 60.0
        mock_metrics.get_snapshot.return_value = snapshot

        assert gate.get_last_decision() is None

        gate.get_safe_concurrency()
        decision = gate.get_last_decision()
        assert decision is not None
        assert decision.safe_concurrency == 12

    def test_stats_after_decision(self, gate, mock_metrics):
        """Test stats reflect last decision."""
        snapshot = MagicMock()
        snapshot.is_healthy.return_value = True
        snapshot.memory.used_percent = 50.0
        snapshot.thermal.thermal_percent = 72.0
        mock_metrics.get_snapshot.return_value = snapshot

        gate.get_safe_concurrency()
        stats = gate.get_stats()

        assert stats["current_concurrency"] == 10
        assert stats["last_vram_percent"] == 50.0
        assert stats["last_thermal_percent"] == 72.0
        assert stats["last_healthy"] is True


class TestAsyncInterface:
    """Test async context manager for concurrency control."""

    @pytest.mark.asyncio
    async def test_acquire_semaphore(self, gate, mock_metrics):
        """Test acquiring a semaphore with calculated concurrency."""
        snapshot = MagicMock()
        snapshot.is_healthy.return_value = True
        snapshot.memory.used_percent = 25.0
        snapshot.thermal.thermal_percent = 50.0
        mock_metrics.get_snapshot.return_value = snapshot

        semaphore = await gate.acquire()
        assert semaphore is not None
        # Semaphore should have 12 permits (calculated concurrency for low pressure)
        assert semaphore._value == 12


class TestSingletonFactory:
    """Test singleton pattern for gate."""

    def test_get_gate_singleton(self):
        """Test that get_concurrency_gate returns same instance."""
        gate1 = get_concurrency_gate()
        gate2 = get_concurrency_gate()
        assert gate1 is gate2

    def test_get_gate_reset(self):
        """Test resetting singleton."""
        gate1 = get_concurrency_gate()
        gate2 = get_concurrency_gate(reset=True)
        assert gate1 is not gate2

    def test_get_gate_custom_params(self):
        """Test gate can be customized after reset."""
        get_concurrency_gate(reset=True)
        gate = get_concurrency_gate()
        assert gate.base_concurrency == 4


class TestIntegration:
    """Integration tests for concurrency gate."""

    def test_full_workflow_scaling_up(self, mock_metrics):
        """Test scaling up with high-resource state."""
        gate = DynamicConcurrencyGate(base_concurrency=4)
        gate.metrics = mock_metrics

        # High-resource state
        snapshot_high = MagicMock()
        snapshot_high.is_healthy.return_value = True
        snapshot_high.memory.used_percent = 15.0
        snapshot_high.thermal.thermal_percent = 45.0
        mock_metrics.get_snapshot.return_value = snapshot_high

        # Should scale up
        concurrency = gate.get_safe_concurrency()
        assert concurrency == 12

        # Get stats
        stats = gate.get_stats()
        assert stats["current_concurrency"] == 12
        assert stats["last_vram_percent"] == 15.0
        assert stats["last_thermal_percent"] == 45.0

    def test_full_workflow_scaling_down(self, mock_metrics):
        """Test scaling down under resource pressure."""
        gate = DynamicConcurrencyGate(base_concurrency=4)
        gate.metrics = mock_metrics

        # Low-resource state
        snapshot_low = MagicMock()
        snapshot_low.is_healthy.return_value = True
        snapshot_low.memory.used_percent = 78.0
        snapshot_low.thermal.thermal_percent = 82.0
        mock_metrics.get_snapshot.return_value = snapshot_low

        # Should scale down
        concurrency = gate.get_safe_concurrency()
        assert concurrency == 4

        # Stats updated
        stats = gate.get_stats()
        assert stats["current_concurrency"] == 4
        assert stats["last_vram_percent"] == 78.0
        assert stats["last_thermal_percent"] == 82.0

    def test_dynamic_adjustment(self, mock_metrics):
        """Test gate responds to changing hardware state."""
        gate = DynamicConcurrencyGate(base_concurrency=4)
        gate.metrics = mock_metrics

        # Start with good conditions (40% < 60%, 60% < 70% = plenty)
        snapshot = MagicMock()
        snapshot.is_healthy.return_value = True
        snapshot.memory.used_percent = 40.0
        snapshot.thermal.thermal_percent = 60.0
        mock_metrics.get_snapshot.return_value = snapshot

        level1 = gate.get_safe_concurrency()
        assert level1 == 12  # Plenty of headroom (VRAM <60% + thermal <70%)

        # Degrade conditions
        snapshot.memory.used_percent = 85.0
        snapshot.thermal.thermal_percent = 88.0
        level2 = gate.get_safe_concurrency()
        assert level2 == 4  # Limited headroom

        # Recover
        snapshot.memory.used_percent = 20.0
        snapshot.thermal.thermal_percent = 40.0
        level3 = gate.get_safe_concurrency()
        assert level3 == 12  # Plenty of headroom
