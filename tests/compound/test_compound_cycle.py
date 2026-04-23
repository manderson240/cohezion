"""Tests for end-to-end compound cycle validation (Phase 8)."""

from unittest.mock import MagicMock

import pytest

from cohezion.compound.degradation_detector import DegradationDetector
from cohezion.compound.executor import CompoundExecutor
from cohezion.compound.inflection_detector import Severity
from cohezion.compound.journey_tracker import JourneyTracker
from cohezion.compound.skill_refiner import SkillRefiner
from cohezion.compound.universe_bridge import UniverseBridge
from cohezion.core.compound.retrospection import RetrospectionEngine


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


@pytest.fixture
def mock_inflection_detector():
    """Create a mock inflection detector with low anomaly."""
    detector = MagicMock()
    anomaly = MagicMock()
    anomaly.severity = Severity.INFO
    anomaly.score = 0.1
    anomaly.issues = []
    anomaly.recommendations = []
    anomaly.should_reexecute = False
    detector.detect_anomaly.return_value = anomaly
    return detector


class TestCompoundCycleEndToEnd:
    """Tests for complete enriched compound cycle (all 7 phases)."""

    def test_enriched_executor_with_all_components(self, mock_mcp_client, mock_inflection_detector):
        """Enriched executor integrates all 7 phase components."""
        journey_tracker = JourneyTracker(seed=42)
        degradation_detector = DegradationDetector()
        retrospection_engine = RetrospectionEngine()
        skill_refiner = SkillRefiner(mcp_client=mock_mcp_client)
        universe_bridge = UniverseBridge(engine=MagicMock(), agent_name="test")

        executor = CompoundExecutor(
            mock_mcp_client,
            enable_guardrails=False,
            inflection_detector=mock_inflection_detector,
            journey_tracker=journey_tracker,
            degradation_detector=degradation_detector,
            retrospection_engine=retrospection_engine,
            skill_refiner=skill_refiner,
            enable_skill_refinement=True,
            universe_bridge=universe_bridge,
        )

        assert executor is not None
        assert executor._journey_tracker is journey_tracker
        assert executor._degradation_detector is degradation_detector
        assert executor._retrospection_engine is retrospection_engine
        assert executor._universe_bridge is universe_bridge

    def test_full_cycle_produces_real_cohesion(self, mock_mcp_client, mock_inflection_detector):
        """Full cycle execution produces real cohesion scores (Phase 1)."""
        executor = CompoundExecutor(
            mock_mcp_client,
            enable_guardrails=False,
            inflection_detector=mock_inflection_detector,
            journey_tracker=JourneyTracker(seed=42),
        )

        def task_fn(guidance):
            return "output", {"quality": 0.9}

        result = executor.execute_task(
            task_description="Test",
            skill_name="test",
            operation_type="generate",
            execute_fn=task_fn,
        )

        assert "coherence" in result.metrics
        # Should be high: success(0.7) + inverse_anomaly(0.9) = 0.8
        assert result.metrics["coherence"] > 0.7

    def test_full_cycle_produces_phi_score(self, mock_mcp_client, mock_inflection_detector):
        """Full cycle execution produces real phi_score (Phase 4)."""
        executor = CompoundExecutor(
            mock_mcp_client,
            enable_guardrails=False,
            inflection_detector=mock_inflection_detector,
            journey_tracker=JourneyTracker(seed=42),
        )

        def task_fn(guidance):
            return "output", {}

        result = executor.execute_task(
            task_description="Test",
            skill_name="test",
            operation_type="generate",
            execute_fn=task_fn,
        )

        assert "phi_score" in result.metrics
        assert result.metrics["phi_score"] > 0.0

    def test_full_cycle_retrospection_gates_refinement(
        self, mock_mcp_client, mock_inflection_detector
    ):
        """Full cycle retrospection gates refinement (Phase 6)."""
        mock_refiner = MagicMock()

        executor = CompoundExecutor(
            mock_mcp_client,
            enable_guardrails=False,
            inflection_detector=mock_inflection_detector,
            retrospection_engine=RetrospectionEngine(),
            skill_refiner=mock_refiner,
            enable_skill_refinement=True,
        )

        def task_fn(guidance):
            return "output", {}

        result = executor.execute_task(
            task_description="Test",
            skill_name="test",
            operation_type="generate",
            execute_fn=task_fn,
        )

        assert "retrospection_insights" in result.metrics
        # Refiner should have been called (retrospection allows it)
        assert mock_refiner.refine.called

    def test_full_cycle_creates_universe_journey(self, mock_mcp_client, mock_inflection_detector):
        """Full cycle creates universe journey (Phase 7)."""
        mock_engine = MagicMock()
        universe_bridge = UniverseBridge(engine=mock_engine, agent_name="test")

        executor = CompoundExecutor(
            mock_mcp_client,
            enable_guardrails=False,
            inflection_detector=mock_inflection_detector,
            journey_tracker=JourneyTracker(seed=42),
            universe_bridge=universe_bridge,
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
        # Bridge should have completed journey (removed from active)
        assert len(universe_bridge._active_journeys) == 0
