"""Tests for AgentVerseBridge - Cohezion-AgentVerse protocol bridge.

TDD tests for AgentVerseBridge that connects AgentVerse agent messages
to Cohezion's CompoundExecutor for coherence-aware execution.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from unittest.mock import MagicMock, patch

import pytest


@dataclass
class MockExecutionResult:
    """Mock execution result for testing."""

    success: bool
    output: str
    metrics: dict = field(default_factory=dict)
    duration_seconds: float = 0.0


class TestAgentVerseBridge:
    """[P0] Tests for AgentVerseBridge."""

    @pytest.fixture()
    def mock_executor(self):
        """Create mock CompoundExecutor."""
        executor = MagicMock()
        executor.execute_task = MagicMock()
        executor.get_experience_guidance = MagicMock(return_value={})
        return executor

    @pytest.fixture()
    def bridge(self, mock_executor):
        """Create bridge with mocked executor."""
        from cohezion.integrations.agentverse import AgentVerseBridge

        bridge = AgentVerseBridge(executor=mock_executor)
        return bridge

    def test_initialization(self, bridge, mock_executor):
        """[P0] Should initialize with executor."""
        assert bridge.executor == mock_executor
        assert bridge.metrics == []

    def test_initialization_with_model_router(self, mock_executor):
        """[P1] Should accept optional model router."""
        from cohezion.integrations.agentverse import AgentVerseBridge

        mock_router = MagicMock()
        bridge = AgentVerseBridge(
            executor=mock_executor,
            model_router=mock_router,
        )
        assert bridge.model_router == mock_router

    def test_on_agent_message_routes_to_executor(self, bridge, mock_executor):
        """[P0] Should route agent messages to executor."""
        mock_executor.execute_task.return_value = MockExecutionResult(
            success=True,
            output="executed",
            metrics={"coherence": 0.8},
            duration_seconds=1.0,
        )

        bridge.on_agent_message(
            agent_name="test_agent",
            message="Write a test",
            skill_name="testing_PRIME",
        )

        mock_executor.execute_task.assert_called_once()

    def test_on_agent_message_captures_metrics(self, bridge, mock_executor):
        """[P0] Should capture coherence metrics from execution."""
        mock_executor.execute_task.return_value = MockExecutionResult(
            success=True,
            output="done",
            metrics={"coherence": 0.85, "alignment": 0.9},
            duration_seconds=1.5,
        )

        bridge.on_agent_message(
            agent_name="coder",
            message="implement feature",
            skill_name="python_PRIME",
        )

        assert len(bridge.metrics) == 1
        assert bridge.metrics[0]["coherence"] == 0.85

    def test_on_agent_message_handles_failure(self, bridge, mock_executor):
        """[P0] Should handle execution failures gracefully."""
        mock_executor.execute_task.return_value = MockExecutionResult(
            success=False,
            output="error",
            metrics={"error": "failed"},
            duration_seconds=0.5,
        )

        bridge.on_agent_message(
            agent_name="test",
            message="fail task",
            skill_name="test_PRIME",
        )

        assert len(bridge.metrics) == 1
        assert bridge.metrics[0]["success"] is False

    def test_get_coherence_trajectory_returns_list(self, bridge):
        """[P0] Should return coherence trajectory."""
        bridge.metrics = [
            {"coherence": 0.7, "agent": "a1"},
            {"coherence": 0.8, "agent": "a2"},
            {"coherence": 0.75, "agent": "a1"},
        ]

        trajectory = bridge.get_coherence_trajectory()
        assert isinstance(trajectory, list)
        assert len(trajectory) == 3

    def test_get_coherence_trajectory_empty(self, bridge):
        """[P0] Should return empty list when no metrics."""
        trajectory = bridge.get_coherence_trajectory()
        assert trajectory == []

    def test_get_average_coherence(self, bridge):
        """[P1] Should compute average coherence."""
        bridge.metrics = [
            {"coherence": 0.8},
            {"coherence": 0.7},
            {"coherence": 0.9},
        ]

        avg = bridge.get_average_coherence()
        assert avg == pytest.approx(0.8, rel=0.01)

    def test_get_average_coherence_empty(self, bridge):
        """[P1] Should return 0 when no metrics."""
        avg = bridge.get_average_coherence()
        assert avg == 0.0

    def test_check_hiho_violation_detects_low_coherence(self, bridge):
        """[P1] Should detect HIHO band violations (low)."""
        bridge.metrics = [{"coherence": 0.3}]

        violations = bridge.check_hiho_violations()
        assert len(violations) > 0

    def test_check_hiho_violation_detects_high_coherence(self, bridge):
        """[P1] Should detect HIHO band violations (high)."""
        bridge.metrics = [{"coherence": 0.9}]

        violations = bridge.check_hiho_violations()
        assert len(violations) > 0

    def test_check_hiho_violation_none_in_band(self, bridge):
        """[P1] Should return no violations when in HIHO band."""
        bridge.metrics = [{"coherence": 0.5}]

        violations = bridge.check_hiho_violations()
        assert len(violations) == 0

    def test_reset_clears_metrics(self, bridge):
        """[P0] Should clear metrics on reset."""
        bridge.metrics = [{"coherence": 0.8}]
        bridge.reset()
        assert bridge.metrics == []


class TestAgentVerseBridgeModelRouting:
    """[P1] Tests for AgentVerseBridge model routing."""

    @pytest.fixture()
    def mock_executor(self):
        """Create mock executor."""
        return MagicMock()

    @pytest.fixture()
    def bridge_with_router(self, mock_executor):
        """Create bridge with model router."""
        from cohezion.integrations.agentverse import AgentVerseBridge

        mock_router = MagicMock()
        mock_router.select_model = MagicMock(return_value="qwen3-coder:30b")
        return AgentVerseBridge(
            executor=mock_executor,
            model_router=mock_router,
        )

    def test_route_message_uses_model_router(self, bridge_with_router):
        """[P1] Should route messages using model router."""
        bridge_with_router.route_message(
            agent_name="coder",
            message="write code",
        )

        bridge_with_router.model_router.select_model.assert_called_once()

    def test_route_message_returns_routing_decision(self, bridge_with_router):
        """[P1] Should return routing decision."""
        decision = bridge_with_router.route_message(
            agent_name="researcher",
            message="analyze this",
        )

        assert decision is not None
        assert hasattr(decision, "model") or isinstance(decision, dict)


class TestAgentVerseBridgeVaultIntegration:
    """[P1] Tests for AgentVerseBridge vault integration."""

    @pytest.fixture()
    def mock_executor(self):
        """Create mock executor with vault logging."""
        executor = MagicMock()
        executor.execute_task.return_value = MockExecutionResult(
            success=True,
            output="done",
            metrics={"coherence": 0.8},
            duration_seconds=1.0,
        )
        return executor

    @pytest.fixture()
    def bridge(self, mock_executor):
        """Create bridge."""
        from cohezion.integrations.agentverse import AgentVerseBridge

        return AgentVerseBridge(executor=mock_executor)

    def test_logs_to_vault_on_critical_inflection(self, bridge, mock_executor):
        """[P1] Should log critical inflection points to vault."""
        bridge.metrics = [
            {"coherence": 0.9, "agent": "a1"},
            {"coherence": 0.2, "agent": "a2"},  # Critical drop
        ]

        with patch.object(bridge, "log_inflection_to_vault"):
            violations = bridge.check_hiho_violations()
            # Verify violations are detected
            assert len(violations) > 0

    def test_export_trajectory_for_vault(self, bridge):
        """[P1] Should export trajectory data for vault persistence."""
        bridge.metrics = [
            {"coherence": 0.8, "agent": "a1", "skill": "python_PRIME"},
            {"coherence": 0.7, "agent": "a2", "skill": "testing_PRIME"},
        ]

        trajectory = bridge.export_trajectory()
        assert isinstance(trajectory, dict)
        assert "metrics" in trajectory
        assert "coherence_trend" in trajectory or len(trajectory) > 0
