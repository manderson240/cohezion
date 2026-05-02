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
from cohezion.compound.executor_integration import ExecutorIntegrationMixin
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


class CompoundExecutor(CompoundContextMixin, ExecutorIntegrationMixin):
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
        self._drr_generator = None
        self._drr_session_id = ""
        try:
            from cohezion.compound.design_review_report import DRRGenerator

            self._drr_generator = DRRGenerator()
        except ImportError:
            pass
        if skill_health_tracker:
            self._skill_health_tracker = skill_health_tracker
        else:
            from cohezion.compound.skill_health_tracker import SkillHealthTracker

            self._skill_health_tracker = SkillHealthTracker()

        # Geometric Latent Bridge for topological reasoning
        try:
            from cohezion.flume.geometric_bridge import GeometricLatentBridge

            self.geometric_bridge = GeometricLatentBridge()
            logger.debug("GeometricLatentBridge initialized")
        except ImportError:
            self.geometric_bridge = None
            logger.debug("GeometricLatentBridge not available")

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

        # Context policy for adaptive breadth/depth
        from cohezion.compound.context_policy import ContextPolicy

        self._context_policy = ContextPolicy(vault_logger=self.logger)
        self.set_context_policy(self._context_policy)

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

    def _try_template_match(self, task_description: str) -> dict[str, Any] | None:
        """Check cache for a template match before LLM execution.

        Uses CacheWarmer.find_template_match() if available. Returns cached
        response dict if match found (>0.85 similarity), None otherwise.
        Non-blocking: returns None on any error.
        """
        try:
            from cohezion.cache.cache_warmer import CacheWarmer
            from cohezion.cache.semantic_cache import SemanticCache

            cache = SemanticCache.get_instance() if hasattr(SemanticCache, "get_instance") else None
            if cache is None:
                return None

            warmer = CacheWarmer(cache)
            # Sync wrapper — find_template_match is async but we need sync here
            import asyncio

            try:
                loop = asyncio.get_running_loop()
                # Already in async context — can't block
                return None
            except RuntimeError:
                # No running loop — safe to run
                return asyncio.run(warmer.find_template_match(task_description))

        except Exception:
            logger.debug("Template matching failed (non-blocking)", exc_info=True)
            return None

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

        # Step 3: Query SurrealDB for recent retrospection decisions (closes feedback loop)
        try:
            import json
            import urllib.request
            from base64 import b64encode

            req = urllib.request.Request(
                "http://localhost:8001/sql",
                data=b"SELECT skill, should_refine, compound_score, recommendation FROM retrospection ORDER BY created DESC LIMIT 3;",
                headers={
                    "Accept": "application/json",
                    "surreal-ns": "cohezion",
                    "surreal-db": "cohezion",
                    "Authorization": "Basic " + b64encode(b"root:root").decode(),
                },
                method="POST",
            )
            resp = urllib.request.urlopen(req, timeout=2)
            data = json.loads(resp.read())
            if data and data[0].get("status") == "OK" and data[0]["result"]:
                result["recent_retrospections"] = data[0]["result"]
                logger.debug(
                    "Guidance enriched with %d recent retrospections", len(data[0]["result"])
                )
        except Exception:
            pass  # Non-blocking: SurrealDB may be unavailable

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

        # Step 0.5: Classify task and apply context policy (adaptive breadth/depth)
        _task_profile = None
        _context_budget = None
        try:
            _context_budget = self.apply_policy(task_description, operation_type)
            if _context_budget is not None:
                _task_profile = self._context_policy.classify_task(task_description, operation_type)
        except Exception as e:
            logger.debug("Context policy classification failed (non-blocking): %s", e)

        # Step 1: Get experience guidance (enhanced with trajectory search)
        guidance = self.get_experience_guidance(task_description, project, operation_type)
        logger.debug("Experience guidance: %s", guidance)

        # Step 1.3: Template matching — check cache for similar completed task
        # If a high-similarity match exists, skip the LLM call entirely
        template_match = self._try_template_match(task_description)
        if template_match is not None:
            logger.info(
                "Template hit (%.0f%% sim, source=%s) — skipping LLM, saved ~%d tokens",
                template_match["similarity"] * 100,
                template_match["source"],
                template_match.get("tokens_saved", 0),
            )
            return ExecutionResult(
                success=True,
                output=template_match["response"],
                metrics={
                    "template_match": True,
                    "similarity": template_match["similarity"],
                    "source": template_match["source"],
                    "tokens_saved": template_match.get("tokens_saved", 0),
                },
                duration_seconds=time.time() - start_seconds,
                vault_experiment_path="",
                token_metrics={"template_hit": True, "tokens_used": 0},
            )

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

        # Step 1.7: Reactive context adjustment (Tier 1 — critical signals only)
        if _context_budget is not None and self._context_policy:
            try:
                from cohezion.compound.context_policy import ContextSignals

                signals = ContextSignals(
                    coherence_state=self._context_manager.coherence_state,
                    token_usage=self._context_manager.token_usage,
                )
                _context_budget = self._context_policy.adjust_immediate(_context_budget, signals)
            except Exception as e:
                logger.debug("Context policy adjustment failed (non-blocking): %s", e)

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

        # Step 4.5: Log execution trace (Meta-Harness L225 pattern)
        # Structured trace for filesystem browsing instead of prompt summaries
        try:
            self.logger.log_execution_trace(
                ctx=ctx,
                success=success,
                output=output[:500],
                metrics=metrics,
                token_metrics=token_metrics,
            )
        except Exception:
            logger.debug("Execution trace logging failed (non-blocking)", exc_info=True)

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

        # Step 5.85: V-Model DRR gate (non-blocking)
        if self._drr_generator:
            try:
                from cohezion.compound.design_review_report import GateLevel

                drr = self._drr_generator.generate(
                    gate=GateLevel.IMPLEMENTATION,
                    session_id=self._drr_session_id or "unknown",
                    left_artifact=skill_name or "unknown",
                    right_artifact=task_description[:100] if task_description else "unknown",
                )
                metrics["drr_gate"] = drr.gate.value
                metrics["drr_passed"] = drr.passed
                metrics["drr_findings"] = len(drr.findings)
                if not drr.passed:
                    logger.warning("DRR-%s FAILED: %s", drr.gate.value, drr.summary)
            except Exception:
                logger.debug("DRR gate check failed (non-blocking)", exc_info=True)

        # Step 5.9: Natural capital valuation (non-blocking)
        # Maps HIHO proximity to habitat quality via InVEST-inspired model
        try:
            import numpy as np

            from cohezion.physics.natural_capital import NaturalCapitalValuation

            ncv = NaturalCapitalValuation()
            coherence_val_nc = metrics.get("coherence", 0.5)
            state_12d = np.full(12, coherence_val_nc)
            nc_metrics = ncv.evaluate(
                state_12d=state_12d,
                coherence=coherence_val_nc,
                connectivity=0.5,
                gauge_curvature=0.0,
                spore_density=0.5,
            )
            metrics["natural_capital"] = nc_metrics.total_natural_capital
            metrics["habitat_quality"] = nc_metrics.habitat_quality
            # Blend natural capital into coherence (10% weight)
            metrics["coherence"] = metrics["coherence"] * 0.9 + nc_metrics.habitat_quality * 0.1
        except (ImportError, Exception):
            pass  # Non-blocking: natural_capital module may not be available

        # Step 5.91: Autoresearch dispatch (non-blocking, research tasks only)
        _RESEARCH_KEYWORDS = {"train", "optimize", "research", "experiment", "tune", "improve loss"}
        if any(kw in task_description.lower() for kw in _RESEARCH_KEYWORDS):
            try:
                import asyncio as _asyncio

                from cohezion.research.autoresearch_driver import AutoresearchDriver

                _target = (
                    "jepa"
                    if "jepa" in task_description.lower()
                    else (
                        "flume_vae"
                        if "flume" in task_description.lower()
                        else (
                            "rl_ppo"
                            if any(w in task_description.lower() for w in ("rl", "ppo", "reward"))
                            else "jepa"
                        )
                    )
                )
                _driver = AutoresearchDriver(target=_target, budget_seconds=60)
                if _asyncio.get_event_loop().is_running():
                    _asyncio.ensure_future(_driver.run_loop(n_iterations=1))
                metrics["autoresearch_target"] = _target
            except (ImportError, Exception):
                pass  # Non-blocking: autoresearch module may not be available

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
        # Gated by retrospection AND DRR: only refine when both pass
        drr_passed = metrics.get("drr_passed", True)  # Default True if DRR not run
        if not drr_passed:
            should_refine = False
            logger.info(
                "Skill refinement blocked: DRR gate failed (%s)", metrics.get("drr_gate", "?")
            )
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

        # Step 7.6: Geometric Latent Mapping (Symmetry-Driven Reasoning)
        # Map the latent state of the execution to a topological regime
        if self.geometric_bridge:
            try:
                import torch

                # Attempt to extract latent vector from metrics or execute_fn result
                latent_vec = metrics.get("latent_vector")
                if latent_vec is None and token_metrics:
                    # Fallback: simulate a latent vector from token metrics if real one isn't provided
                    # In a real integration, the LLM provider would return the VAE z-vector
                    latent_vec = torch.randn(256)

                if latent_vec is not None:
                    # Ensure it's a torch tensor
                    if not isinstance(latent_vec, torch.Tensor):
                        latent_vec = torch.tensor(latent_vec).float()

                    regime = self.geometric_bridge.map_to_regime(latent_vec)
                    coords = self.geometric_bridge.project_to_coordinates(latent_vec)

                    metrics["topological_regime"] = regime
                    metrics["mereon_coords"] = coords.tolist()

                    logger.debug(f"Latent state mapped to {regime} regime at {coords}")

                    # Persist regime to vault as a decision point for distillation
                    if regime in ["A", "C", "Inner"]:
                        regime_path = self.log_inflection_point(
                            title=f"Regime Transition: {regime}",
                            context=f"Task: {task_description}\nSymmetry: {regime}",
                            decision="Distillation trigger",
                            rationale=f"Latent state aligned with {regime} sector of Mereon manifold",
                            project=project,
                        )
                        if regime_path:
                            decision_paths.append(regime_path)
            except Exception as e:
                logger.debug(f"Geometric latent mapping failed (non-blocking): {e}")

        # Step 7.7: Bioelectric coherence monitoring (non-blocking)
        # Maps execution coherence to Levin bioelectric network state
        try:
            import numpy as np

            from cohezion.physics.bioelectric_model import BioelectricNetwork

            bio_net = BioelectricNetwork(n_cells=8)
            bio_net.set_uniform_conductance(0.3)
            # Map coherence [0,1] to membrane potentials [-1,1]
            bio_net.v_mem = np.full(8, coherence_val * 2 - 1)
            bio_net.simulate(n_steps=10, dt=0.01)
            bio_coherence = bio_net.coherence()
            metrics["bioelectric_coherence"] = float(bio_coherence)
            percolation = bio_net.percolation_analysis()
            metrics["bioelectric_percolated"] = percolation.is_percolated
        except (ImportError, Exception):
            pass  # Non-blocking: bioelectric_model may not be available

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

        # Step 9.1: Persist universe snapshot (L183)
        # Record a universe state snapshot to SurrealDB for world model training
        try:
            import asyncio

            from cohezion.persistence.genesis_persistence import persist_universe_snapshot

            _snap_coro = persist_universe_snapshot(
                tick=int(time.time()),
                global_coherence=metrics.get("coherence", 0.5),
                symmetry_group="SU2",
                temperature=float(metrics.get("temperature", 0.5)),
                n_agents=1,
            )
            try:
                asyncio.get_running_loop()
                asyncio.ensure_future(_snap_coro)
            except RuntimeError:
                asyncio.run(_snap_coro)
        except Exception as e:
            logger.debug("Universe snapshot persistence failed (non-blocking): %s", e)

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

        # Step 10.5: OuroborosBridge physics check (non-blocking)
        # Cross-validate coherence via physics layer and trigger healing if anomalous
        try:
            from cohezion.physics.ouroboros_bridge import OuroborosBridge

            if not hasattr(self, "_ouroboros_bridge_instance"):
                self._ouroboros_bridge_instance = OuroborosBridge()
            coherence_val = metrics.get("coherence", 0.5)
            coherence_drop = abs(coherence_val - 0.5)
            if coherence_drop > 0.3:
                import asyncio

                try:
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        logger.debug(
                            "Ouroboros: coherence drop %.3f (async deferred)", coherence_drop
                        )
                    else:
                        loop.run_until_complete(
                            self._ouroboros_bridge_instance.check_coherence(
                                coherence_drop, task_id=skill_name
                            )
                        )
                except RuntimeError:
                    logger.debug("Ouroboros: no event loop, skipping async check")
        except (ImportError, Exception):
            pass  # Non-blocking: ouroboros bridge may not be available

        # Step 10.6: Mycelium learning capture (non-blocking)
        # Auto-capture execution results into MyceliumRegistry for skill synthesis
        try:
            if success:
                from cohezion.learning.mycelium_registry import JournalEntry, MyceliumRegistry

                if not hasattr(self, "_mycelium_registry"):
                    self._mycelium_registry = MyceliumRegistry()
                entry = JournalEntry(
                    entry_id=f"exec_{int(time.time())}_{skill_name}",
                    content=f"Executed {skill_name}: {task_description[:200]}",
                    domain="pattern",
                )
                self._mycelium_registry.ingest_entry(entry)
                # Trigger audit every 10 entries to synthesize new skills
                if (
                    hasattr(self._mycelium_registry, "_entries")
                    and len(self._mycelium_registry._entries) % 10 == 0
                ):
                    try:
                        report = self._mycelium_registry.run_audit()
                        logger.info(
                            "Mycelium audit: %d skills synthesized",
                            getattr(report, "skills_synthesized", 0) if report else 0,
                        )
                    except Exception:
                        logger.debug("Mycelium audit failed (non-blocking)")
                logger.debug("Mycelium: captured execution as pattern entry")
        except (ImportError, Exception):
            pass  # Non-blocking: mycelium may not be available

        # Step 10.7: Persist prompt artifact (L183)
        # Record prompt/response pair to SurrealDB for retrospective analysis
        try:
            import asyncio

            from cohezion.persistence.genesis_persistence import persist_prompt_artifact

            _artifact_coro = persist_prompt_artifact(
                prompt_text=task_description,
                response_text=output[:2000],
                model_id=token_metrics.get("model", "unknown") if token_metrics else "unknown",
                confidence=metrics.get("coherence", 0.5),
                latency_ms=metrics.get("duration_seconds", 0.0) * 1000,
            )
            try:
                asyncio.get_running_loop()
                asyncio.ensure_future(_artifact_coro)
            except RuntimeError:
                asyncio.run(_artifact_coro)
        except Exception as e:
            logger.debug("Prompt artifact persistence failed (non-blocking): %s", e)

        # Step 10.9: Record context policy outcome for cross-session learning
        if _task_profile is not None and _context_budget is not None:
            try:
                self._context_policy.record_outcome(
                    profile=_task_profile,
                    budget=_context_budget,
                    execution_success=success,
                    coherence_final=metrics.get("coherence", 0.5),
                )
            except Exception as e:
                logger.debug("Context policy outcome recording failed (non-blocking): %s", e)

        return ExecutionResult(
            success=success,
            output=output,
            metrics=metrics,
            duration_seconds=duration_seconds,
            vault_experiment_path=experiment_path,
            vault_decision_paths=decision_paths,
            token_metrics=token_metrics,
        )

    # Integration methods (_compute_token_delta, log_inflection_point,
    # compile_natural_language, validate_sandbox) inherited from
    # ExecutorIntegrationMixin — see executor_integration.py


# Backward-compatible import — ExecutorFactory moved to executor_factory.py
from cohezion.compound.executor_factory import ExecutorFactory  # noqa: F401
