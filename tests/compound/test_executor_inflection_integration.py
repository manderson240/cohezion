"""Tests for CompoundExecutor integration with InflectionDetector."""

from unittest.mock import MagicMock, patch

import pytest

from cohezion.compound.executor import CompoundExecutor, ExecutionResult, ExecutorFactory
from cohezion.compound.inflection_detector import (
    InflectionDetector,
    InflectionDetectorFactory,
)


@pytest.fixture
def mock_mcp_client():
    """Create mock MCP client."""
    return MagicMock()


@pytest.fixture
def mock_detector():
    """Create mock inflection detector."""
    return MagicMock(spec=InflectionDetector)


@pytest.fixture
def detector():
    """Create real inflection detector for integration tests."""
    return InflectionDetectorFactory.create_default()


@pytest.fixture
def executor(mock_mcp_client):
    """Create compound executor with default detector."""
    with patch("cohezion.compound.exp_persistence.vault.VaultLogger"):
        return CompoundExecutor(mock_mcp_client)


@pytest.fixture
def executor_with_detector(mock_mcp_client, detector):
    """Create compound executor with custom detector."""
    with patch("cohezion.compound.exp_persistence.vault.VaultLogger"):
        return CompoundExecutor(mock_mcp_client, inflection_detector=detector)


class TestExecutorInflectionIntegration:
    """Tests for InflectionDetector integration with CompoundExecutor."""

    def test_executor_has_default_detector(self, mock_mcp_client):
        """Test executor initializes with default detector."""
        with patch("cohezion.compound.exp_persistence.vault.VaultLogger"):
            executor = CompoundExecutor(mock_mcp_client)
            assert executor.inflection_detector is not None
            assert isinstance(executor.inflection_detector, InflectionDetector)

    def test_executor_uses_custom_detector(self, mock_mcp_client, detector):
        """Test executor uses provided custom detector."""
        with patch("cohezion.compound.exp_persistence.vault.VaultLogger"):
            executor = CompoundExecutor(mock_mcp_client, inflection_detector=detector)
            assert executor.inflection_detector is detector

    def test_successful_execution_adds_anomaly_metrics(self, executor):
        """Test successful execution includes anomaly metrics in result."""
        with (
            patch.object(
                executor.logger,
                "get_experience_guidance",
                return_value={"context": "test"},
            ),
            patch.object(executor.logger, "log_execution_start", return_value="exp_path"),
            patch.object(executor.logger, "log_execution_result"),
            patch.object(executor.logger, "extract_execution_pattern", return_value="pattern_path"),
        ):

            def execute_fn(guidance):
                return "output", {"coherence": 0.8}

            result = executor.execute_task(
                task_description="Test task",
                skill_name="test_skill",
                operation_type="generate",
                execute_fn=execute_fn,
            )

            assert result.success
            assert "anomaly_severity" in result.metrics
            assert "anomaly_score" in result.metrics
            assert result.metrics["anomaly_severity"] == "info"
            assert result.metrics["anomaly_score"] > 0.7

    def test_low_coherence_execution_triggers_warning(self, executor):
        """Test low coherence execution is flagged as warning."""
        with (
            patch.object(
                executor.logger,
                "get_experience_guidance",
                return_value={"context": "test"},
            ),
            patch.object(executor.logger, "log_execution_start", return_value="exp_path"),
            patch.object(executor.logger, "log_execution_result"),
            patch.object(executor.logger, "extract_execution_pattern", return_value="pattern_path"),
        ):

            def execute_fn(guidance):
                return "output", {"coherence": 0.15}  # Below threshold

            result = executor.execute_task(
                task_description="Test task",
                skill_name="test_skill",
                operation_type="generate",
                execute_fn=execute_fn,
            )

            assert result.success
            assert result.metrics["anomaly_severity"] == "warning"
            assert result.metrics["anomaly_score"] < 0.75

    def test_failed_execution_detected_as_anomaly(self, executor):
        """Test failed execution is detected as anomaly."""
        with (
            patch.object(
                executor.logger,
                "get_experience_guidance",
                return_value={"context": "test"},
            ),
            patch.object(executor.logger, "log_execution_start", return_value="exp_path"),
            patch.object(executor.logger, "log_execution_result"),
        ):

            def execute_fn(guidance):
                raise ValueError("Task failed")

            result = executor.execute_task(
                task_description="Failing task",
                skill_name="test_skill",
                operation_type="generate",
                execute_fn=execute_fn,
            )

            assert not result.success
            # Single failure with low score triggers CRITICAL (score < 0.6)
            assert result.metrics["anomaly_severity"] == "critical"
            assert result.metrics["anomaly_score"] < 0.6

    def test_critical_severity_logs_inflection_point(self, executor):
        """Test critical anomaly logs inflection point to vault."""
        with (
            patch.object(
                executor.logger,
                "get_experience_guidance",
                return_value={"context": "test"},
            ),
            patch.object(executor.logger, "log_execution_start", return_value="exp_path"),
            patch.object(executor.logger, "log_execution_result"),
            patch.object(
                executor, "log_inflection_point", return_value="decision_path"
            ) as mock_log_inflection,
        ):
            # Simulate consecutive failures to trigger critical
            for _ in range(3):
                executor.inflection_detector.detect_anomaly(
                    ExecutionResult(
                        success=False,
                        output="Error",
                        metrics={},
                        duration_seconds=0.5,
                    )
                )

            def execute_fn(guidance):
                raise ValueError("Task failed")

            result = executor.execute_task(
                task_description="Failing task",
                skill_name="test_skill",
                operation_type="generate",
                execute_fn=execute_fn,
            )

            assert not result.success
            assert result.metrics["anomaly_severity"] == "critical"
            # Should have called log_inflection_point
            assert mock_log_inflection.called

    def test_inflection_point_includes_anomaly_details(self, executor):
        """Test inflection point logging captures anomaly details."""
        with (
            patch.object(
                executor.logger,
                "get_experience_guidance",
                return_value={"context": "test"},
            ),
            patch.object(executor.logger, "log_execution_start", return_value="exp_path"),
            patch.object(executor.logger, "log_execution_result"),
            patch.object(
                executor, "log_inflection_point", return_value="decision_path"
            ) as mock_log_inflection,
        ):
            # Trigger critical condition
            for _ in range(3):
                executor.inflection_detector.detect_anomaly(
                    ExecutionResult(
                        success=False,
                        output="Error",
                        metrics={},
                        duration_seconds=0.5,
                    )
                )

            def execute_fn(guidance):
                raise ValueError("Task failed")

            executor.execute_task(
                task_description="Critical task",
                skill_name="critical_skill",
                operation_type="transform",
                execute_fn=execute_fn,
            )

            # Verify inflection point was logged with correct context
            if mock_log_inflection.called:
                call_kwargs = mock_log_inflection.call_args.kwargs
                assert "critical" in call_kwargs["title"].lower()
                assert "critical_skill" in call_kwargs["title"]
                assert "Critical task" in call_kwargs["context"]
                assert "Re-execution" in call_kwargs["decision"]

    def test_detector_state_persists_across_executions(self, detector):
        """Test detector state tracks failures across executions."""
        mock_client = MagicMock()
        with patch("cohezion.compound.exp_persistence.vault.VaultLogger"):
            executor = CompoundExecutor(mock_client, inflection_detector=detector)

        # First execution fails
        with (
            patch.object(
                executor.logger,
                "get_experience_guidance",
                return_value={"context": "test"},
            ),
            patch.object(executor.logger, "log_execution_start", return_value="exp_path"),
            patch.object(executor.logger, "log_execution_result"),
        ):

            def execute_fn_1(guidance):
                raise ValueError("Fail 1")

            result1 = executor.execute_task(
                task_description="Task 1",
                skill_name="skill",
                operation_type="generate",
                execute_fn=execute_fn_1,
            )

            # First failure with low score triggers CRITICAL
            assert result1.metrics["anomaly_severity"] == "critical"
            assert detector.consecutive_failures == 1

        # Second execution fails
        with (
            patch.object(
                executor.logger,
                "get_experience_guidance",
                return_value={"context": "test"},
            ),
            patch.object(executor.logger, "log_execution_start", return_value="exp_path"),
            patch.object(executor.logger, "log_execution_result"),
        ):

            def execute_fn_2(guidance):
                raise ValueError("Fail 2")

            result2 = executor.execute_task(
                task_description="Task 2",
                skill_name="skill",
                operation_type="analyze",
                execute_fn=execute_fn_2,
            )

            # Second failure is also CRITICAL (single failures with low score)
            assert result2.metrics["anomaly_severity"] == "critical"
            assert detector.consecutive_failures == 2

        # Third execution fails - definitely critical
        with (
            patch.object(
                executor.logger,
                "get_experience_guidance",
                return_value={"context": "test"},
            ),
            patch.object(executor.logger, "log_execution_start", return_value="exp_path"),
            patch.object(executor.logger, "log_execution_result"),
        ):

            def execute_fn_3(guidance):
                raise ValueError("Fail 3")

            result3 = executor.execute_task(
                task_description="Task 3",
                skill_name="skill",
                operation_type="search",
                execute_fn=execute_fn_3,
            )

            # Three consecutive failures -> CRITICAL severity and failure_streak = 3
            assert result3.metrics["anomaly_severity"] == "critical"
            assert detector.consecutive_failures == 3

    def test_successful_execution_resets_failure_streak(self, detector):
        """Test successful execution resets failure streak."""
        mock_client = MagicMock()
        with patch("cohezion.compound.exp_persistence.vault.VaultLogger"):
            executor = CompoundExecutor(mock_client, inflection_detector=detector)

        # First execution fails
        with (
            patch.object(
                executor.logger,
                "get_experience_guidance",
                return_value={"context": "test"},
            ),
            patch.object(executor.logger, "log_execution_start", return_value="exp_path"),
            patch.object(executor.logger, "log_execution_result"),
            patch.object(executor.logger, "extract_execution_pattern", return_value="pattern_path"),
        ):

            def execute_fn_fail(guidance):
                raise ValueError("Fail")

            executor.execute_task(
                task_description="Task 1",
                skill_name="skill",
                operation_type="generate",
                execute_fn=execute_fn_fail,
            )

            assert detector.consecutive_failures == 1

        # Second execution succeeds
        with (
            patch.object(
                executor.logger,
                "get_experience_guidance",
                return_value={"context": "test"},
            ),
            patch.object(executor.logger, "log_execution_start", return_value="exp_path"),
            patch.object(executor.logger, "log_execution_result"),
            patch.object(executor.logger, "extract_execution_pattern", return_value="pattern_path"),
        ):

            def execute_fn_success(guidance):
                return "output", {"coherence": 0.8}

            executor.execute_task(
                task_description="Task 2",
                skill_name="skill",
                operation_type="analyze",
                execute_fn=execute_fn_success,
            )

            # Failure streak should reset
            assert detector.consecutive_failures == 0

    def test_anomaly_detection_non_blocking_on_error(self, executor):
        """Test anomaly detection errors don't break execution."""
        with (
            patch.object(
                executor.logger,
                "get_experience_guidance",
                return_value={"context": "test"},
            ),
            patch.object(executor.logger, "log_execution_start", return_value="exp_path"),
            patch.object(executor.logger, "log_execution_result"),
            patch.object(executor.logger, "extract_execution_pattern", return_value="pattern_path"),
            patch.object(
                executor.inflection_detector,
                "detect_anomaly",
                side_effect=RuntimeError("Detector error"),
            ),
        ):

            def execute_fn(guidance):
                return "output", {"coherence": 0.8}

            # Should not raise despite detector error
            result = executor.execute_task(
                task_description="Test task",
                skill_name="test_skill",
                operation_type="generate",
                execute_fn=execute_fn,
            )

            assert result.success
            assert result.output == "output"
            # Metrics might not have anomaly data, but execution succeeds
            assert not result.metrics.get("blocked_by_guardrails")


class TestExecutorFactoryWithDetector:
    """Tests for ExecutorFactory with detector support."""

    def test_factory_create_with_detector(self, mock_mcp_client, detector):
        """Test factory create with custom detector."""
        with patch("cohezion.compound.exp_persistence.vault.VaultLogger"):
            executor = ExecutorFactory.create(mock_mcp_client, inflection_detector=detector)
            assert executor.inflection_detector is detector

    def test_factory_create_default_detector(self, mock_mcp_client):
        """Test factory create initializes default detector."""
        with patch("cohezion.compound.exp_persistence.vault.VaultLogger"):
            executor = ExecutorFactory.create(mock_mcp_client)
            assert executor.inflection_detector is not None

    def test_factory_singleton_preserves_detector(self, mock_mcp_client, detector):
        """Test factory singleton preserves detector instance."""
        with patch("cohezion.compound.exp_persistence.vault.VaultLogger"):
            ExecutorFactory.reset_singleton()
            executor1 = ExecutorFactory.get_singleton(mock_mcp_client, inflection_detector=detector)
            executor2 = ExecutorFactory.get_singleton(mock_mcp_client)

            assert executor1 is executor2
            assert executor1.inflection_detector is detector

    def test_factory_supports_all_parameters(self, mock_mcp_client, detector):
        """Test factory supports all parameters together."""
        mock_token_client = MagicMock()
        mock_guardrail = MagicMock()

        with patch("cohezion.compound.exp_persistence.vault.VaultLogger"):
            executor = ExecutorFactory.create(
                mcp_client=mock_mcp_client,
                token_client=mock_token_client,
                guardrail_pipeline=mock_guardrail,
                enable_guardrails=True,
                inflection_detector=detector,
            )

            assert executor.mcp_client is mock_mcp_client
            assert executor.token_client is mock_token_client
            assert executor.inflection_detector is detector


class TestExecutorIntegrationScenarios:
    """Integration scenarios with real detectors."""

    def test_batch_processing_with_anomaly_detection(self, executor):
        """Test batch processing scenario with anomaly monitoring."""
        successful_count = 0
        warning_count = 0
        critical_count = 0

        # Simulate 5 batch tasks
        for i in range(5):
            with (
                patch.object(
                    executor.logger,
                    "get_experience_guidance",
                    return_value={"context": f"batch_{i}"},
                ),
                patch.object(executor.logger, "log_execution_start", return_value=f"exp_{i}"),
                patch.object(executor.logger, "log_execution_result"),
                patch.object(
                    executor.logger,
                    "extract_execution_pattern",
                    return_value=f"pattern_{i}",
                ),
            ):

                def execute_fn(guidance, i=i):
                    if i == 2:
                        # One task has low coherence
                        return f"output_{i}", {"coherence": 0.2}
                    else:
                        return f"output_{i}", {"coherence": 0.8}

                result = executor.execute_task(
                    task_description=f"Batch task {i}",
                    skill_name="batch_skill",
                    operation_type="generate",
                    execute_fn=execute_fn,
                )

                assert result.success
                severity = result.metrics.get("anomaly_severity", "unknown")
                if severity == "info":
                    successful_count += 1
                elif severity == "warning":
                    warning_count += 1
                elif severity == "critical":
                    critical_count += 1

        assert successful_count == 4
        assert warning_count == 1
        assert critical_count == 0

    def test_recovery_after_failure_streak(self, executor):
        """Test recovery detection after failure streak."""
        # Simulate 3 consecutive failures
        for _ in range(3):
            with (
                patch.object(
                    executor.logger,
                    "get_experience_guidance",
                    return_value={"context": "test"},
                ),
                patch.object(executor.logger, "log_execution_start", return_value="exp"),
                patch.object(executor.logger, "log_execution_result"),
            ):

                def execute_fn(guidance):
                    raise ValueError("Failure")

                executor.execute_task(
                    task_description="Failing task",
                    skill_name="skill",
                    operation_type="generate",
                    execute_fn=execute_fn,
                )

        # Now execute successfully
        with (
            patch.object(
                executor.logger,
                "get_experience_guidance",
                return_value={"context": "recovery"},
            ),
            patch.object(executor.logger, "log_execution_start", return_value="exp_recovery"),
            patch.object(executor.logger, "log_execution_result"),
            patch.object(executor.logger, "extract_execution_pattern", return_value="pattern"),
        ):

            def execute_fn_success(guidance):
                return "recovered", {"coherence": 0.9}

            result = executor.execute_task(
                task_description="Recovery task",
                skill_name="skill",
                operation_type="generate",
                execute_fn=execute_fn_success,
            )

            assert result.success
            # After successful execution, severity should reset
            assert result.metrics["anomaly_severity"] == "info"
