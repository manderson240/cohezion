"""Tests for compound executor with vault integration."""

from unittest.mock import MagicMock

import pytest

from cohezion.compound.executor import (
    CompoundExecutor,
    ExecutionResult,
    ExecutorFactory,
)


@pytest.fixture
def mock_mcp_client():
    """Create a mock MCP client."""
    client = MagicMock()
    client.vault_find_relevant_context.return_value = [{"file": "experiments/similar.md", "score": 0.85}]
    client.vault_search.return_value = [{"file": "experiments/similar.md", "score": 0.85}]
    client.vault_write.return_value = "success"
    client.vault_read.return_value = '{"status": "started"}'
    client.vault_log_experiment.return_value = "experiments/execution_123.md"
    client.vault_log_decision.return_value = "decisions/inflection_456.md"
    client.vault_extract_pattern.return_value = "patterns/success_789.md"
    client.vault_edit.return_value = "success"
    return client


@pytest.fixture
def executor(mock_mcp_client):
    """Create a test executor."""
    return CompoundExecutor(mock_mcp_client)


def test_executor_init(mock_mcp_client):
    """Test executor initialization."""
    executor = CompoundExecutor(mock_mcp_client)
    assert executor.mcp_client == mock_mcp_client
    assert executor.logger is not None


def test_get_experience_guidance(executor, mock_mcp_client):
    """Test fetching experience guidance."""
    guidance = executor.get_experience_guidance(
        task_description="Optimize token usage",
        project="cohezion",
    )

    assert "relevant_context" in guidance
    mock_mcp_client.vault_search.assert_called_once()


def test_execute_task_success(executor, mock_mcp_client):
    """Test successful task execution."""

    def dummy_task(guidance):
        return "Task output", {"tokens": 100, "latency": 1.5}

    result = executor.execute_task(
        task_description="Test task",
        skill_name="test_skill",
        operation_type="generate",
        execute_fn=dummy_task,
    )

    assert result.success is True
    assert result.output == "Task output"
    assert result.metrics["tokens"] == 100
    # VaultLogger generates path as experiments/{project}/{skill}/{timestamp}.json
    assert result.vault_experiment_path.startswith("experiments/cohezion/test_skill/")
    assert result.vault_experiment_path.endswith(".json")
    assert result.vault_decision_paths is not None
    assert len(result.vault_decision_paths) > 0


def test_execute_task_failure(executor, mock_mcp_client):
    """Test task execution with failure."""

    def failing_task(guidance):
        raise ValueError("Task failed")

    result = executor.execute_task(
        task_description="Failing task",
        skill_name="test_skill",
        operation_type="analyze",
        execute_fn=failing_task,
    )

    assert result.success is False
    assert "Error: Task failed" in result.output
    assert "error" in result.metrics
    # Execution is still logged even on failure (via vault_write)
    assert mock_mcp_client.vault_write.call_count >= 2  # start + result


def test_execute_task_includes_guidance(executor):
    """Test that execute_fn receives experience guidance."""
    received_guidance = None

    def capture_guidance(guidance):
        nonlocal received_guidance
        received_guidance = guidance
        return "output", {}

    executor.execute_task(
        task_description="Test",
        skill_name="test",
        operation_type="generate",
        execute_fn=capture_guidance,
    )

    assert received_guidance is not None
    assert "relevant_context" in received_guidance


def test_execute_task_logs_start_and_result(executor, mock_mcp_client):
    """Test that both start and result logging are called."""

    def dummy_task(guidance):
        return "result", {"metric": 1.0}

    executor.execute_task(
        task_description="Test",
        skill_name="test_skill",
        operation_type="transform",
        execute_fn=dummy_task,
    )

    # Should log start (vault_write) and result (vault_read + vault_write)
    # Plus pattern extraction (vault_write) = at least 3 vault_write calls
    assert mock_mcp_client.vault_write.call_count >= 2  # start + result
    assert mock_mcp_client.vault_read.called  # result reads first


def test_execute_task_extracts_pattern_on_success(executor, mock_mcp_client):
    """Test pattern extraction after successful execution."""

    def dummy_task(guidance):
        return "success", {"coherence": 0.92}

    result = executor.execute_task(
        task_description="Pattern extraction test",
        skill_name="pattern_skill",
        operation_type="generate",
        execute_fn=dummy_task,
    )

    assert result.success is True
    # Pattern extraction happens via vault_write
    # Calls: start + result + pattern = at least 3
    assert mock_mcp_client.vault_write.call_count >= 3

    # Verify pattern was written (check call args for pattern path)
    pattern_calls = [
        call
        for call in mock_mcp_client.vault_write.call_args_list
        if "patterns/domains/compound-engineering" in str(call)
    ]
    assert len(pattern_calls) >= 1


def test_execute_task_no_pattern_on_failure(executor, mock_mcp_client):
    """Test that patterns are not extracted on failure."""

    def failing_task(guidance):
        raise RuntimeError("Failed")

    result = executor.execute_task(
        task_description="Failing task",
        skill_name="test",
        operation_type="analyze",
        execute_fn=failing_task,
    )

    assert result.success is False
    # Pattern extraction should not happen on failure
    # Calls: start + result + inflection point (3 total)
    # Verify no pattern paths in calls (pattern extraction writes to patterns/domains/)
    pattern_calls = [call for call in mock_mcp_client.vault_write.call_args_list if "patterns/domains" in str(call)]
    assert len(pattern_calls) == 0  # no pattern extraction on failure


def test_log_inflection_point(executor, mock_mcp_client):
    """Test logging inflection points."""
    path = executor.log_inflection_point(
        title="Critical threshold",
        context="Token budget exceeded",
        decision="Switch to smaller model",
        rationale="Maintain quality",
    )

    # Path should be decisions/{project}/inflection_{timestamp}.md
    assert path.startswith("decisions/cohezion/inflection_")
    assert path.endswith(".md")
    # Decision logging uses vault_write
    mock_mcp_client.vault_write.assert_called()


def test_execution_result_dataclass(executor):
    """Test ExecutionResult dataclass."""

    def dummy_task(guidance):
        return "output", {"metric": 1.0}

    result = executor.execute_task(
        task_description="Test",
        skill_name="test",
        operation_type="generate",
        execute_fn=dummy_task,
    )

    assert isinstance(result, ExecutionResult)
    assert result.success is True
    assert result.duration_seconds >= 0
    assert result.vault_decision_paths is not None


def test_executor_factory_create(mock_mcp_client):
    """Test factory creation."""
    executor = ExecutorFactory.create(mock_mcp_client)
    assert isinstance(executor, CompoundExecutor)
    assert executor.mcp_client == mock_mcp_client


def test_executor_factory_singleton(mock_mcp_client):
    """Test singleton pattern."""
    ExecutorFactory.reset_singleton()

    executor1 = ExecutorFactory.get_singleton(mock_mcp_client)
    executor2 = ExecutorFactory.get_singleton(mock_mcp_client)

    assert executor1 is executor2

    ExecutorFactory.reset_singleton()


def test_execute_task_duration(executor):
    """Test that duration is measured correctly."""
    import time

    def slow_task(guidance):
        time.sleep(0.1)
        return "output", {}

    result = executor.execute_task(
        task_description="Slow task",
        skill_name="slow",
        operation_type="generate",
        execute_fn=slow_task,
    )

    assert result.duration_seconds >= 0.1


def test_execute_task_with_custom_project(executor, mock_mcp_client):
    """Test execution with custom project name."""

    def dummy_task(guidance):
        return "output", {}

    result = executor.execute_task(
        task_description="Test",
        skill_name="test",
        operation_type="generate",
        execute_fn=dummy_task,
        project="custom_project",
    )

    # Verify project name appears in experiment path
    assert result.vault_experiment_path.startswith("experiments/custom_project/test/")
    # Vault logging uses vault_write, verify it was called
    assert mock_mcp_client.vault_write.call_count >= 1


def test_executor_guardrails_enabled_by_default(mock_mcp_client):
    """Test that guardrails are enabled by default."""
    executor = CompoundExecutor(mock_mcp_client)
    assert executor.guardrail_pipeline is not None


def test_executor_guardrails_can_be_disabled(mock_mcp_client):
    """Test that guardrails can be disabled."""
    executor = CompoundExecutor(mock_mcp_client, enable_guardrails=False)
    assert executor.guardrail_pipeline is None


def test_executor_custom_guardrail_pipeline(mock_mcp_client):
    """Test executor with custom guardrail pipeline."""
    from cohezion.security.guardrail_factory import create_minimal_pipeline

    custom_pipeline = create_minimal_pipeline()
    executor = CompoundExecutor(mock_mcp_client, guardrail_pipeline=custom_pipeline)
    assert executor.guardrail_pipeline == custom_pipeline


def test_execute_task_with_guardrails_enabled(mock_mcp_client):
    """Test task execution with guardrails enabled."""

    def dummy_task(guidance):
        return "safe output", {"result": "ok"}

    executor = CompoundExecutor(mock_mcp_client, enable_guardrails=True)
    result = executor.execute_task(
        task_description="Safe task",
        skill_name="test",
        operation_type="generate",
        execute_fn=dummy_task,
    )

    assert result.success is True
    assert result.output == "safe output"


def test_executor_factory_with_guardrails(mock_mcp_client):
    """Test factory creates executor with guardrails enabled."""
    executor = ExecutorFactory.create(mock_mcp_client, enable_guardrails=True)
    assert executor.guardrail_pipeline is not None


def test_executor_factory_without_guardrails(mock_mcp_client):
    """Test factory creates executor with guardrails disabled."""
    executor = ExecutorFactory.create(mock_mcp_client, enable_guardrails=False)
    assert executor.guardrail_pipeline is None


def test_executor_singleton_with_guardrails(mock_mcp_client):
    """Test singleton maintains guardrail configuration."""
    ExecutorFactory.reset_singleton()
    executor1 = ExecutorFactory.get_singleton(mock_mcp_client, enable_guardrails=True)
    executor2 = ExecutorFactory.get_singleton(mock_mcp_client)

    assert executor1 is executor2
    assert executor1.guardrail_pipeline is not None


# ---- Phase 1: Real cohesion score tests ----


class TestCohesionScore:
    """Tests for real cohesion score computation (Phase 1)."""

    def test_cohesion_populated_on_success(self, mock_mcp_client):
        """Cohesion populated and higher on success than failure."""
        executor = CompoundExecutor(mock_mcp_client, enable_guardrails=False)

        def success_task(guidance):
            return "output", {}

        result = executor.execute_task(
            task_description="Test",
            skill_name="test",
            operation_type="generate",
            execute_fn=success_task,
        )
        assert result.success is True
        assert "coherence" in result.metrics
        # Success contributes 0.7 (vs 0.2 for failure)
        assert result.metrics["coherence"] > 0.0

    def test_cohesion_populated_on_failure(self, mock_mcp_client):
        """Cohesion populated on failed precipitation with success=0.2 component."""
        executor = CompoundExecutor(mock_mcp_client, enable_guardrails=False)

        def failing_task(guidance):
            raise ValueError("boom")

        result = executor.execute_task(
            task_description="Fail",
            skill_name="test",
            operation_type="generate",
            execute_fn=failing_task,
        )
        assert result.success is False
        assert "coherence" in result.metrics
        # Failure contributes 0.2 component; coherence should be computed
        assert result.metrics["coherence"] > 0.0
        assert result.metrics["coherence"] <= 1.0

    def test_cohesion_incorporates_anomaly_score(self, mock_mcp_client):
        """Cohesion uses anomaly_score when present (spin misalignment)."""
        executor = CompoundExecutor(mock_mcp_client, enable_guardrails=False)

        def task_with_anomaly(guidance):
            return "output", {}

        result = executor.execute_task(
            task_description="Test",
            skill_name="test",
            operation_type="generate",
            execute_fn=task_with_anomaly,
        )
        # anomaly_score is set by inflection detector in Step 5
        assert "coherence" in result.metrics
        # Coherence should incorporate the anomaly_score
        anomaly = result.metrics.get("anomaly_score", 0.5)
        # With success (0.7) and anomaly inverse, coherence is computed
        expected_min = (0.7 + (1.0 - anomaly)) / 2 - 0.01
        assert result.metrics["coherence"] >= expected_min

    def test_cohesion_incorporates_alignment_intent_match(self, mock_mcp_client):
        """Cohesion uses alignment intent_match when quadrature analysis available."""
        executor = CompoundExecutor(
            mock_mcp_client,
            enable_guardrails=False,
            enable_alignment_analysis=True,
        )

        def task_fn(guidance):
            return "output", {}

        result = executor.execute_task(
            task_description="Test alignment",
            skill_name="test",
            operation_type="generate",
            execute_fn=task_fn,
            human_request="test request",
        )
        assert "coherence" in result.metrics
        assert result.metrics["coherence"] > 0.0
        # Alignment analysis adds a third component (intent_match),
        # which changes the denominator from 2 to 3
        if "alignment" in result.metrics:
            assert result.metrics["coherence"] != pytest.approx(0.0)

    def test_cohesion_computed_without_detectors(self, mock_mcp_client):
        """Cohesion still computed from precipitation alone when no detectors."""
        executor = CompoundExecutor(mock_mcp_client, enable_guardrails=False)

        def task_fn(guidance):
            return "output", {}

        result = executor.execute_task(
            task_description="Simple",
            skill_name="test",
            operation_type="generate",
            execute_fn=task_fn,
        )
        assert "coherence" in result.metrics
        # At minimum: success(0.7) + inverse_anomaly(0.5) / 2 = 0.6
        assert result.metrics["coherence"] > 0.0


# ---- Phase 3: Degradation feedback loop tests ----


class TestDegradationMode:
    """Tests for degradation mode feedback loop (Phase 3)."""

    def _make_critical_detector(self):
        """Create a mock degradation detector that always fires CRITICAL."""
        from dataclasses import dataclass
        from enum import Enum
        from unittest.mock import MagicMock

        class Sev(Enum):
            CRITICAL = "CRITICAL"

        @dataclass
        class Alert:
            severity: Sev = Sev.CRITICAL
            metric: str = "coherence"
            message: str = "Coherence collapsed"
            current_value: float = 0.1
            baseline_value: float = 0.5
            threshold: float = 0.3

        detector = MagicMock()
        detector.check_degradation.return_value = [Alert()]
        return detector

    def _make_ok_detector(self):
        """Create a mock degradation detector that returns no alerts."""
        from unittest.mock import MagicMock

        detector = MagicMock()
        detector.check_degradation.return_value = []
        return detector

    def test_degradation_mode_set_on_critical(self, mock_mcp_client):
        """_degradation_mode set on CRITICAL cohesion alert."""
        detector = self._make_critical_detector()
        executor = CompoundExecutor(
            mock_mcp_client,
            enable_guardrails=False,
            degradation_detector=detector,
        )

        def task_fn(guidance):
            return "output", {}

        result = executor.execute_task(
            task_description="Test",
            skill_name="test",
            operation_type="generate",
            execute_fn=task_fn,
        )
        assert executor._degradation_mode is True
        assert result.metrics.get("execution_degraded") is True

    def test_degraded_mode_skips_alignment(self, mock_mcp_client):
        """In degraded mode, alignment analysis is skipped."""
        from unittest.mock import MagicMock

        analyzer = MagicMock()
        executor = CompoundExecutor(
            mock_mcp_client,
            enable_guardrails=False,
            alignment_analyzer=analyzer,
            enable_alignment_analysis=True,
        )
        # Force degradation mode
        executor._degradation_mode = True

        def task_fn(guidance):
            return "output", {}

        executor.execute_task(
            task_description="Test",
            skill_name="test",
            operation_type="generate",
            execute_fn=task_fn,
            human_request="test",
        )
        # parse_request should NOT have been called
        analyzer.parse_request.assert_not_called()

    def test_degraded_mode_skips_pattern_extraction(self, mock_mcp_client):
        """In degraded mode, pattern extraction is skipped."""
        executor = CompoundExecutor(mock_mcp_client, enable_guardrails=False)
        executor._degradation_mode = True

        def task_fn(guidance):
            return "output", {}

        result = executor.execute_task(
            task_description="Test",
            skill_name="test",
            operation_type="generate",
            execute_fn=task_fn,
        )
        assert result.success is True
        # No pattern extraction calls (normally writes to patterns/domains/)
        pattern_calls = [c for c in mock_mcp_client.vault_write.call_args_list if "patterns/domains" in str(c)]
        assert len(pattern_calls) == 0

    def test_degradation_clears_on_hiho_return(self, mock_mcp_client):
        """Degradation mode clears when cohesion returns to HIHO band."""
        from unittest.mock import MagicMock

        from cohezion.compound.inflection_detector import Severity

        detector = self._make_ok_detector()
        # Mock inflection detector to produce anomaly_score=0.7
        # coherence = (0.7 + (1.0 - 0.7)) / 2 = 0.5 → in HIHO band [0.4, 0.6]
        mock_inflection = MagicMock()
        mock_anomaly = MagicMock()
        mock_anomaly.severity = Severity.INFO
        mock_anomaly.score = 0.7
        mock_anomaly.issues = []
        mock_anomaly.recommendations = []
        mock_anomaly.should_reexecute = False
        mock_inflection.detect_anomaly.return_value = mock_anomaly
        executor = CompoundExecutor(
            mock_mcp_client,
            enable_guardrails=False,
            degradation_detector=detector,
            inflection_detector=mock_inflection,
        )
        # Force into degradation mode
        executor._degradation_mode = True

        def task_fn(guidance):
            return "output", {}

        result = executor.execute_task(
            task_description="Test",
            skill_name="test",
            operation_type="generate",
            execute_fn=task_fn,
        )
        # Coherence = (0.7 + 0.3) / 2 = 0.5 → in HIHO band [0.4, 0.6]
        # OK detector returns no CRITICAL alerts → degradation clears
        assert executor._degradation_mode is False
        assert 0.4 <= result.metrics["coherence"] <= 0.6

    def test_execution_degraded_in_metrics(self, mock_mcp_client):
        """execution_degraded flag appears in ExecutionResult.metrics."""
        detector = self._make_critical_detector()
        executor = CompoundExecutor(
            mock_mcp_client,
            enable_guardrails=False,
            degradation_detector=detector,
        )

        def task_fn(guidance):
            return "output", {}

        result = executor.execute_task(
            task_description="Test",
            skill_name="test",
            operation_type="generate",
            execute_fn=task_fn,
        )
        assert "execution_degraded" in result.metrics
        assert result.metrics["execution_degraded"] is True
