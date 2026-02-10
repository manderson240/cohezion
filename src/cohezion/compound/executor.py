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

from cohezion.compound.exp_persistence.vault import (
    ExecutionContext,
    VaultLogger,
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
        metrics_collector: Any | None = None,
        journey_tracker: Any | None = None,
        journey_persistence: Any | None = None,
        alignment_analyzer: Any | None = None,
        enable_alignment_analysis: bool = False,
        degradation_detector: Any | None = None,
        model_quality_classifier: Any | None = None,
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
            metrics_collector: Optional CompoundMetricsCollector for recording
                execution metrics. If None, no metrics recorded.
            journey_tracker: Optional JourneyTracker for 12D FLUME trajectory
                tracking. If None, no journey tracking.
            journey_persistence: Optional JourneyPersistence for persisting
                journey data. Requires journey_tracker to be set.
            alignment_analyzer: Optional RequestAlignmentAnalyzer for request
                alignment analysis. If None and enable_alignment_analysis is True,
                creates default analyzer.
            enable_alignment_analysis: If True, enable alignment analysis
                (requires alignment_analyzer or auto-creates one).
            degradation_detector: Optional DegradationDetector for monitoring
                metric drops (cache hit rate, token efficiency, coherence).
                If None, no degradation detection.
            model_quality_classifier: Optional ModelQualityClassifier for
                predicting model failure likelihood. If None, no quality
                classification.
        """
        self.mcp_client = mcp_client
        self.token_client = token_client
        self._guardrail_pipeline = guardrail_pipeline
        self._enable_guardrails = enable_guardrails
        self._skill_refiner = skill_refiner
        self._enable_skill_refinement = enable_skill_refinement
        self._metrics_collector = metrics_collector
        self._journey_tracker = journey_tracker
        self._journey_persistence = journey_persistence
        self._alignment_analyzer = alignment_analyzer
        self._enable_alignment_analysis = enable_alignment_analysis
        self._degradation_detector = degradation_detector
        self._model_quality_classifier = model_quality_classifier
        # Lazy import to avoid circular dependency
        if inflection_detector:
            self.inflection_detector = inflection_detector
        else:
            from cohezion.compound.inflection_detector import InflectionDetectorFactory
            self.inflection_detector = InflectionDetectorFactory.create_default()
        self.logger = VaultLogger(mcp_client=mcp_client)

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

    @property
    def alignment_analyzer(self) -> Any | None:
        """Lazy-initialize default alignment analyzer if enabled.

        Returns:
            RequestAlignmentAnalyzer if alignment analysis enabled, None otherwise
        """
        if not self._enable_alignment_analysis:
            return None

        if self._alignment_analyzer is None:
            from cohezion.compound.request_alignment_analyzer import (
                RequestAlignmentAnalyzerFactory,
            )

            self._alignment_analyzer = RequestAlignmentAnalyzerFactory.create(
                self.mcp_client
            )
            logger.debug("Initialized default alignment analyzer")

        return self._alignment_analyzer

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
        human_request: str | None = None,
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
            human_request: Optional raw request text for alignment analysis

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

        # Step 1.5: Parse request for alignment analysis (if enabled)
        parsed_request = None
        alignment_patterns = None
        if self._enable_alignment_analysis and self.alignment_analyzer:
            try:
                request_text = human_request or task_description
                parsed_request = self.alignment_analyzer.parse_request(request_text)
                alignment_patterns = self.alignment_analyzer.query_alignment_patterns(
                    task_description, project
                )
                logger.debug(
                    "Parsed request: intent=%s (confidence=%.2f), "
                    "%d constraints, %d criteria",
                    parsed_request.intent.value,
                    parsed_request.intent_confidence,
                    len(parsed_request.constraints),
                    len(parsed_request.criteria),
                )
            except Exception as e:
                logger.debug(
                    "Request alignment parsing failed (non-blocking): %s", e, exc_info=True
                )

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

        # Step 5.5: Analyze request-execution alignment (if enabled)
        if self._enable_alignment_analysis and self.alignment_analyzer and parsed_request:
            try:
                from cohezion.compound.inflection_detector import Severity

                temp_result = ExecutionResult(
                    success=success,
                    output=output,
                    metrics=metrics,
                    duration_seconds=duration_seconds,
                    token_metrics=token_metrics,
                )

                # Get anomaly analysis if available
                anomaly_analysis = None
                if "anomaly_severity" in metrics:
                    # Create a minimal anomaly object for alignment analysis
                    from cohezion.compound.inflection_detector import AnomalyDetection

                    severity_val = metrics.get("anomaly_severity", "info")
                    severity_enum = Severity(severity_val)
                    anomaly_analysis = AnomalyDetection(
                        severity=severity_enum,
                        score=metrics.get("anomaly_score", 0.0),
                        issues=metrics.get("anomaly_issues", []),
                        recommendations=metrics.get("anomaly_recommendations", []),
                        should_reexecute=False,
                    )

                alignment = self.alignment_analyzer.analyze_alignment(
                    parsed_request, temp_result, operation_type, anomaly_analysis
                )

                # Log alignment to vault if high misalignment
                if alignment.misalignment_score > 0.3:
                    vault_path = self.alignment_analyzer.log_alignment_to_vault(
                        parsed_request, alignment, project
                    )
                    if vault_path:
                        decision_paths.append(vault_path)
                        logger.debug("Logged alignment analysis: %s", vault_path)

                # Add alignment metrics to result
                metrics["alignment"] = {
                    "misalignment_score": alignment.misalignment_score,
                    "intent_match": alignment.intent_match_score,
                    "constraint_satisfaction": alignment.constraint_satisfaction,
                    "criteria_satisfaction": alignment.criteria_satisfaction,
                    "violations_count": len(alignment.violations),
                    "failures_count": len(alignment.failures),
                    "issues_count": len(alignment.issues),
                    "should_retry": alignment.should_retry,
                }
                logger.debug("Alignment analysis: %s", metrics["alignment"])
            except Exception as e:
                logger.debug(
                    "Request alignment analysis failed (non-blocking): %s",
                    e,
                    exc_info=True,
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

        # Step 7.5: Check for degradation (non-blocking)
        if self._degradation_detector:
            try:
                degradation_metrics = {
                    "combined_hit_rate": 0.0,
                    "tokens_per_second": 0.0,
                    "mean_coherence": metrics.get("coherence", 0.5),
                    "elapsed_seconds": duration_seconds,
                    "success_rate": 1.0 if success else 0.0,
                }
                if token_metrics:
                    degradation_metrics["combined_hit_rate"] = token_metrics.get(
                        "cache_hit_rate", token_metrics.get("combined_hit_rate", 0.0)
                    )
                    degradation_metrics["tokens_per_second"] = token_metrics.get(
                        "tokens_per_second", 0.0
                    )
                alerts = self._degradation_detector.check_degradation(
                    degradation_metrics
                )
                if alerts:
                    metrics["degradation_alerts"] = len(alerts)
                    for alert in alerts:
                        logger.warning(
                            "Degradation alert [%s]: %s",
                            alert.severity.value,
                            alert.message,
                        )
                    # Log critical alerts to vault
                    critical_alerts = [
                        a
                        for a in alerts
                        if a.severity.value == "CRITICAL"
                    ]
                    for alert in critical_alerts:
                        try:
                            dp = self.log_inflection_point(
                                title=f"Degradation: {alert.metric}",
                                context=f"Task: {task_description}\n{alert.message}",
                                decision="Investigate degradation",
                                rationale=f"Current: {alert.current_value:.3f}, "
                                f"Baseline: {alert.baseline_value:.3f}, "
                                f"Threshold: {alert.threshold:.3f}",
                                project=project,
                            )
                            if dp:
                                decision_paths.append(dp)
                        except Exception as e:
                            logger.debug(
                                "Failed to log degradation alert (non-blocking): %s",
                                e,
                            )
            except Exception as e:
                logger.debug(
                    "Degradation detection failed (non-blocking): %s", e
                )

        # Step 7.7: Record model quality (non-blocking)
        if self._model_quality_classifier:
            try:
                model_name = "unknown"
                tokens_used_for_quality = 0
                if token_metrics:
                    model_name = token_metrics.get("model", "unknown")
                    tokens_used_for_quality = token_metrics.get("tokens_used", 0)
                self._model_quality_classifier.add_execution(
                    model=model_name,
                    coherence=metrics.get("coherence", 0.5),
                    success=success,
                    tokens_used=tokens_used_for_quality,
                    duration=duration_seconds,
                )
            except Exception as e:
                logger.debug(
                    "Model quality recording failed (non-blocking): %s", e
                )

        # Step 8: Record metrics (non-blocking)
        if self._metrics_collector:
            try:
                tokens_used = 0
                model_used = ""
                if token_metrics:
                    tokens_used = token_metrics.get("tokens_used", 0)
                    model_used = token_metrics.get("model", "")
                self._metrics_collector.record_execution(
                    skill_name=skill_name,
                    success=success,
                    tokens_used=tokens_used,
                    duration_ms=duration_seconds * 1000,
                    model_used=model_used,
                )
            except Exception as e:
                logger.debug("Metrics recording failed (non-blocking): %s", e)

        # Step 9: Track journey (non-blocking)
        if self._journey_tracker:
            try:
                temp_result = ExecutionResult(
                    success=success,
                    output=output,
                    metrics=metrics,
                    duration_seconds=duration_seconds,
                    token_metrics=token_metrics,
                )
                point = self._journey_tracker.track_execution(
                    temp_result, task_description, operation_type
                )
                if self._journey_persistence and point:
                    try:
                        point_data = {
                            "coherence": point.coherence,
                            "efficiency": point.efficiency,
                            "operation_type": point.operation_type,
                            "task_description": point.task_description[:200],
                            "timestamp": point.timestamp,
                        }
                        if point.metadata:
                            point_data["metadata"] = point.metadata
                        import asyncio
                        exec_id = f"exec_{int(time.time())}"
                        try:
                            asyncio.get_running_loop()
                            _task = asyncio.ensure_future(  # noqa: RUF006
                                self._journey_persistence
                                .save_trajectory_point(
                                    exec_id, point_data,
                                )
                            )
                        except RuntimeError:
                            asyncio.run(
                                self._journey_persistence
                                .save_trajectory_point(
                                    exec_id, point_data,
                                )
                            )
                    except Exception as e:
                        logger.debug("Journey persistence failed (non-blocking): %s", e)
            except Exception as e:
                logger.debug("Journey tracking failed (non-blocking): %s", e)

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

        # Pass through model name and other non-delta fields
        if "model" in metrics_after:
            delta["model"] = metrics_after["model"]
        if "combined_hit_rate" in metrics_after:
            delta["combined_hit_rate"] = metrics_after["combined_hit_rate"]
        if "tokens_per_second" in metrics_after:
            delta["tokens_per_second"] = metrics_after["tokens_per_second"]

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
        metrics_collector: Any | None = None,
        journey_tracker: Any | None = None,
        journey_persistence: Any | None = None,
        alignment_analyzer: Any | None = None,
        enable_alignment_analysis: bool = False,
        degradation_detector: Any | None = None,
        model_quality_classifier: Any | None = None,
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
            metrics_collector: Optional CompoundMetricsCollector
            journey_tracker: Optional JourneyTracker
            journey_persistence: Optional JourneyPersistence
            alignment_analyzer: Optional RequestAlignmentAnalyzer
            enable_alignment_analysis: If True, enable alignment analysis
            degradation_detector: Optional DegradationDetector
            model_quality_classifier: Optional ModelQualityClassifier

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
            metrics_collector=metrics_collector,
            journey_tracker=journey_tracker,
            journey_persistence=journey_persistence,
            alignment_analyzer=alignment_analyzer,
            enable_alignment_analysis=enable_alignment_analysis,
            degradation_detector=degradation_detector,
            model_quality_classifier=model_quality_classifier,
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
        metrics_collector: Any | None = None,
        journey_tracker: Any | None = None,
        journey_persistence: Any | None = None,
        alignment_analyzer: Any | None = None,
        enable_alignment_analysis: bool = False,
        degradation_detector: Any | None = None,
        model_quality_classifier: Any | None = None,
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
            metrics_collector: Optional CompoundMetricsCollector
            journey_tracker: Optional JourneyTracker
            journey_persistence: Optional JourneyPersistence
            alignment_analyzer: Optional RequestAlignmentAnalyzer
            enable_alignment_analysis: If True, enable alignment analysis
            degradation_detector: Optional DegradationDetector
            model_quality_classifier: Optional ModelQualityClassifier

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
                metrics_collector=metrics_collector,
                journey_tracker=journey_tracker,
                journey_persistence=journey_persistence,
                alignment_analyzer=alignment_analyzer,
                enable_alignment_analysis=enable_alignment_analysis,
                degradation_detector=degradation_detector,
                model_quality_classifier=model_quality_classifier,
            )
        return ExecutorFactory._instance

    @staticmethod
    def reset_singleton() -> None:
        """Reset singleton for testing."""
        ExecutorFactory._instance = None
