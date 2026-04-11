"""Tests for compound feedback loop with anomaly detection."""

from unittest.mock import MagicMock

import pytest

from cohezion.compound.executor import CompoundExecutor, ExecutionResult
from cohezion.compound.feedback_loop import (
    CompoundFeedbackLoop,
    CompoundFeedbackLoopFactory,
    FeedbackLoopResult,
    RetryAttempt,
    RetryStrategy,
)
from cohezion.compound.inflection_detector import (
    AnomalyDetection,
    InflectionDetector,
    Severity,
)


@pytest.fixture
def mock_executor():
    """Create mock CompoundExecutor."""
    executor = MagicMock(spec=CompoundExecutor)
    executor.execute_task = MagicMock(
        return_value=ExecutionResult(
            success=True,
            output="test output",
            metrics={"coherence": 0.85},
            duration_seconds=1.0,
        )
    )
    return executor


@pytest.fixture
def mock_detector():
    """Create mock InflectionDetector."""
    detector = MagicMock(spec=InflectionDetector)
    detector.detect_anomaly = MagicMock(
        return_value=AnomalyDetection(
            severity=Severity.INFO,
            score=0.85,
            issues=[],
            recommendations=[],
            should_reexecute=False,
        )
    )
    return detector


@pytest.fixture
def feedback_loop(mock_executor, mock_detector):
    """Create feedback loop with mocks."""
    return CompoundFeedbackLoop(
        executor=mock_executor,
        detector=mock_detector,
        max_retries=3,
    )


class TestRetryStrategy:
    """Tests for retry strategy selection."""

    def test_retry_strategy_enum(self):
        """Test RetryStrategy enum values."""
        assert RetryStrategy.SAME_SKILL.value == "same_skill"
        assert RetryStrategy.ALTERNATIVE_SKILL.value == "alternative_skill"
        assert RetryStrategy.ADJUSTED_PARAMETERS.value == "adjusted_parameters"
        assert RetryStrategy.ESCALATE_MODEL.value == "escalate_model"


class TestRetryAttempt:
    """Tests for RetryAttempt dataclass."""

    def test_retry_attempt_creation(self):
        """Test creating a retry attempt."""
        attempt = RetryAttempt(
            attempt_number=1,
            strategy=RetryStrategy.SAME_SKILL,
            skill_used="test_skill",
            success=True,
        )

        assert attempt.attempt_number == 1
        assert attempt.strategy == RetryStrategy.SAME_SKILL
        assert attempt.skill_used == "test_skill"
        assert attempt.success is True

    def test_retry_attempt_with_anomaly(self):
        """Test retry attempt with anomaly detection."""
        anomaly = AnomalyDetection(
            severity=Severity.CRITICAL,
            score=0.2,
            issues=["coherence drop"],
            recommendations=["retry"],
            should_reexecute=True,
        )

        attempt = RetryAttempt(
            attempt_number=2,
            strategy=RetryStrategy.ALTERNATIVE_SKILL,
            skill_used="alt_skill",
            success=False,
            anomaly_detected=anomaly,
        )

        assert attempt.anomaly_detected.severity == Severity.CRITICAL
        assert "coherence drop" in attempt.anomaly_detected.issues


class TestFeedbackLoopResult:
    """Tests for FeedbackLoopResult dataclass."""

    def test_feedback_loop_result_success(self):
        """Test successful feedback loop result."""
        result = FeedbackLoopResult(
            task_description="Test task",
            operation_type="generate",
            success=True,
            final_output="result",
            final_metrics={"coherence": 0.9},
            total_retries=0,
        )

        assert result.success is True
        assert result.total_retries == 0
        assert result.final_output == "result"

    def test_feedback_loop_result_with_retries(self):
        """Test feedback loop result with retries."""
        result = FeedbackLoopResult(
            task_description="Test task",
            operation_type="generate",
            success=True,
            final_output="result",
            final_metrics={"coherence": 0.85},
            total_retries=2,
            should_persist_learning=True,
        )

        assert result.total_retries == 2
        assert result.should_persist_learning is True


class TestCompoundFeedbackLoopInitialization:
    """Tests for feedback loop initialization."""

    def test_initialization_with_defaults(self, mock_executor):
        """Test initialization with default parameters."""
        loop = CompoundFeedbackLoop(executor=mock_executor)

        assert loop.executor == mock_executor
        assert loop.max_retries == 3
        assert loop.critical_threshold == 0.5
        assert loop.enable_learning is True
        assert isinstance(loop.detector, InflectionDetector)

    def test_initialization_with_custom_detector(self, mock_executor, mock_detector):
        """Test initialization with custom detector."""
        loop = CompoundFeedbackLoop(
            executor=mock_executor,
            detector=mock_detector,
            max_retries=5,
        )

        assert loop.detector == mock_detector
        assert loop.max_retries == 5

    def test_initialization_with_custom_thresholds(self, mock_executor):
        """Test initialization with custom thresholds."""
        loop = CompoundFeedbackLoop(
            executor=mock_executor,
            critical_threshold=0.3,
            max_retries=1,
            enable_learning=False,
        )

        assert loop.critical_threshold == 0.3
        assert loop.enable_learning is False


class TestRetryStrategySelection:
    """Tests for retry strategy selection logic."""

    def test_select_first_retry_strategy(self, feedback_loop):
        """Test first retry uses adjusted parameters."""
        anomaly = AnomalyDetection(
            severity=Severity.CRITICAL,
            score=0.2,
            issues=[],
            recommendations=[],
            should_reexecute=True,
        )

        strategy = feedback_loop._select_retry_strategy(0, anomaly)

        assert strategy == RetryStrategy.ADJUSTED_PARAMETERS

    def test_select_second_retry_strategy_with_alternatives(self, feedback_loop):
        """Test second retry with alternative skills available."""
        anomaly = AnomalyDetection(
            severity=Severity.CRITICAL,
            score=0.2,
            issues=[],
            recommendations=[],
            should_reexecute=True,
        )

        strategy = feedback_loop._select_retry_strategy(
            1, anomaly, available_alternatives=["skill2", "skill3"]
        )

        assert strategy == RetryStrategy.ALTERNATIVE_SKILL

    def test_select_escalate_strategy(self, feedback_loop):
        """Test escalation strategy for later retries."""
        anomaly = AnomalyDetection(
            severity=Severity.CRITICAL,
            score=0.2,
            issues=[],
            recommendations=[],
            should_reexecute=True,
        )

        strategy = feedback_loop._select_retry_strategy(2, anomaly)

        assert strategy == RetryStrategy.ESCALATE_MODEL


class TestNextSkillSelection:
    """Tests for next skill selection."""

    def test_same_skill_strategy(self, feedback_loop):
        """Test same skill is returned for SAME_SKILL strategy."""
        skill = feedback_loop._select_next_skill(
            "current_skill",
            RetryStrategy.SAME_SKILL,
        )

        assert skill == "current_skill"

    def test_alternative_skill_strategy(self, feedback_loop):
        """Test alternative skill is selected."""
        skill = feedback_loop._select_next_skill(
            "skill1",
            RetryStrategy.ALTERNATIVE_SKILL,
            available_alternatives=["skill2", "skill3"],
        )

        assert skill in ["skill2", "skill3"]
        assert skill != "skill1"

    def test_alternative_skill_fallback(self, feedback_loop):
        """Test fallback when no alternatives available."""
        skill = feedback_loop._select_next_skill(
            "skill1",
            RetryStrategy.ALTERNATIVE_SKILL,
            available_alternatives=[],
        )

        assert skill == "skill1"

    def test_adjusted_parameters_strategy(self, feedback_loop):
        """Test adjusted parameters strategy."""
        skill = feedback_loop._select_next_skill(
            "skill1",
            RetryStrategy.ADJUSTED_PARAMETERS,
        )

        assert skill == "skill1"

    def test_escalate_model_strategy(self, feedback_loop):
        """Test model escalation strategy."""
        skill = feedback_loop._select_next_skill(
            "skill1",
            RetryStrategy.ESCALATE_MODEL,
        )

        assert skill == "skill1"


class TestExecutionWithFeedback:
    """Tests for main feedback loop execution."""

    @pytest.mark.asyncio
    async def test_execute_success_on_first_attempt(self, feedback_loop):
        """Test task succeeds on first attempt."""

        def execute_fn(guidance):
            return "output", {"coherence": 0.9}

        result = await feedback_loop.execute_with_feedback(
            task_description="Test task",
            skill_name="test_skill",
            operation_type="generate",
            execute_fn=execute_fn,
        )

        assert result.success is True
        assert result.total_retries == 0
        assert len(result.attempts) == 1
        assert result.attempts[0].success is True

    @pytest.mark.asyncio
    async def test_execute_failure_no_retries(self, feedback_loop):
        """Test task failure with no retries available."""
        # Mock detector to return critical anomaly
        feedback_loop.detector.detect_anomaly = MagicMock(
            return_value=AnomalyDetection(
                severity=Severity.CRITICAL,
                score=0.1,
                issues=["coherence drop"],
                recommendations=["retry"],
                should_reexecute=True,
            )
        )

        # Mock executor to fail
        feedback_loop.executor.execute_task = MagicMock(
            return_value=ExecutionResult(
                success=False,
                output="error",
                metrics={"coherence": 0.1},
                duration_seconds=1.0,
            )
        )

        def execute_fn(guidance):
            raise RuntimeError("Task failed")

        result = await feedback_loop.execute_with_feedback(
            task_description="Test task",
            skill_name="test_skill",
            operation_type="generate",
            execute_fn=execute_fn,
        )

        assert result.success is False

    @pytest.mark.asyncio
    async def test_execute_with_retries(self, feedback_loop):
        """Test task succeeds after retries."""
        attempt_count = 0

        def mock_execute_task(*args, **kwargs):
            nonlocal attempt_count
            attempt_count += 1
            if attempt_count < 3:
                # First two attempts fail
                return ExecutionResult(
                    success=False,
                    output="error",
                    metrics={"coherence": 0.1},
                    duration_seconds=1.0,
                )
            else:
                # Third attempt succeeds
                return ExecutionResult(
                    success=True,
                    output="success",
                    metrics={"coherence": 0.9},
                    duration_seconds=1.0,
                )

        feedback_loop.executor.execute_task = mock_execute_task

        # Mock detector to return different severity levels
        attempt_num = [0]

        def mock_detect(result):
            attempt_num[0] += 1
            if attempt_num[0] < 3:
                return AnomalyDetection(
                    severity=Severity.CRITICAL,
                    score=0.1,
                    issues=["coherence drop"],
                    recommendations=["retry"],
                    should_reexecute=True,
                )
            else:
                return AnomalyDetection(
                    severity=Severity.INFO,
                    score=0.9,
                    issues=[],
                    recommendations=[],
                    should_reexecute=False,
                )

        feedback_loop.detector.detect_anomaly = mock_detect

        def execute_fn(guidance):
            return "output", {}

        result = await feedback_loop.execute_with_feedback(
            task_description="Test task",
            skill_name="test_skill",
            operation_type="generate",
            execute_fn=execute_fn,
        )

        assert result.success is True
        assert result.total_retries == 2
        assert len(result.attempts) == 3

    @pytest.mark.asyncio
    async def test_execute_with_alternative_skills(self, feedback_loop):
        """Test retry with alternative skills."""
        feedback_loop.max_retries = 2

        def mock_execute_task(*args, **kwargs):
            return ExecutionResult(
                success=True,
                output="success",
                metrics={"coherence": 0.85},
                duration_seconds=1.0,
            )

        feedback_loop.executor.execute_task = mock_execute_task
        feedback_loop.detector.detect_anomaly = MagicMock(
            return_value=AnomalyDetection(
                severity=Severity.INFO,
                score=0.85,
                issues=[],
                recommendations=[],
                should_reexecute=False,
            )
        )

        def execute_fn(guidance):
            return "output", {}

        result = await feedback_loop.execute_with_feedback(
            task_description="Test task",
            skill_name="skill1",
            operation_type="generate",
            execute_fn=execute_fn,
            available_alternative_skills=["skill2", "skill3"],
        )

        assert result.success is True


class TestLearningLogging:
    """Tests for learning logging."""

    def test_log_learning_basic(self, feedback_loop):
        """Test learning logging doesn't crash."""
        attempts = [
            RetryAttempt(
                attempt_number=1,
                strategy=RetryStrategy.SAME_SKILL,
                skill_used="skill1",
                success=False,
                anomaly_detected=AnomalyDetection(
                    severity=Severity.WARNING,
                    score=0.4,
                    issues=["low coherence"],
                    recommendations=[],
                    should_reexecute=True,
                ),
            ),
            RetryAttempt(
                attempt_number=2,
                strategy=RetryStrategy.ALTERNATIVE_SKILL,
                skill_used="skill2",
                success=True,
            ),
        ]

        result = ExecutionResult(
            success=True,
            output="output",
            metrics={"coherence": 0.9},
            duration_seconds=2.0,
        )

        # Should not raise
        feedback_loop._log_learning("task", "skill1", "generate", attempts, result)


class TestStatistics:
    """Tests for retry statistics."""

    def test_retry_statistics_empty(self, feedback_loop):
        """Test statistics with no execution history."""
        stats = feedback_loop.get_retry_statistics()

        assert stats["total_executions"] == 0
        assert stats["successful_on_first_attempt"] == 0
        assert stats["average_retries"] == 0.0


class TestReset:
    """Tests for reset functionality."""

    def test_reset_feedback_loop(self, feedback_loop):
        """Test resetting feedback loop state."""
        feedback_loop.execution_history = [RetryAttempt(1, RetryStrategy.SAME_SKILL, "skill", True)]

        feedback_loop.reset()

        assert len(feedback_loop.execution_history) == 0
        assert isinstance(feedback_loop.detector, InflectionDetector)


class TestCompoundFeedbackLoopFactory:
    """Tests for factory pattern."""

    def test_factory_creates_loop(self, mock_executor):
        """Test factory creates feedback loop."""
        loop = CompoundFeedbackLoopFactory.create(
            mock_executor,
            max_retries=5,
            critical_threshold=0.3,
        )

        assert isinstance(loop, CompoundFeedbackLoop)
        assert loop.executor == mock_executor
        assert loop.max_retries == 5
        assert loop.critical_threshold == 0.3

    def test_factory_default_parameters(self, mock_executor):
        """Test factory with default parameters."""
        loop = CompoundFeedbackLoopFactory.create(mock_executor)

        assert loop.max_retries == 3
        assert loop.critical_threshold == 0.5
        assert loop.enable_learning is True
