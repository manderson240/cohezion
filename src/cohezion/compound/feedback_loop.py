"""Compound feedback loop with re-execution on critical anomalies.

Monitors execution results and automatically re-executes tasks when
critical anomalies are detected, with learned improvements applied.

Lifecycle:
  1. Execute task with CompoundExecutor
  2. Detect anomalies using InflectionDetector
  3. If CRITICAL: Trigger re-execution with adjusted skill/parameters
  4. Log retry trajectory and learning
  5. Refine skills based on cumulative feedback
"""

import asyncio
import logging
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from cohezion.compound.executor import CompoundExecutor, ExecutionResult
from cohezion.compound.inflection_detector import (
    AnomalyDetection,
    InflectionDetector,
    Severity,
)


logger = logging.getLogger(__name__)


class RetryStrategy(Enum):
    """Strategy for retrying failed executions."""

    SAME_SKILL = "same_skill"  # Retry with same skill
    ALTERNATIVE_SKILL = "alternative_skill"  # Try different skill
    ADJUSTED_PARAMETERS = "adjusted_parameters"  # Same skill, adjusted params
    ESCALATE_MODEL = "escalate_model"  # Use more capable model


@dataclass
class RetryAttempt:
    """Record of a single retry attempt."""

    attempt_number: int
    strategy: RetryStrategy
    skill_used: str
    success: bool
    anomaly_detected: AnomalyDetection | None = None
    execution_result: ExecutionResult | None = None
    error: str = ""


@dataclass
class FeedbackLoopResult:
    """Result of feedback loop execution with retries."""

    task_description: str
    operation_type: str
    success: bool
    final_output: str
    final_metrics: dict[str, Any]
    attempts: list[RetryAttempt] = field(default_factory=list)
    total_retries: int = 0
    total_duration_seconds: float = 0.0
    learned_skill_adjustment: str = ""
    should_persist_learning: bool = False


class CompoundFeedbackLoop:
    """Compound execution with automatic feedback and re-execution.

    Monitors execution quality and automatically handles failures
    by detecting anomalies and attempting intelligent re-execution
    with learned improvements.

    Example:
        ```python
        loop = CompoundFeedbackLoop(
            executor=executor,
            detector=detector,
            max_retries=3,
        )

        result = asyncio.run(loop.execute_with_feedback(
            task_description="Generate ideas",
            skill_name="generator",
            operation_type="generate",
            execute_fn=my_task,
        ))

        if result.success:
            print(f"Task succeeded after {result.total_retries} retries")
        ```
    """

    def __init__(
        self,
        executor: CompoundExecutor,
        detector: InflectionDetector | None = None,
        max_retries: int = 3,
        critical_threshold: float = 0.5,
        enable_learning: bool = True,
        model_router: Any | None = None,
    ):
        """Initialize compound feedback loop.

        Args:
            executor: CompoundExecutor for task execution
            detector: InflectionDetector for anomaly detection
                If None, created with defaults
            max_retries: Maximum retry attempts for critical anomalies
            critical_threshold: Score threshold for critical severity
            enable_learning: Whether to refine skills based on feedback
            model_router: Optional TipOfTheSpearRouter for model escalation.
                When provided, ESCALATE_MODEL strategy selects the next tier
                model via HOT→WARM→COLD→CLOUD escalation chain.
        """
        self.executor = executor
        self.detector = detector or InflectionDetector()
        self.max_retries = max_retries
        self.critical_threshold = critical_threshold
        self.enable_learning = enable_learning
        self.model_router = model_router

        # Track execution history for learning
        self.execution_history: list[RetryAttempt] = []

        logger.debug(
            "Initialized CompoundFeedbackLoop with max_retries=%d, critical_threshold=%.2f",
            max_retries,
            critical_threshold,
        )

    async def execute_with_feedback(
        self,
        task_description: str,
        skill_name: str,
        operation_type: str,
        execute_fn: Callable,
        project: str = "cohezion",
        available_alternative_skills: list[str] | None = None,
    ) -> FeedbackLoopResult:
        """Execute task with feedback loop and automatic re-execution.

        Args:
            task_description: What the task does
            skill_name: Primary skill to attempt
            operation_type: Type of operation
            execute_fn: Callable that executes task
            project: Project name for vault logging
            available_alternative_skills: List of skills to try on failure

        Returns:
            FeedbackLoopResult with outcomes and retry history
        """
        start_time = time.time()
        attempts: list[RetryAttempt] = []
        current_skill = skill_name
        current_retry = 0

        logger.info(
            "Starting feedback loop execution: %s (skill=%s, operation=%s)",
            task_description,
            skill_name,
            operation_type,
        )

        while current_retry <= self.max_retries:
            logger.debug(
                "Attempt %d/%d with skill: %s",
                current_retry + 1,
                self.max_retries + 1,
                current_skill,
            )

            # Execute task
            execution_result = self.executor.execute_task(
                task_description=task_description,
                skill_name=current_skill,
                operation_type=operation_type,
                execute_fn=execute_fn,
                project=project,
            )

            # Detect anomalies
            anomaly = self.detector.detect_anomaly(execution_result)
            logger.debug(
                "Anomaly detection: severity=%s, score=%.2f, issues=%s",
                anomaly.severity,
                anomaly.score,
                anomaly.issues,
            )

            # Create retry attempt record
            attempt = RetryAttempt(
                attempt_number=current_retry + 1,
                strategy=self._select_retry_strategy(
                    current_retry, anomaly, available_alternative_skills
                ),
                skill_used=current_skill,
                success=execution_result.success and anomaly.score > self.critical_threshold,
                anomaly_detected=anomaly,
                execution_result=execution_result,
            )
            attempts.append(attempt)

            # If successful and no critical anomaly, we're done
            if attempt.success:
                logger.info(
                    "Task succeeded on attempt %d with score %.2f",
                    current_retry + 1,
                    anomaly.score,
                )

                # Log learning if anomalies were detected
                if current_retry > 0 and self.enable_learning:
                    self._log_learning(
                        task_description,
                        skill_name,
                        operation_type,
                        attempts,
                        execution_result,
                    )

                return FeedbackLoopResult(
                    task_description=task_description,
                    operation_type=operation_type,
                    success=True,
                    final_output=execution_result.output,
                    final_metrics=execution_result.metrics,
                    attempts=attempts,
                    total_retries=current_retry,
                    total_duration_seconds=time.time() - start_time,
                    should_persist_learning=current_retry > 0,
                )

            # If critical and retries available, attempt retry
            if anomaly.severity == Severity.CRITICAL and current_retry < self.max_retries:
                logger.warning(
                    "Critical anomaly detected: %s. Attempting retry %d/%d",
                    anomaly.issues,
                    current_retry + 1,
                    self.max_retries,
                )

                # Determine next retry strategy
                next_skill = self._select_next_skill(
                    current_skill,
                    attempt.strategy,
                    available_alternative_skills,
                    anomaly,
                )
                current_skill = next_skill
                current_retry += 1
            else:
                # No more retries or not critical
                logger.warning(
                    "Task failed with severity=%s, no more retries available",
                    anomaly.severity,
                )

                # Still log learning if enabled
                if self.enable_learning:
                    self._log_learning(
                        task_description,
                        skill_name,
                        operation_type,
                        attempts,
                        execution_result,
                    )

                return FeedbackLoopResult(
                    task_description=task_description,
                    operation_type=operation_type,
                    success=False,
                    final_output=execution_result.output,
                    final_metrics=execution_result.metrics,
                    attempts=attempts,
                    total_retries=current_retry,
                    total_duration_seconds=time.time() - start_time,
                    should_persist_learning=True,
                )

        # Exhausted all retries
        logger.error(
            "Exhausted all retry attempts (%d) for task: %s",
            self.max_retries,
            task_description,
        )

        return FeedbackLoopResult(
            task_description=task_description,
            operation_type=operation_type,
            success=False,
            final_output=attempts[-1].execution_result.output,
            final_metrics=attempts[-1].execution_result.metrics,
            attempts=attempts,
            total_retries=self.max_retries,
            total_duration_seconds=time.time() - start_time,
            should_persist_learning=True,
        )

    def _select_retry_strategy(
        self,
        attempt_number: int,
        anomaly: AnomalyDetection,
        available_alternatives: list[str] | None = None,
    ) -> RetryStrategy:
        """Select strategy for next retry.

        Args:
            attempt_number: Current attempt (0-indexed)
            anomaly: Detected anomaly information
            available_alternatives: Alternative skills to try

        Returns:
            RetryStrategy for next attempt
        """
        # First retry: try same skill with adjusted parameters
        if attempt_number == 0:
            return RetryStrategy.ADJUSTED_PARAMETERS

        # Second retry: try alternative skill if available
        if attempt_number == 1 and available_alternatives:
            return RetryStrategy.ALTERNATIVE_SKILL

        # Later retries: escalate to more capable model
        return RetryStrategy.ESCALATE_MODEL

    def _select_next_skill(
        self,
        current_skill: str,
        strategy: RetryStrategy,
        available_alternatives: list[str] | None = None,
        anomaly: AnomalyDetection | None = None,
    ) -> str:
        """Select skill for next retry based on strategy.

        Args:
            current_skill: Currently used skill
            strategy: Retry strategy to apply
            available_alternatives: List of alternative skills
            anomaly: Anomaly detection results

        Returns:
            Skill name for next attempt
        """
        if strategy == RetryStrategy.SAME_SKILL:
            return current_skill

        if strategy == RetryStrategy.ALTERNATIVE_SKILL and available_alternatives:
            # Pick first alternative different from current
            for skill in available_alternatives:
                if skill != current_skill:
                    logger.info("Switching to alternative skill: %s", skill)
                    return skill
            # Fall back to same if no alternatives
            return current_skill

        if strategy == RetryStrategy.ADJUSTED_PARAMETERS:
            # Modify skill name to indicate adjusted params
            adjusted = f"{current_skill}_adjusted"
            logger.debug("Retrying with adjusted parameters: %s", adjusted)
            return current_skill  # Original skill, execute_fn adjusts params

        if strategy == RetryStrategy.ESCALATE_MODEL:
            # Use TipOfTheSpearRouter if available for tier-based escalation
            if self.model_router and hasattr(self.model_router, "get_current_tier"):
                try:
                    current_tier = self.model_router.get_current_tier()
                    next_tier = self.model_router._get_next_tier(current_tier)
                    if next_tier:
                        model = self.model_router._get_tier_model(next_tier, "general")
                        logger.info(
                            "Model escalation via TotS: %s → %s (model=%s)",
                            current_tier.value,
                            next_tier.value,
                            model,
                        )
                except Exception:
                    logger.debug("TotS escalation failed, using default", exc_info=True)
            else:
                logger.info("Escalating to more capable model (no router attached)")
            return current_skill  # Skill unchanged, model escalation is metadata

        return current_skill

    def _log_learning(
        self,
        task_description: str,
        original_skill: str,
        operation_type: str,
        attempts: list[RetryAttempt],
        final_result: ExecutionResult,
    ) -> None:
        """Log learning insights from retry trajectory.

        Args:
            task_description: Task description
            original_skill: Original skill attempted
            operation_type: Operation type
            attempts: List of retry attempts
            final_result: Final execution result
        """
        try:
            # Analyze retry trajectory
            success_rate = sum(1 for a in attempts if a.success) / len(attempts)
            failures = [a for a in attempts if not a.success]

            logger.info(
                "Learning from retry trajectory: task=%s, skill=%s, attempts=%d, success_rate=%.2f",
                task_description,
                original_skill,
                len(attempts),
                success_rate,
            )

            # Identify common issues
            common_issues: dict[str, int] = {}
            for attempt in failures:
                if attempt.anomaly_detected:
                    for issue in attempt.anomaly_detected.issues:
                        common_issues[issue] = common_issues.get(issue, 0) + 1

            if common_issues:
                logger.debug("Common failure issues: %s", common_issues)

            # Log which strategies worked
            successful_strategies = [a.strategy for a in attempts if a.success]
            if successful_strategies:
                logger.info(
                    "Successful strategies: %s",
                    ", ".join(str(s) for s in successful_strategies),
                )

        except Exception as e:
            logger.debug("Error logging learning insights: %s", e)

    def reset(self) -> None:
        """Reset execution history and detector state."""
        self.execution_history.clear()
        self.detector = InflectionDetector()
        logger.debug("Reset feedback loop state")

    def get_retry_statistics(self) -> dict[str, Any]:
        """Get statistics about retry attempts.

        Returns:
            Dictionary with retry statistics
        """
        if not self.execution_history:
            return {
                "total_executions": 0,
                "successful_on_first_attempt": 0,
                "required_retries": 0,
                "average_retries": 0.0,
            }

        total = len(self.execution_history)
        first_attempts = sum(1 for a in self.execution_history if a.attempt_number == 1)
        total_retries = sum((a.attempt_number - 1) for a in self.execution_history if a.success)

        return {
            "total_executions": total,
            "successful_on_first_attempt": first_attempts,
            "required_retries": total - first_attempts,
            "average_retries": total_retries / total if total > 0 else 0,
        }

    async def execute_batch_with_feedback(
        self, tasks: list[tuple[str, Callable]]
    ) -> dict[str, Any]:
        """Execute batch of tasks with feedback loop integration.

        Phase 2.5: Batch execution with cache warming from learned patterns.

        Workflow:
          1. Execute all tasks with feedback loops in parallel
          2. Detect critical anomalies across batch
          3. Cache successful retry results for future use
          4. Re-execute critical tasks with improved prompts
          5. Extract patterns from successful retries

        Args:
            tasks: List of (task_description, execute_fn) tuples

        Returns:
            Dict with aggregated results and learning metrics
        """
        if not tasks:
            logger.warning("execute_batch_with_feedback called with empty task list")
            return {
                "success": True,
                "tasks_executed": 0,
                "tasks_failed": 0,
                "cache_warming_hits": 0,
                "learned_patterns": [],
            }

        logger.info(f"Starting batch feedback execution for {len(tasks)} tasks")

        # Execute all tasks in parallel with feedback loops
        batch_results = await asyncio.gather(
            *[
                self.execute_with_feedback(
                    task_description=desc,
                    skill_name="general",
                    operation_type="execute",
                    execute_fn=fn,
                )
                for desc, fn in tasks
            ],
            return_exceptions=True,
        )

        # Collect results and identify critical anomalies
        successful_results = []
        critical_failures = []
        cache_warming_opportunities = []

        for i, result in enumerate(batch_results):
            if isinstance(result, Exception):
                logger.error(f"Task {i} failed with exception: {result}")
                critical_failures.append((i, str(result)))
            elif isinstance(result, FeedbackLoopResult):
                if result.success:
                    successful_results.append(result)
                    # Cache successful results for future use (Phase 2.5)
                    if result.total_retries > 0:
                        cache_warming_opportunities.append(
                            {
                                "task_description": result.task_description,
                                "final_output": result.final_output,
                                "retry_count": result.total_retries,
                                "learned_skill_adjustment": result.learned_skill_adjustment,
                            }
                        )
                else:
                    critical_failures.append((i, "Task failed after all retries"))

        # Cache successful retry results for future batch executions
        logger.info(
            f"Batch cache warming: Found {len(cache_warming_opportunities)} successful retry patterns to cache"
        )

        # Extract and persist learning patterns
        learned_patterns = []
        for opportunity in cache_warming_opportunities:
            try:
                if hasattr(self.executor, "skill_refiner"):
                    refiner = self.executor.skill_refiner
                    pattern = await refiner.extract_retry_pattern(
                        task_description=opportunity["task_description"],
                        retry_count=opportunity["retry_count"],
                        successful_output=opportunity["final_output"],
                    )
                    learned_patterns.append(pattern)
            except Exception as e:
                logger.debug(f"Error extracting pattern: {e}")

        return {
            "success": len(critical_failures) == 0,
            "tasks_executed": len(successful_results),
            "tasks_failed": len(critical_failures),
            "cache_warming_hits": len(cache_warming_opportunities),
            "learned_patterns": learned_patterns,
            "critical_failures": critical_failures,
        }


class CompoundFeedbackLoopFactory:
    """Factory for creating feedback loop instances."""

    @staticmethod
    def create(
        executor: CompoundExecutor,
        max_retries: int = 3,
        critical_threshold: float = 0.5,
        enable_learning: bool = True,
        model_router: Any | None = None,
    ) -> CompoundFeedbackLoop:
        """Create a compound feedback loop.

        Args:
            executor: CompoundExecutor for task execution
            max_retries: Maximum retry attempts
            critical_threshold: Score threshold for critical severity
            enable_learning: Whether to enable skill refinement
            model_router: Optional TipOfTheSpearRouter for model escalation

        Returns:
            CompoundFeedbackLoop instance
        """
        detector = InflectionDetector()
        return CompoundFeedbackLoop(
            executor=executor,
            detector=detector,
            max_retries=max_retries,
            critical_threshold=critical_threshold,
            enable_learning=enable_learning,
            model_router=model_router,
        )
