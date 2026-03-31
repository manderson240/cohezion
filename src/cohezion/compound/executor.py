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

from cohezion.compound.context_integration import CompoundContextMixin
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


class CompoundExecutor(CompoundContextMixin):
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
        retrospection_engine: Any | None = None,
        universe_bridge: Any | None = None,
        skill_health_tracker: Any | None = None,
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
            retrospection_engine: Optional RetrospectionEngine for analyzing
                live execution results and gating skill refinement.
                If None, skill refinement is not gated by retrospection.
            universe_bridge: Optional UniverseBridge for connecting journeys
                to the universe simulation engine. If None, no universe tracking.
            skill_health_tracker: Optional SkillHealthTracker for recording per-skill
                usage metrics (invocations, success rate, tokens, quality).
                If None, no health tracking recorded.
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
        self._retrospection_engine = retrospection_engine
        self._universe_bridge = universe_bridge
        if skill_health_tracker:
            self._skill_health_tracker = skill_health_tracker
        else:
            from cohezion.compound.skill_health_tracker import SkillHealthTracker

            self._skill_health_tracker = SkillHealthTracker()
        self._degradation_mode = False  # HIHO band violation flag
        # Lazy import to avoid circular dependency
        if inflection_detector:
            self.inflection_detector = inflection_detector
        else:
            from cohezion.compound.inflection_detector import InflectionDetectorFactory

            self.inflection_detector = InflectionDetectorFactory.create_default()
        self.logger = VaultLogger(mcp_client=mcp_client)
        # Initialize context manager automatically
        self.__init_context__()
        self._context_loaded = False

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

            self._alignment_analyzer = RequestAlignmentAnalyzerFactory.create(self.mcp_client)
            logger.debug("Initialized default alignment analyzer")

        return self._alignment_analyzer

    def get_experience_guidance(
        self, task_description: str, project: str = "cohezion", operation_type: str = "generate"
    ) -> dict[str, Any]:
        """Fetch experience guidance from vault before execution.

        Enhanced with trajectory search: finds similar past executions and
        provides recommendations based on their outcomes.

        Args:
            task_description: Description of the task to execute
            project: Project name for scoped search
            operation_type: Type of operation (for trajectory search)

        Returns:
            Dict with relevant_context (decisions, experiments, patterns)
            plus trajectory-based recommendations, warnings, and confidence
        """
        logger.info("Fetching experience guidance for: %s", task_description)

        # Step 1: Get base guidance from vault
        base_guidance: dict[str, Any] = self.logger.get_experience_guidance(
            task_description=task_description, project=project
        )

        # Step 2: Enhance with trajectory search (if available)
        try:
            from cohezion.compound.guidance_enhancer import GuidanceEnhancer
            from cohezion.compound.trajectory_search import TrajectorySearchEngine
            from cohezion.flume.experience_collector import ExperienceCollector
            from cohezion.flume.experience_encoder import ExperienceEncoder

            # Initialize search components (lazy)
            collector = ExperienceCollector()
            encoder = ExperienceEncoder()
            search = TrajectorySearchEngine(collector, encoder)
            enhancer = GuidanceEnhancer()

            # Find similar trajectories
            trajectory_results = search.find_similar_trajectories(
                task_description=task_description,
                operation_type=operation_type,
                top_k=5,
                min_coherence=0.4,  # HIHO threshold
            )

            # Enhance guidance
            enhanced = enhancer.enhance_guidance(base_guidance, trajectory_results)
            result = enhancer.to_dict(enhanced)

            logger.info(
                "Guidance enhanced with %d similar trajectories (confidence=%.2f)",
                enhanced.similar_task_count,
                enhanced.confidence,
            )

        except Exception as e:
            logger.debug(
                "Trajectory search failed (non-blocking): %s. Using base guidance only.",
                e,
                exc_info=True,
            )
            result = base_guidance

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

        # Load context automatically if not already done (shoshen-minded automation)
        if not self._context_loaded:
            try:
                self.load_execution_context()
                self._context_loaded = True
                logger.debug("Context loaded automatically for execution")
            except Exception as e:
                logger.warning(f"Failed to auto-load context: {e}")

        # Continue execution - context failure shouldn't block execution

        logger.info(
            "Executing task: %s (operation=%s, skill=%s)",
            task_description,
            operation_type,
            skill_name,
        )

        # Start universe journey if bridge configured
        universe_journey_id: str | None = None
        if self._universe_bridge:
            try:
                universe_journey_id = self._universe_bridge.start_journey(
                    task_description,
                    execution_id=f"exec_{int(time.time())}_{skill_name}",
                )
            except Exception as e:
                logger.debug("Universe bridge start failed (non-blocking): %s", e)

        # Step 1: Get experience guidance (enhanced with trajectory search)
        guidance = self.get_experience_guidance(task_description, project, operation_type)
        logger.debug("Experience guidance: %s", guidance)

        # Step 1.5: Parse request for alignment analysis (if enabled)
        # Skip in degradation mode to conserve resources
        parsed_request = None
        _alignment_patterns = None
        if (
            self._enable_alignment_analysis
            and self.alignment_analyzer
            and not self._degradation_mode
        ):
            try:
                request_text = human_request or task_description
                parsed_request = self.alignment_analyzer.parse_request(request_text)
                _alignment_patterns = self.alignment_analyzer.query_alignment_patterns(
                    task_description, project
                )
                logger.debug(
                    "Parsed request: intent=%s (confidence=%.2f), %d constraints, %d criteria",
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
                self.guardrail_pipeline.check_input(task_description, guard_context)
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
            token_metrics = self._compute_token_delta(token_metrics_before, token_metrics_after)
            logger.debug("Token metrics: %s", token_metrics)

        # Check output via guardrails if successful
        if success and self.guardrail_pipeline:
            guard_context = {
                "skill_name": skill_name,
                "operation_type": operation_type,
                "task_description": task_description,
            }
            output_check = _run_async_guardrail(
                self.guardrail_pipeline.check_output(output, guard_context)
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
                    logger.debug("Failed to log inflection point (non-blocking): %s", e)
        except Exception as e:
            logger.debug("Anomaly detection failed (non-blocking): %s", e, exc_info=True)

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

        # Step 5.8: Compute real cohesion score from available signals
        # Cohesion = overlap between agent's internal intent and precipitated result
        cohesion_components: list[float] = []
        # Precipitation success: did reality match intent?
        cohesion_components.append(0.7 if success else 0.2)
        # Spin alignment: inverse of anomaly score (low anomaly = high alignment)
        # Default 0.0 = no anomaly detected (assume clean if detection unavailable)
        cohesion_components.append(1.0 - metrics.get("anomaly_score", 0.0))
        # Quadrature consensus: alignment with human request
        if alignment_data := metrics.get("alignment", {}):
            cohesion_components.append(alignment_data.get("intent_match", 0.5))
        metrics["coherence"] = sum(cohesion_components) / len(cohesion_components)

        # Step 6: If successful, extract patterns (skip in degradation mode)
        if success and experiment_path and not self._degradation_mode:
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

        # Step 7.3: Retrospection analysis (gates skill refinement)
        retrospection_context: dict[str, Any] | None = None
        should_refine = True  # default: refine if no retrospection engine
        if self._retrospection_engine:
            try:
                temp_result = ExecutionResult(
                    success=success,
                    output=output,
                    metrics=metrics,
                    duration_seconds=duration_seconds,
                    token_metrics=token_metrics,
                )
                retrospection_context = self._retrospection_engine.analyze_execution_result(
                    temp_result, skill_name
                )
                if retrospection_context is not None:
                    should_refine = retrospection_context.get("should_refine", True)
                    if retrospection_context.get("insights"):
                        metrics["retrospection_insights"] = retrospection_context["insights"]
                logger.debug(
                    "Retrospection: should_refine=%s, compound=%.3f",
                    should_refine,
                    retrospection_context.get("compound_score", 0.0)
                    if retrospection_context
                    else 0.0,
                )
            except Exception as e:
                logger.debug("Retrospection failed (non-blocking): %s", e, exc_info=True)

        # Step 7: Refine skills based on execution results (non-blocking)
        # Gated by retrospection: only refine when quadrature assessment warrants it
        if success and self.skill_refiner and should_refine:
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
                logger.debug("Skill refinement failed (non-blocking): %s", e, exc_info=True)

        # Step 7.4: Record skill health metrics (non-blocking)
        if self._skill_health_tracker:
            try:
                tokens = 0
                quality = 0.0
                if token_metrics:
                    tokens = token_metrics.get("tokens_used", 0)
                quality = metrics.get("coherence", 0.0)
                self._skill_health_tracker.record_usage(
                    skill_name=skill_name,
                    success=success,
                    tokens_used=tokens,
                    quality_score=quality,
                )
            except Exception as e:
                logger.warning(f"Skill health tracking failed (non-blocking): {e}")

        # Step 7.5: Check for degradation and manage HIHO band (non-blocking)
        # Coherence within HIHO band [0.4, 0.6] -> exit degradation mode
        # Coherence outside band with CRITICAL alert -> enter degradation mode
        coherence_val = metrics.get("coherence", 0.5)
        if 0.4 <= coherence_val <= 0.6 and self._degradation_mode:
            logger.info(
                "Cohesion returned to HIHO band (%.2f), exiting degradation mode", coherence_val
            )
            self._degradation_mode = False

        if self._degradation_detector:
            try:
                degradation_metrics = {
                    "combined_hit_rate": 0.0,
                    "tokens_per_second": 0.0,
                    "mean_coherence": coherence_val,
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
                alerts = self._degradation_detector.check_degradation(degradation_metrics)
                if alerts:
                    metrics["degradation_alerts"] = len(alerts)
                    for alert in alerts:
                        logger.warning(
                            "Degradation alert [%s]: %s",
                            alert.severity.value,
                            alert.message,
                        )
                    # Log critical alerts to vault and enter degradation mode
                    critical_alerts = [a for a in alerts if a.severity.value == "CRITICAL"]
                    if critical_alerts:
                        self._degradation_mode = True
                        metrics["execution_degraded"] = True
                        logger.warning(
                            "Entering degradation mode: %d CRITICAL alerts, "
                            "cohesion=%.2f outside HIHO band",
                            len(critical_alerts),
                            coherence_val,
                        )
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
                logger.debug("Degradation detection failed (non-blocking): %s", e)

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
                logger.debug("Model quality recording failed (non-blocking): %s", e)

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
        journey_point_tracked = False
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
                journey_point_tracked = True
                # Propagate phi_score to metrics for retrospection
                if point and point.metadata:
                    metrics["phi_score"] = point.metadata.get("phi_score", 0.0)
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
                            _task = asyncio.ensure_future(
                                self._journey_persistence.save_trajectory_point(
                                    exec_id,
                                    point_data,
                                )
                            )
                        except RuntimeError:
                            asyncio.run(
                                self._journey_persistence.save_trajectory_point(
                                    exec_id,
                                    point_data,
                                )
                            )
                    except Exception as e:
                        logger.debug("Journey persistence failed (non-blocking): %s", e)
            except Exception as e:
                logger.debug("Journey tracking failed (non-blocking): %s", e)

        # Step 9.5: Add trajectory point to universe bridge (non-blocking)
        # Only proceed if Step 9 succeeded to avoid stale data
        if self._universe_bridge and universe_journey_id and journey_point_tracked:
            try:
                if self._journey_tracker:
                    last_point = self._journey_tracker.get_last_point()
                    if last_point:
                        self._universe_bridge.add_point(
                            universe_journey_id,
                            last_point,
                            step_number=self._journey_tracker.get_recent_point_count(),
                            action=operation_type,
                        )
            except Exception as e:
                logger.debug("Universe bridge point failed (non-blocking): %s", e)

        # Step 10: Complete universe journey (non-blocking)
        if self._universe_bridge and universe_journey_id:
            try:
                phi = metrics.get("phi_score", 0.0)
                self._universe_bridge.complete_journey(
                    universe_journey_id,
                    success=success,
                    phi_score=phi,
                    output=output[:500],
                )
            except Exception as e:
                logger.debug("Universe bridge completion failed (non-blocking): %s", e)

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
            delta["tokens_used"] = metrics_after["total_tokens"] - metrics_before["total_tokens"]
        if "api_calls" in metrics_after and "api_calls" in metrics_before:
            delta["api_calls_made"] = metrics_after["api_calls"] - metrics_before["api_calls"]
        if "cache_hits" in metrics_after and "cache_hits" in metrics_before:
            delta["cache_hits"] = metrics_after["cache_hits"] - metrics_before["cache_hits"]
        if "cache_misses" in metrics_after and "cache_misses" in metrics_before:
            delta["cache_misses"] = metrics_after["cache_misses"] - metrics_before["cache_misses"]

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
        retrospection_engine: Any | None = None,
        universe_bridge: Any | None = None,
        skill_health_tracker: Any | None = None,
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
            retrospection_engine: Optional RetrospectionEngine
            universe_bridge: Optional UniverseBridge
            skill_health_tracker: Optional SkillHealthTracker

        Returns:
            CompoundExecutor (or TokenEfficientCompoundExecutor when token_client provided)
        """
        # When token_client is available, use TokenEfficientCompoundExecutor
        # for automatic API prompt caching (static prefix/dynamic suffix separation)
        executor_class = CompoundExecutor
        if token_client is not None:
            try:
                from cohezion.compound.token_efficient_executor import (
                    TokenEfficientCompoundExecutor,
                )

                executor_class = TokenEfficientCompoundExecutor
                logger.info(
                    "ExecutorFactory: using TokenEfficientCompoundExecutor (token_client provided)"
                )
            except ImportError:
                logger.debug("TokenEfficientCompoundExecutor not available, using base executor")

        return executor_class(
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
            retrospection_engine=retrospection_engine,
            universe_bridge=universe_bridge,
            skill_health_tracker=skill_health_tracker,
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
        retrospection_engine: Any | None = None,
        universe_bridge: Any | None = None,
        skill_health_tracker: Any | None = None,
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
            retrospection_engine: Optional RetrospectionEngine
            universe_bridge: Optional UniverseBridge

        Returns:
            Singleton CompoundExecutor instance
        """
        if ExecutorFactory._instance is None:
            ExecutorFactory._instance = ExecutorFactory.create(
                mcp_client=mcp_client,
                token_client=token_client,
                guardrail_pipeline=guardrail_pipeline,
                enable_guardrails=enable_guardrails,
                inflection_detector=inflection_detector,
                skill_refiner=skill_refiner,
                enable_skill_refinement=enable_skill_refinement,
                metrics_collector=metrics_collector,
                journey_tracker=journey_tracker,
                journey_persistence=journey_persistence,
                alignment_analyzer=alignment_analyzer,
                enable_alignment_analysis=enable_alignment_analysis,
                degradation_detector=degradation_detector,
                model_quality_classifier=model_quality_classifier,
                retrospection_engine=retrospection_engine,
                universe_bridge=universe_bridge,
                skill_health_tracker=skill_health_tracker,
            )
        return ExecutorFactory._instance

    @staticmethod
    def reset_singleton() -> None:
        """Reset singleton for testing."""
        ExecutorFactory._instance = None
