"""Tests for UniverseBridge connecting compound executor to universe engine (Phase 7).

Validates that enriched journey data flows through to universe simulation.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import numpy as np
import pytest

from cohezion.compound.executor import CompoundExecutor
from cohezion.compound.journey_tracker import JourneyTracker
from cohezion.compound.universe_bridge import UniverseBridge


@pytest.fixture
def mock_mcp_client():
    """Create a mock MCP client."""
    client = MagicMock()
    client.vault_find_relevant_context.return_value = []
    client.vault_search.return_value = []
    client.vault_write.return_value = "success"
    client.vault_read.return_value = '{"status": "started"}'
    client.vault_log_experiment.return_value = "experiments/test.md"
    client.vault_log_decision.return_value = "decisions/test.md"
    client.vault_extract_pattern.return_value = "patterns/test.md"
    client.vault_edit.return_value = "success"
    return client


class TestUniverseBridge:
    """Tests for UniverseBridge adapter (Phase 7)."""

    def test_execution_creates_universe_journey(self, mock_mcp_client):
        """Execution creates a UniverseJourney (symmetry breaking event)."""
        # Use a real engine as the "engine" parameter
        engine = MagicMock()  # Acts as a non-None flag
        bridge = UniverseBridge(engine=engine, agent_name="test-agent")
        tracker = JourneyTracker(seed=42)

        executor = CompoundExecutor(
            mock_mcp_client,
            enable_guardrails=False,
            journey_tracker=tracker,
            universe_bridge=bridge,
        )

        def task_fn(guidance):
            return "output", {}

        result = executor.execute_task(
            task_description="Test universe",
            skill_name="test",
            operation_type="generate",
            execute_fn=task_fn,
        )
        assert result.success is True
        # Bridge should have no remaining active journeys (completed)
        assert len(bridge._active_journeys) == 0

    def test_trajectory_point_maps_to_axiomatic_state(self):
        """JourneyTracker point correctly maps to AxiomaticState across 4 fabrics."""
        bridge = UniverseBridge(engine=MagicMock())

        vector_12d = np.array(
            [
                0.1,
                0.2,
                0.3,  # Space fabric
                0.4,
                0.5,
                0.6,  # Field fabric
                0.7,
                0.8,
                0.9,  # Control fabric
                0.15,
                0.25,
                0.35,  # Precipitation fabric
            ]
        )

        axiomatic = bridge._vector_to_axiomatic(vector_12d)

        # Space fabric
        assert axiomatic.spatial_x == pytest.approx(0.1)
        assert axiomatic.spatial_y == pytest.approx(0.2)
        assert axiomatic.spatial_z == pytest.approx(0.3)
        # Field fabric
        assert axiomatic.physics == pytest.approx(0.4)
        assert axiomatic.biology == pytest.approx(0.5)
        assert axiomatic.field == pytest.approx(0.6)
        # Control fabric
        assert axiomatic.logic == pytest.approx(0.7)
        assert axiomatic.quantum == pytest.approx(0.8)
        assert axiomatic.control == pytest.approx(0.9)
        # Precipitation fabric
        assert axiomatic.temporal == pytest.approx(0.15)
        assert axiomatic.novelty == pytest.approx(0.25)
        assert axiomatic.precipitation == pytest.approx(0.35)

    def test_successful_execution_completes_journey(self, mock_mcp_client):
        """Successful execution completes journey with phi_score and precipitation."""
        engine = MagicMock()
        bridge = UniverseBridge(engine=engine, agent_name="test-agent")
        tracker = JourneyTracker(seed=42)

        executor = CompoundExecutor(
            mock_mcp_client,
            enable_guardrails=False,
            journey_tracker=tracker,
            universe_bridge=bridge,
        )

        def task_fn(guidance):
            return "successful output", {"quality": 0.9}

        executor.execute_task(
            task_description="Complete test",
            skill_name="test",
            operation_type="generate",
            execute_fn=task_fn,
        )
        # Journey should be completed (removed from active)
        assert len(bridge._active_journeys) == 0

    def test_bridge_noop_when_engine_unavailable(self, mock_mcp_client):
        """Bridge gracefully no-ops if engine unavailable."""
        bridge = UniverseBridge(engine=None)  # No engine

        # All operations should return None/False without crashing
        assert bridge.start_journey("test") is None
        assert bridge.add_point("nonexistent", MagicMock()) is False
        assert bridge.complete_journey("nonexistent", True) is None

        # Executor should work fine with no-op bridge
        executor = CompoundExecutor(
            mock_mcp_client,
            enable_guardrails=False,
            universe_bridge=bridge,
        )

        def task_fn(guidance):
            return "output", {}

        result = executor.execute_task(
            task_description="Test",
            skill_name="test",
            operation_type="generate",
            execute_fn=task_fn,
        )
        assert result.success is True

    def test_real_coherence_flows_to_universe(self, mock_mcp_client):
        """Real cohesion from Phase 1 flows through to universe trajectory."""
        engine = MagicMock()
        bridge = UniverseBridge(engine=engine, agent_name="test-agent")
        tracker = JourneyTracker(seed=42)

        executor = CompoundExecutor(
            mock_mcp_client,
            enable_guardrails=False,
            journey_tracker=tracker,
            universe_bridge=bridge,
        )

        def task_fn(guidance):
            return "output", {}

        result = executor.execute_task(
            task_description="Coherence test",
            skill_name="test",
            operation_type="generate",
            execute_fn=task_fn,
        )

        # Verify coherence was computed (Phase 1) and is not the default 0.5
        assert "coherence" in result.metrics
        # The tracker should have received the real coherence
        assert len(tracker._recent_points) > 0
        point = tracker._recent_points[-1]
        # Coherence should match what the executor computed
        assert point.coherence == result.metrics["coherence"]
