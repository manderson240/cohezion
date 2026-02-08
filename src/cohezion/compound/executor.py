"""Compound executor with vault-integrated knowledge persistence.

Orchestrates execution lifecycle:
  1. Query vault for experience guidance (prior similar runs)
  2. Execute task with guidance
  3. Log execution trajectory, decisions, metrics to vault
  4. Extract reusable patterns for future runs
"""

import asyncio
import json
import logging
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING, Any

from cohezion.compound.vault_execution_logger import (
    ExecutionContext,
    VaultExecutionLogger,
)
from cohezion.core.mcp_client import MCPClient
from cohezion.security.guardrail_pipeline import GuardrailAction, GuardrailPipeline


if TYPE_CHECKING:
    from cohezion.compound.inflection_detector import InflectionDetector
    from cohezion.compound.skill_refiner import SkillRefiner
else:
    # Lazy import to avoid circular dependency at runtime
    InflectionDetector = None
    SkillRefiner = None


logger = logging.getLogger(__name__)


def _run_async_guardrail(coro: Any) -> Any:
    """Execute async guardrail check in sync context.

    Non-blocking on failure - logs and returns None.

    Args:
        coro: Async coroutine to execute

    Returns:
        Result of coroutine or None on failure
    """
    try:
        return asyncio.run(coro)
    except Exception as e:
        logger.debug(f"Guardrail check failed (non-blocking): {e}")
        return None


@dataclass
class ExecutionResult:
    """Result of a compound execution."""

    success: bool
    output: str
    metrics: dict[str, Any]
    duration_seconds: float
    vault_experiment_path: str = ""
    vault_decision_paths: list[str] | None = None
    token_metrics: dict[str, Any] | None = None


class CompoundExecutor:
    """Executor for compound engineering tasks with vault integration.

    Lifecycle:
      1. get_experience_guidance() - Query vault for similar tasks
      2. execute_task() - Run the task with token-efficient client
      3. Logs are persisted to vault automatically
      4. extract_patterns() - Save reusable insights

    Optionally uses TokenEfficientClient for token-efficient LLM operations:
      - SHA-256 caching eliminates redundant API calls
      - Batch processing (Phase 1 cache + Phase 2 parallel) saves tokens
      - Token metrics captured in ExecutionResult for compound scoring
    """

    def __init__(
        self,
        mcp_client: MCPClient,
        token_client: Any | None = None,
        guardrail_pipeline: GuardrailPipeline | None = None,
        enable_guardrails: bool = True,
        inflection_detector: Any | None = None,
        skill_refiner: Any | None = None,
        enable_skill_refinement: bool = True,
    ):
        """Initialize compound executor.

        Args:
            mcp_client: Connected MCPClient for vault operations
            token_client: Optional TokenEfficientClient for LLM operations
                If provided, enables token-efficient caching and batching
            guardrail_pipeline: Optional GuardrailPipeline for safety checks.
                If None and enable_guardrails is True, creates default pipeline.
                If None and enable_guardrails is False, no guardrails applied.
            enable_guardrails: If True (default), enable guardrails via default
                pipeline (unless guardrail_pipeline is provided).
            inflection_detector: Optional InflectionDetector for anomaly detection.
                If None, creates default detector automatically.
            skill_refiner: Optional SkillRefiner for learning from executions.
                If None and enable_skill_refinement is True, creates default.
            enable_skill_refinement: If True (default), enable skill refinement.
        """
        self.mcp_client = mcp_client
        self.token_client = token_client
        self._guardrail_pipeline = guardrail_pipeline
        self._enable_guardrails = enable_guardrails
        self._skill_refiner = skill_refiner
        self._enable_skill_refinement = enable_skill_refinement
        # Lazy import to avoid circular dependency
        if inflection_detector:
            self.inflection_detector = inflection_detector
        else:
            from cohezion.compound.inflection_detector import InflectionDetectorFactory
            self.inflection_detector = InflectionDetectorFactory.create_default()
        self.logger = VaultExecutionLogger(mcp_client)

    @property
    def guardrail_pipeline(self) -> GuardrailPipeline | None:
        """Lazy-initialize default guardrail pipeline if enabled.

        Returns:
            GuardrailPipeline if guardrails enabled, None otherwise
        """
        if not self._enable_guardrails:
            return None

        if self._guardrail_pipeline is None:
            from cohezion.security.guardrail_factory import create_default_pipeline

            self._guardrail_pipeline = create_default_pipeline()
            logger.debug("Initialized default guardrail pipeline")

        return self._guardrail_pipeline

    @property
    def skill_refiner(self) -> Any | None:
        """Lazy-initialize default skill refiner if enabled.

        Returns:
            SkillRefiner if skill refinement enabled, None otherwise
        """
        if not self._enable_skill_refinement:
            return None

        if self._skill_refiner is None:
            from cohezion.compound.skill_refiner import SkillRefinerFactory

            self._skill_refiner = SkillRefinerFactory.create(self.mcp_client)
            logger.debug("Initialized default skill refiner")

        return self._skill_refiner

    def get_experience_guidance(
        self, task_description: str, project: str = "cohezion"
    ) -> dict[str, Any]:
        """Fetch experience guidance from vault before execution.

        Args:
            task_description: Description of the task to execute
            project: Project name for scoped search

        Returns:
            Dict with relevant_context (decisions, experiments, patterns)
        """
        logger.info("Fetching experience guidance for: %s", task_description)
        result: dict[str, Any] = self.logger.get_experience_guidance(
            task_description=task_description, project=project
        )
        return result

    def suggest_skills(
        self,
        task_description: str,
        operation_type: str,
        project: str = "cohezion",
        top_k: int = 3,
    ) -> list[tuple[str, float]]:
        """Suggest best skills for a task using vault experience.

        Queries vault patterns to find skills that performed well on
        similar tasks. Returns ranked list of candidates.

        Args:
            task_description: Description of the task
            operation_type: Type of operation (generate, analyze, etc.)
            project: Project name for scoped search
            top_k: Number of skill suggestions to return

        Returns:
            List of (skill_name, score) tuples, sorted by score (highest first)
        """
        try:
            from cohezion.compound.skill_selector import SkillSelector

            selector = SkillSelector(self.mcp_client)
            suggestions = selector.select_skills(
                task_description,
                operation_type,
                project=project,
                top_k=top_k,
            )

            logger.info(
                "Suggested %d skills for task: %s",
                len(suggestions),
                ", ".join(s.skill_name for s in suggestions),
            )

            return [(s.skill_name, s.composite_score) for s in suggestions]
        except Exception as e:
            logger.warning(
                "Error suggesting skills: %s. Returning empty list.",
                e,
                exc_info=True,
            )
            return []

    def execute_task(
        self,
        task_description: str,
        skill_name: str,
        operation_type: str,
        execute_fn: Callable,
        project: str = "cohezion",
    ) -> ExecutionResult:
        """Execute a compound task with vault logging.

        Args:
            task_description: What the task does
            skill_name: Name of the skill being executed
            operation_type: Type of operation
                (generate, analyze, search, transform, persist)
            execute_fn: Callable that executes the task, returns (output, metrics)
                Can optionally use self.token_client if available
            project: Project name for vault logging

        Returns:
            ExecutionResult with success status, output, metrics, vault paths,
            and token_metrics if TokenEfficientClient was used
        """
        start_time = datetime.now()
        start_seconds = time.time()

        # Create execution context
        ctx = ExecutionContext(
            project=project,
            skill_name=skill_name,
            task_description=task_description,
            operation_type=operation_type,
            start_time=start_time,
            mcp_client=self.mcp_client,
        )

        logger.info(
            "Executing task: %s (operation=%s, skill=%s)",
            task_description,
            operation_type,
            skill_name,
        )

        # Step 1: Get experience guidance
        guidance = self.get_experience_guidance(task_description, project)
        logger.debug("Experience guidance: %s", guidance)

        # Step 2: Log execution start
        experiment_path = self.logger.log_execution_start(ctx)

        # Step 3: Check input via guardrails
        success = False
        output = ""
        metrics: dict[str, Any] = {}
        token_metrics: dict[str, Any] | None = None
        error_msg = ""

        # Check input against guardrails if enabled
        if self.guardrail_pipeline:
            guard_context = {
                "skill_name": skill_name,
                "operation_type": operation_type,
                "task_description": task_description,
            }
            input_check = _run_async_guardrail(
                self.guardrail_pipeline.check_input(
                    task_description, guard_context
                )
            )
            if input_check and input_check.action == GuardrailAction.BLOCK:
                error_msg = f"Input blocked by guardrails: {input_check.reason}"
                output = f"Error: {error_msg}"
                metrics = {"error": error_msg, "blocked_by_guardrails": True}
                logger.warning("Task input blocked: %s", input_check.reason)
                # Log execution result and return
                self.logger.log_execution_result(
                    experiment_path=experiment_path,
                    success=False,
                    output=output,
                    metrics=metrics,
                )
                return ExecutionResult(
                    success=False,
                    output=output,
                    metrics=metrics,
                    duration_seconds=time.time() - start_seconds,
                    vault_experiment_path=experiment_path,
                )

        # Capture token metrics before execution (if token_client available)
        token_metrics_before = None
        if self.token_client:
            token_metrics_before = self.token_client.get_metrics()

        try:
            output, metrics = execute_fn(guidance)
            success = True
            logger.info("Task completed successfully")
        except Exception as e:
            error_msg = str(e)
            output = f"Error: {error_msg}"
            metrics = {"error": error_msg}
            logger.error("Task failed: %s", error_msg, exc_info=True)

        # Capture token metrics after execution (if token_client available)
        if self.token_client:
            token_metrics_after = self.token_client.get_metrics()
            token_metrics = self._compute_token_delta(
                token_metrics_before, token_metrics_after
            )
            logger.debug("Token metrics: %s", token_metrics)

        # Check output via guardrails if successful
        if success and self.guardrail_pipeline:
            guard_context = {
                "skill_name": skill_name,
                "operation_type": operation_type,
                "task_description": task_description,
            }
            output_check = _run_async_guardrail(
                self.guardrail_pipeline.check_output(
                    output, guard_context
                )
            )
            if output_check:
                if output_check.action == GuardrailAction.BLOCK:
                    output = "[Output blocked by content filter]"
                    success = False
                    metrics["output_blocked_by_guardrails"] = True
                    logger.warning("Task output blocked: %s", output_check.reason)
                elif output_check.action == GuardrailAction.SANITIZE:
                    if output_check.modified_input:
                        output = output_check.modified_input
                        metrics["output_sanitized_by_guardrails"] = True
                        logger.debug("Task output sanitized")

        duration_seconds = time.time() - start_seconds
        metrics["duration_seconds"] = duration_seconds

        # Step 4: Log execution results
        self.logger.log_execution_result(
            experiment_path=experiment_path,
            success=success,
            output=output,
            metrics=metrics,
        )

        # Step 5: Detect anomalies (non-blocking)
        decision_paths = []
        try:
            from cohezion.compound.inflection_detector import Severity
            temp_result = ExecutionResult(
                success=success,
                output=output,
                metrics=metrics,
                duration_seconds=duration_seconds,
                token_metrics=token_metrics,
            )
            anomaly = self.inflection_detector.detect_anomaly(temp_result)
            metrics["anomaly_severity"] = anomaly.severity.value
            metrics["anomaly_score"] = anomaly.score
            logger.debug(
                "Anomaly detection: severity=%s, score=%.2f, issues=%s",
                anomaly.severity.value,
                anomaly.score,
                anomaly.issues,
            )
            # Log critical inflection points to vault
            if anomaly.severity == Severity.CRITICAL:
                logger.warning(
                    "Critical inflection point detected: %s issues",
                    len(anomaly.issues),
                )
                try:
                    decision_path = self.log_inflection_point(
                        title=f"Critical anomaly in {skill_name}",
                        context=f"Task: {task_description}\nIssues: {'; '.join(anomaly.issues)}",
                        decision="Re-execution recommended",
                        rationale=f"Quality score {anomaly.score:.2f}, {anomaly.recommendations[0] if anomaly.recommendations else 'Investigate issues'}",
                        project=project,
                    )
                    if decision_path:
                        decision_paths.append(decision_path)
                except Exception as e:
                    logger.debug(
                        "Failed to log inflection point (non-blocking): %s", e
                    )
        except Exception as e:
            logger.debug(
                "Anomaly detection failed (non-blocking): %s", e, exc_info=True
            )

        # Step 6: If successful, extract patterns
        if success and experiment_path:
            try:
                pattern_path = self.logger.extract_execution_pattern(
                    source_path=experiment_path,
                    pattern_name=f"{skill_name}_{operation_type}_success",
                    description=f"Successful execution pattern for {skill_name} "
                    f"operation: {operation_type}. "
                    f"Task: {task_description[:100]}",
                    code_example=f"Result metrics: {json.dumps(metrics, indent=2)}",
                    domain="compound-engineering",
                )
                if pattern_path:
                    decision_paths.append(pattern_path)
            except Exception as e:
                logger.warning("Failed to extract pattern: %s", e, exc_info=True)

        # Step 7: Refine skills based on execution results (non-blocking)
        if success and self.skill_refiner:
            try:
                # Create execution result dict for refiner
                exec_result = {
                    "success": success,
                    "output": output,
                    "metrics": metrics,
                    "duration_seconds": duration_seconds,
                    "token_metrics": token_metrics,
                }

                # Call skill refiner
                refined_path = self.skill_refiner.refine(
                    skill_name=skill_name,
                    operation_type=operation_type,
                    execution_result=exec_result,
                    patterns_extracted=decision_paths,
                )

                if refined_path:
                    logger.info(f"Skill refined: {refined_path}")
                    decision_paths.append(refined_path)

            except Exception as e:
                logger.debug(
                    "Skill refinement failed (non-blocking): %s", e, exc_info=True
                )

        return ExecutionResult(
            success=success,
            output=output,
            metrics=metrics,
            duration_seconds=duration_seconds,
            vault_experiment_path=experiment_path,
            vault_decision_paths=decision_paths,
            token_metrics=token_metrics,
        )

    def _compute_token_delta(
        self,
        metrics_before: dict[str, Any] | None,
        metrics_after: dict[str, Any],
    ) -> dict[str, Any]:
        """Compute token metric deltas (tokens used in this execution).

        Args:
            metrics_before: Token metrics before execution
            metrics_after: Token metrics after execution

        Returns:
            Dict with token delta information
        """
        if not metrics_before:
            # First execution, can't compute delta
            return metrics_after

        delta: dict[str, Any] = {}

        # Compute differences
        if "total_tokens" in metrics_after and "total_tokens" in metrics_before:
            delta["tokens_used"] = (
                metrics_after["total_tokens"] - metrics_before["total_tokens"]
            )
        if "api_calls" in metrics_after and "api_calls" in metrics_before:
            delta["api_calls_made"] = (
                metrics_after["api_calls"] - metrics_before["api_calls"]
            )
        if "cache_hits" in metrics_after and "cache_hits" in metrics_before:
            delta["cache_hits"] = metrics_after["cache_hits"] - metrics_before["cache_hits"]
        if "cache_misses" in metrics_after and "cache_misses" in metrics_before:
            delta["cache_misses"] = (
                metrics_after["cache_misses"] - metrics_before["cache_misses"]
            )

        # Include final hit rate
        if "cache_hit_rate" in metrics_after:
            delta["cache_hit_rate"] = metrics_after["cache_hit_rate"]

        return delta

    def log_inflection_point(
        self,
        title: str,
        context: str,
        decision: str,
        rationale: str,
        project: str = "cohezion",
    ) -> str:
        """Log a critical decision point (called by InflectionDetector).

        Args:
            title: Decision title
            context: What led to this decision
            decision: The decision made
            rationale: Why this decision was made
            project: Project name

        Returns:
            Path to vault decision file
        """
        logger.info("Logging inflection point: %s", title)
        result: str = self.logger.log_decision_point(
            project=project,
            title=title,
            context=context,
            decision=decision,
            rationale=rationale,
        )
        return result


class ExecutorFactory:
    """Factory for creating compound executors with vault integration."""

    _instance: CompoundExecutor | None = None

    @staticmethod
    def create(
        mcp_client: MCPClient,
        token_client: Any | None = None,
        guardrail_pipeline: GuardrailPipeline | None = None,
        enable_guardrails: bool = True,
        inflection_detector: Any | None = None,
        skill_refiner: Any | None = None,
        enable_skill_refinement: bool = True,
    ) -> CompoundExecutor:
        """Create a new compound executor.

        Args:
            mcp_client: Connected MCP client
            token_client: Optional TokenEfficientClient for token-efficient operations
            guardrail_pipeline: Optional GuardrailPipeline for safety checks
            enable_guardrails: If True (default), enable guardrails
            inflection_detector: Optional InflectionDetector for anomaly detection
            skill_refiner: Optional SkillRefiner for learning from executions
            enable_skill_refinement: If True (default), enable skill refinement

        Returns:
            CompoundExecutor instance
        """
        return CompoundExecutor(
            mcp_client,
            token_client,
            guardrail_pipeline,
            enable_guardrails,
            inflection_detector,
            skill_refiner,
            enable_skill_refinement,
        )

    @staticmethod
    def get_singleton(
        mcp_client: MCPClient,
        token_client: Any | None = None,
        guardrail_pipeline: GuardrailPipeline | None = None,
        enable_guardrails: bool = True,
        inflection_detector: Any | None = None,
        skill_refiner: Any | None = None,
        enable_skill_refinement: bool = True,
    ) -> CompoundExecutor:
        """Get or create singleton executor.

        Args:
            mcp_client: Connected MCP client
            token_client: Optional TokenEfficientClient for token-efficient operations
            guardrail_pipeline: Optional GuardrailPipeline for safety checks
            enable_guardrails: If True (default), enable guardrails
            inflection_detector: Optional InflectionDetector for anomaly detection
            skill_refiner: Optional SkillRefiner for learning from executions
            enable_skill_refinement: If True (default), enable skill refinement

        Returns:
            Singleton CompoundExecutor instance
        """
        if ExecutorFactory._instance is None:
            ExecutorFactory._instance = CompoundExecutor(
                mcp_client,
                token_client,
                guardrail_pipeline,
                enable_guardrails,
                inflection_detector,
                skill_refiner,
                enable_skill_refinement,
            )
        return ExecutorFactory._instance

    @staticmethod
    def reset_singleton() -> None:
        """Reset singleton for testing."""
        ExecutorFactory._instance = None
