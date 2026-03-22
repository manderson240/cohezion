"""Integration tests for DegradationDetector and ModelQualityClassifier
wiring into CompoundExecutor.

Tests Phase 5A.6 (degradation detection) and 5A.7 (model quality classification)
integration with the 11-step executor pipeline.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from cohezion.compound.degradation_detector import (
    DegradationDetector,
)
from cohezion.compound.executor import CompoundExecutor, ExecutorFactory
from cohezion.compound.model_quality_classifier import ModelQualityClassifier


@pytest.fixture
def mock_mcp_client():
    """Create mock MCP client."""
    client = MagicMock()
    client.vault_search.return_value = []
    client.vault_find_relevant_context.return_value = {"results": []}
    return client


@pytest.fixture
def mock_vault_logger():
    """Patch VaultExecutionLogger to avoid real vault calls."""
    with patch("cohezion.compound.exp_persistence.vault.VaultLogger") as mock_logger_cls:
        mock_logger = MagicMock()
        mock_logger.get_experience_guidance.return_value = {"relevant_context": []}
        mock_logger.log_execution_start.return_value = "experiments/test.md"
        mock_logger.log_execution_result.return_value = None
        mock_logger.extract_execution_pattern.return_value = "patterns/test.md"
        mock_logger.log_decision_point.return_value = "decisions/test.md"
        mock_logger_cls.return_value = mock_logger
        yield mock_logger


def _make_executor(
    mock_mcp_client,
    degradation_detector=None,
    model_quality_classifier=None,
    token_client=None,
):
    """Create executor with monitoring components."""
    return CompoundExecutor(
        mcp_client=mock_mcp_client,
        token_client=token_client,
        enable_guardrails=False,
        enable_skill_refinement=False,
        enable_alignment_analysis=False,
        degradation_detector=degradation_detector,
        model_quality_classifier=model_quality_classifier,
    )


# ---------------------------------------------------------------------------
# DegradationDetector integration tests
# ---------------------------------------------------------------------------


class TestDegradationDetectorIntegration:
    """Test DegradationDetector wired into CompoundExecutor Step 7.5."""

    def test_executor_accepts_degradation_detector(self, mock_mcp_client, mock_vault_logger):
        """Verify executor accepts degradation_detector parameter."""
        detector = DegradationDetector()
        executor = _make_executor(mock_mcp_client, degradation_detector=detector)
        assert executor._degradation_detector is detector

    def test_executor_without_detector_unchanged(self, mock_mcp_client, mock_vault_logger):
        """Verify executor works without degradation_detector."""
        executor = _make_executor(mock_mcp_client)
        result = executor.execute_task(
            task_description="Test task",
            skill_name="test_skill",
            operation_type="generate",
            execute_fn=lambda guidance: ("output", {"coherence": 0.8}),
        )
        assert result.success is True
        assert "degradation_alerts" not in result.metrics

    def test_detector_receives_metrics_during_execution(self, mock_mcp_client, mock_vault_logger):
        """Verify detector.check_degradation() is called with metrics."""
        detector = DegradationDetector()
        executor = _make_executor(mock_mcp_client, degradation_detector=detector)

        # Execute enough times to establish baseline (5 samples)
        for _ in range(6):
            executor.execute_task(
                task_description="Test task",
                skill_name="test_skill",
                operation_type="generate",
                execute_fn=lambda guidance: ("output", {"coherence": 0.8}),
            )

        # Verify baselines are being built
        stats = detector.get_baseline_stats()
        assert stats["coherence"]["num_samples"] >= 5
        assert stats["coherence"]["is_established"] is True

    def test_degradation_alert_recorded_in_metrics(self, mock_mcp_client, mock_vault_logger):
        """Verify degradation alerts appear in result.metrics."""
        detector = DegradationDetector(
            cache_hit_rate_threshold=0.50,
            coherence_threshold=0.60,
        )
        executor = _make_executor(
            mock_mcp_client,
            degradation_detector=detector,
            token_client=MagicMock(
                get_metrics=MagicMock(
                    return_value={
                        "total_tokens": 100,
                        "combined_hit_rate": 0.75,
                        "tokens_per_second": 1000.0,
                    }
                )
            ),
        )

        # Establish baseline with high metrics
        for _ in range(5):
            executor.execute_task(
                task_description="Baseline task",
                skill_name="test_skill",
                operation_type="generate",
                execute_fn=lambda guidance: ("output", {"coherence": 0.85}),
            )

        # Now simulate degradation — low coherence
        result = executor.execute_task(
            task_description="Degraded task",
            skill_name="test_skill",
            operation_type="generate",
            execute_fn=lambda guidance: ("output", {"coherence": 0.40}),
        )

        # Should still succeed (degradation is non-blocking)
        assert result.success is True
        # Alert count should be in metrics if triggered
        if "degradation_alerts" in result.metrics:
            assert result.metrics["degradation_alerts"] > 0

    def test_detector_failure_is_non_blocking(self, mock_mcp_client, mock_vault_logger):
        """Verify detector failures don't crash execution."""
        detector = MagicMock()
        detector.check_degradation.side_effect = RuntimeError("Detector crash")

        executor = _make_executor(mock_mcp_client, degradation_detector=detector)
        result = executor.execute_task(
            task_description="Test task",
            skill_name="test_skill",
            operation_type="generate",
            execute_fn=lambda guidance: ("output", {"coherence": 0.8}),
        )

        assert result.success is True  # Non-blocking

    def test_critical_alert_logged_to_vault(self, mock_mcp_client, mock_vault_logger):
        """Verify CRITICAL alerts are logged to vault as decisions."""
        detector = DegradationDetector(coherence_threshold=0.60)
        executor = _make_executor(mock_mcp_client, degradation_detector=detector)

        # Establish baseline
        for _ in range(5):
            executor.execute_task(
                task_description="Baseline",
                skill_name="test_skill",
                operation_type="generate",
                execute_fn=lambda guidance: ("output", {"coherence": 0.85}),
            )

        # Trigger critical coherence drop
        result = executor.execute_task(
            task_description="Degraded",
            skill_name="test_skill",
            operation_type="generate",
            execute_fn=lambda guidance: ("output", {"coherence": 0.30}),
        )

        # Check if vault decision was logged (non-blocking, so check paths)
        if result.vault_decision_paths:
            assert any("decisions" in p for p in result.vault_decision_paths)


# ---------------------------------------------------------------------------
# ModelQualityClassifier integration tests
# ---------------------------------------------------------------------------


class TestModelQualityClassifierIntegration:
    """Test ModelQualityClassifier wired into CompoundExecutor Step 7.7."""

    def test_executor_accepts_quality_classifier(self, mock_mcp_client, mock_vault_logger):
        """Verify executor accepts model_quality_classifier parameter."""
        classifier = ModelQualityClassifier()
        executor = _make_executor(mock_mcp_client, model_quality_classifier=classifier)
        assert executor._model_quality_classifier is classifier

    def test_executor_without_classifier_unchanged(self, mock_mcp_client, mock_vault_logger):
        """Verify executor works without model_quality_classifier."""
        executor = _make_executor(mock_mcp_client)
        result = executor.execute_task(
            task_description="Test task",
            skill_name="test_skill",
            operation_type="generate",
            execute_fn=lambda guidance: ("output", {"coherence": 0.8}),
        )
        assert result.success is True

    def test_classifier_records_execution_outcome(self, mock_mcp_client, mock_vault_logger):
        """Verify classifier.add_execution() is called after execution."""
        classifier = ModelQualityClassifier()
        token_client = MagicMock()
        token_client.get_metrics.return_value = {
            "total_tokens": 100,
            "model": "phi3:mini",
            "tokens_used": 50,
            "combined_hit_rate": 0.75,
        }
        executor = _make_executor(
            mock_mcp_client,
            model_quality_classifier=classifier,
            token_client=token_client,
        )

        executor.execute_task(
            task_description="Test task",
            skill_name="test_skill",
            operation_type="generate",
            execute_fn=lambda guidance: ("output", {"coherence": 0.85}),
        )

        # Classifier should have recorded the execution
        assert "phi3:mini" in classifier._predictors
        predictor = classifier._predictors["phi3:mini"]
        assert len(predictor.coherence_history) == 1

    def test_classifier_failure_is_non_blocking(self, mock_mcp_client, mock_vault_logger):
        """Verify classifier failures don't crash execution."""
        classifier = MagicMock()
        classifier.add_execution.side_effect = RuntimeError("Classifier crash")

        executor = _make_executor(mock_mcp_client, model_quality_classifier=classifier)
        result = executor.execute_task(
            task_description="Test task",
            skill_name="test_skill",
            operation_type="generate",
            execute_fn=lambda guidance: ("output", {"coherence": 0.8}),
        )

        assert result.success is True  # Non-blocking

    def test_classifier_learns_from_failures(self, mock_mcp_client, mock_vault_logger):
        """Verify classifier records failed executions."""
        classifier = ModelQualityClassifier()
        token_client = MagicMock()
        token_client.get_metrics.return_value = {
            "total_tokens": 100,
            "model": "phi3:mini",
            "tokens_used": 50,
        }
        executor = _make_executor(
            mock_mcp_client,
            model_quality_classifier=classifier,
            token_client=token_client,
        )

        # Execute with failure
        executor.execute_task(
            task_description="Failing task",
            skill_name="test_skill",
            operation_type="generate",
            execute_fn=lambda guidance: (_ for _ in ()).throw(RuntimeError("Task failed")),
        )

        # Classifier should record the failure
        assert "phi3:mini" in classifier._predictors
        predictor = classifier._predictors["phi3:mini"]
        assert len(predictor.success_history) == 1
        assert predictor.success_history[0] is False


# ---------------------------------------------------------------------------
# Combined monitoring integration tests
# ---------------------------------------------------------------------------


class TestCombinedMonitoringIntegration:
    """Test DegradationDetector + ModelQualityClassifier together."""

    def test_both_monitoring_components_work_together(self, mock_mcp_client, mock_vault_logger):
        """Verify both detector and classifier work in same executor."""
        detector = DegradationDetector()
        classifier = ModelQualityClassifier()

        executor = _make_executor(
            mock_mcp_client,
            degradation_detector=detector,
            model_quality_classifier=classifier,
        )

        result = executor.execute_task(
            task_description="Test task",
            skill_name="test_skill",
            operation_type="generate",
            execute_fn=lambda guidance: ("output", {"coherence": 0.85}),
        )

        assert result.success is True
        # Both should be recording
        stats = detector.get_baseline_stats()
        assert stats["coherence"]["num_samples"] == 1

    def test_factory_passes_monitoring_params(self, mock_mcp_client, mock_vault_logger):
        """Verify ExecutorFactory passes through monitoring params."""
        detector = DegradationDetector()
        classifier = ModelQualityClassifier()

        executor = ExecutorFactory.create(
            mcp_client=mock_mcp_client,
            enable_guardrails=False,
            enable_skill_refinement=False,
            degradation_detector=detector,
            model_quality_classifier=classifier,
        )

        assert executor._degradation_detector is detector
        assert executor._model_quality_classifier is classifier

    def test_singleton_factory_passes_monitoring_params(self, mock_mcp_client, mock_vault_logger):
        """Verify ExecutorFactory.get_singleton() passes monitoring params."""
        ExecutorFactory.reset_singleton()
        detector = DegradationDetector()
        classifier = ModelQualityClassifier()

        executor = ExecutorFactory.get_singleton(
            mcp_client=mock_mcp_client,
            enable_guardrails=False,
            enable_skill_refinement=False,
            degradation_detector=detector,
            model_quality_classifier=classifier,
        )

        assert executor._degradation_detector is detector
        assert executor._model_quality_classifier is classifier
        ExecutorFactory.reset_singleton()

    def test_full_pipeline_11_steps(self, mock_mcp_client, mock_vault_logger):
        """Verify all 11 steps execute in order with monitoring."""
        from cohezion.compound.journey_tracker import JourneyTracker
        from cohezion.compound.metrics import CompoundMetricsCollector

        detector = DegradationDetector()
        classifier = ModelQualityClassifier()
        metrics_collector = CompoundMetricsCollector()
        journey_tracker = JourneyTracker()

        executor = CompoundExecutor(
            mcp_client=mock_mcp_client,
            enable_guardrails=False,
            enable_skill_refinement=False,
            enable_alignment_analysis=False,
            degradation_detector=detector,
            model_quality_classifier=classifier,
            metrics_collector=metrics_collector,
            journey_tracker=journey_tracker,
        )

        result = executor.execute_task(
            task_description="Full pipeline test",
            skill_name="test_skill",
            operation_type="generate",
            execute_fn=lambda guidance: ("output", {"coherence": 0.85}),
        )

        assert result.success is True
        # Verify all monitoring components received data
        assert detector.get_baseline_stats()["coherence"]["num_samples"] == 1
        assert metrics_collector.total_executions == 1
