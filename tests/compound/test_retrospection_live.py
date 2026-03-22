"""Tests for RetrospectionEngine analyzing live ExecutionResults (Phase 6).

Validates the closed compound loop: execute -> measure -> retrospect -> gate refinement.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from cohezion.compound.executor import CompoundExecutor, ExecutionResult
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


class TestRetrospectionLive:
    """Tests for analyze_execution_result (Phase 6)."""

    def test_analyze_extracts_insights(self):
        """analyze_execution_result extracts insights from ExecutionResult."""
        engine = RetrospectionEngine()
        result = ExecutionResult(
            success=True,
            output="test output",
            metrics={"coherence": 0.75, "anomaly_score": 0.2},
            duration_seconds=1.5,
        )

        analysis = engine.analyze_execution_result(result, "test_skill")

        assert "insights" in analysis
        assert len(analysis["insights"]) > 0
        assert "compound_score" in analysis
        assert analysis["compound_score"] > 0.0

    def test_low_coherence_returns_no_refine(self):
        """Low cohesion execution (HIHO violation) returns should_refine=False."""
        engine = RetrospectionEngine()
        result = ExecutionResult(
            success=True,
            output="test output",
            metrics={"coherence": 0.2, "anomaly_score": 0.8},
            duration_seconds=1.0,
        )

        analysis = engine.analyze_execution_result(result, "test_skill")

        assert analysis["should_refine"] is False

    def test_executor_calls_retrospection(self, mock_mcp_client):
        """Executor calls retrospection after execution when configured."""
        engine = RetrospectionEngine()

        executor = CompoundExecutor(
            mock_mcp_client,
            enable_guardrails=False,
            retrospection_engine=engine,
        )

        def task_fn(guidance):
            return "output", {}

        result = executor.execute_task(
            task_description="Test task",
            skill_name="test",
            operation_type="generate",
            execute_fn=task_fn,
        )

        # Retrospection insights should appear in metrics
        assert "retrospection_insights" in result.metrics
        assert len(result.metrics["retrospection_insights"]) > 0

    def test_retrospection_gates_refinement_on_failure(self, mock_mcp_client):
        """Retrospection gates refinement: failed execution -> no refinement."""
        engine = RetrospectionEngine()

        mock_refiner = MagicMock()
        mock_refiner.refine.return_value = None

        executor = CompoundExecutor(
            mock_mcp_client,
            enable_guardrails=False,
            skill_refiner=mock_refiner,
            enable_skill_refinement=True,
            retrospection_engine=engine,
        )

        def failing_task(guidance):
            raise ValueError("boom")

        executor.execute_task(
            task_description="Test task",
            skill_name="test",
            operation_type="generate",
            execute_fn=failing_task,
        )

        # Refiner should NOT have been called (retrospection blocks it)
        assert not mock_refiner.refine.called

    def test_degraded_execution_produces_investigation_recommendation(self):
        """Degraded execution produces investigation recommendation."""
        engine = RetrospectionEngine()
        result = ExecutionResult(
            success=True,
            output="output",
            metrics={
                "coherence": 0.3,
                "anomaly_score": 0.6,
                "execution_degraded": True,
            },
            duration_seconds=2.0,
        )

        analysis = engine.analyze_execution_result(result, "test_skill")

        assert analysis["should_refine"] is False
        assert (
            "degradation" in analysis["recommendation"].lower() or "investigate" in analysis["recommendation"].lower()
        )
        assert analysis["degraded"] is True
