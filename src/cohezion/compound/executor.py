"""Compound executor with vault-integrated knowledge persistence.

Orchestrates execution lifecycle:
  1. Query vault for experience guidance (prior similar runs)
  2. Execute task with guidance
  3. Log execution trajectory, decisions, metrics to vault
  4. Extract reusable patterns for future runs
"""

import asyncio
import contextlib
import json
import logging
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from functools import cached_property
from pathlib import (
    Path,  # noqa: F401 — structural guard; used at 4 sites in vault-default resolution
)
from typing import TYPE_CHECKING, Any

from cohezion.compound.context_integration import (
    CompoundContextMixin,
    ContextCoherenceError,
    ContextLoadError,
)
from cohezion.compound.executor_helpers.guardrail_runner import (
    run_async_guardrail as _run_async_guardrail,
)
from cohezion.compound.executor_integration import ExecutorIntegrationMixin
from cohezion.compound.exp_persistence.vault import (
    ExecutionContext,
    VaultLogger,
)
from cohezion.compound.inflection_detector import AnomalyDetection, Severity
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

# Tier cost order (cheapest → most expensive) for routing-signal synthesis.
_TIER_ORDER = ("npu", "igpu", "cpu", "cloud")


def _resolve_tier(
    predicted: str | None,
    suggested: str | None,
    jepa_reroute: bool,
    oracle_tier: str | None = None,
) -> str | None:
    """Synthesize the GIC's routing signals into ONE tier that DRIVES cascade entry (H4 fix).

    Fuse the predictive signal (DifficultyEstimator.predict_tier — skill-specific), the reactive
    health signal (DegradationDetector.suggest_routing_tier), and the regime-driven oracle signal
    (CompoundHealthOracle.last_assessment.tier_recommendation — rolling FD regime, cross-session
    persistent) by MAX-CAPABILITY: capability/SLO is a hard floor, so health may only ESCALATE a
    predicted-hard task, never cheapen it. A JEPA REROUTE verdict (marginal coherence = the world
    model expects divergence) escalates ONE more step toward capability, never cheaper. oracle_tier
    (OC1-OC3) adds the HIHO/STUCK/CHAOTIC regime as a 4th routing signal with the same MAX-CAPABILITY
    semantics — a STUCK regime (FD < 1.3, over-exploiting) raises the floor toward iGPU/CPU without
    overriding an already-confident higher prediction. Returns None when no valid signal is present.
    """
    candidates = [t for t in (predicted, suggested, oracle_tier) if t in _TIER_ORDER]
    base = max(candidates, key=_TIER_ORDER.index) if candidates else None
    if jepa_reroute and base is not None:
        return _TIER_ORDER[min(len(_TIER_ORDER) - 1, _TIER_ORDER.index(base) + 1)]
    return base


_TIER_NAME_TO_INDEX = {"npu": 0, "igpu": 1, "cpu": 2, "cloud": 3}


def _call_execute_fn(execute_fn, guidance, predicted_tier):
    """Call execute_fn, binding the difficulty prediction to the cascade ENTRY (O9) when execute_fn
    accepts a ``min_tier_index`` kwarg — a hard task skips the cheap tiers it would only fail-and-
    escalate through. Conservative + miscalibration-safe (cascade routers are usually miscalibrated):
    only a CONFIDENT high prediction skips; "unknown"/"npu"/None → 0 (cheap-first default). On local
    $0 silicon a mis-skip costs only latency, and the cascade still escalates from the entry tier.
    Backward-compatible: a 1-arg execute_fn (no min_tier_index) is always called with just guidance.
    """
    import inspect

    idx = _TIER_NAME_TO_INDEX.get(predicted_tier or "", 0)
    if idx > 0:
        try:
            if "min_tier_index" in inspect.signature(execute_fn).parameters:
                return execute_fn(guidance, min_tier_index=idx)
        except (TypeError, ValueError):
            pass
    return execute_fn(guidance)


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
    compound_score: float = 0.0


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

    # MGPO: fire batch refinement every N skill executions
    MGPO_BATCH_SIZE: int = 10

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
        rubric_middleware: Any | None = None,
        inference_provider: Any | None = None,
        jepa_gate: Any | None = None,
        memory_service: Any | None = None,
        enable_memory: bool = False,
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
        self._inference_provider = inference_provider
        self._jepa_gate = jepa_gate
        self._memory_service = memory_service
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

        # MGPO: accumulator of recent skill names for boundary-first batch refinement
        self._recent_skill_names: list[str] = []

        # Rubric middleware: structured output gate before MGPO accumulation
        self._rubric_middleware = rubric_middleware

        # Geometric Latent Bridge for topological reasoning
        try:
            from cohezion.flume.geometric_bridge import GeometricLatentBridge

            self.geometric_bridge = GeometricLatentBridge()
            logger.debug("GeometricLatentBridge initialized")
        except ImportError:
            self.geometric_bridge = None
            logger.debug("GeometricLatentBridge not available")

        # SkillStateEncoder: FLUME 256D encoding for post-execution skill state
        self._skill_state_encoder = None
        try:
            from cohezion.flume.skill_state_encoder import SkillStateEncoder

            self._skill_state_encoder = SkillStateEncoder()
        except Exception:
            pass

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
    def memory_service(self) -> Any:
        """Backward-compat: returns the memory service (or None if not configured)."""
        return self._memory_service

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

    def _flume_encode_skill_state(
        self,
        skill_name: str,
        *,
        mgpo_weight: float,
        success_rate: float,
        verdict: object | None = None,
        **kwargs: Any,
    ) -> Any:
        """Encode skill state into a 256D FLUME vector (fail-open).

        Routes to encode_rubric_verdict when ``verdict`` is provided,
        otherwise to encode_skill.  Returns None when the encoder is
        absent or any exception occurs.
        """
        if self._skill_state_encoder is None:
            return None
        try:
            if verdict is not None:
                return self._skill_state_encoder.encode_rubric_verdict(
                    skill_name,
                    verdict,
                    mgpo_weight=mgpo_weight,
                    success_rate=success_rate,
                    **kwargs,
                )
            return self._skill_state_encoder.encode_skill(
                skill_name,
                mgpo_weight=mgpo_weight,
                success_rate=success_rate,
                **kwargs,
            )
        except Exception:
            return None

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

            self._skill_refiner = SkillRefinerFactory.create(
                self.mcp_client, degradation_detector=self._degradation_detector
            )
            logger.debug("Initialized default skill refiner")

        return self._skill_refiner

    def _batch_mgpo_refine(self, top_k: int | None = None) -> None:
        """MGPO: refine boundary skills (highest weight) from the recent-skill accumulator.

        Deduplicates candidates, sorts by MGPO weight (boundary-first), calls
        skill_refiner.refine() for the top K, then drains the accumulator.
        """
        if not self._recent_skill_names:
            return
        refiner = self.skill_refiner
        if refiner is None:
            self._recent_skill_names = []
            return
        try:
            candidates = list(dict.fromkeys(self._recent_skill_names))
            prioritized = refiner.prioritized_skills(candidates)
            k = top_k if top_k is not None else len(prioritized)
            for skill in prioritized[:k]:
                try:
                    refiner.refine(
                        skill_name=skill,
                        operation_type="mgpo_batch",
                        execution_result={},
                    )
                except Exception:
                    pass
        except Exception:
            pass
        finally:
            self._recent_skill_names = []

    def _check_mgpo_batch(self) -> None:
        """Fire _batch_mgpo_refine() when accumulator reaches MGPO_BATCH_SIZE."""
        if len(self._recent_skill_names) >= self.MGPO_BATCH_SIZE:
            self._batch_mgpo_refine()

    def _evaluate_rubric(self, task_output: str, task_context: str = "") -> bool:
        """Gate task output through rubric middleware. Returns True when no middleware."""
        if self._rubric_middleware is None:
            return True
        try:
            verdict = self._rubric_middleware.evaluate(task_output, task_context)
            return bool(verdict.passed)
        except Exception:
            return True  # fail-open

    def _rubric_gated_accumulate(self, skill_name: str, task_output: str = "") -> None:
        """Append skill_name to MGPO accumulator only when rubric passes (or absent)."""
        if self._evaluate_rubric(task_output, task_context=skill_name):
            self._recent_skill_names.append(skill_name)

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

    @cached_property
    def _bioelectric_network(self) -> Any:
        """Single BioelectricNetwork instance reused across executions.

        Z6 perf: previously instantiated per execution (~1.2ms each). Cached
        once on first use; .v_mem is overwritten per call so state is fresh.
        """
        from cohezion.physics.bioelectric_model import BioelectricNetwork

        net = BioelectricNetwork(n_cells=8)
        net.set_uniform_conductance(0.3)
        return net

    @cached_property
    def _natural_capital_valuation(self) -> Any:
        """Single NaturalCapitalValuation instance reused across executions.

        Z6 perf: previously instantiated per execution. Stateless; safe to share.
        """
        from cohezion.physics.natural_capital import NaturalCapitalValuation

        return NaturalCapitalValuation()

    def _try_template_match(self, task_description: str) -> dict[str, Any] | None:
        """Check cache for a template match before LLM execution.

        Thin delegator — implementation lives in
        ``executor_helpers.template_matcher.try_template_match``.
        """
        from cohezion.compound.executor_helpers.template_matcher import try_template_match

        return try_template_match(task_description)

    def get_experience_guidance(
        self,
        task_description: str,
        project: str = "cohezion",
        operation_type: str = "generate",
        skill_name: str = "",
    ) -> dict[str, Any]:
        """Fetch experience guidance from vault before execution.

        Thin delegator — implementation lives in
        ``executor_helpers.vault_integration.fetch_experience_guidance``.

        Args:
            task_description: Description of the task to execute
            project: Project name for scoped search
            operation_type: Type of operation (for trajectory search)
            skill_name: Skill whose PRIME-file learned refinements should
                be merged in (empty string skips the refinement read)

        Returns:
            Dict with relevant_context (decisions, experiments, patterns)
            plus trajectory-based recommendations, warnings, and confidence
        """
        from cohezion.compound.executor_helpers.vault_integration import (
            fetch_experience_guidance,
        )

        return fetch_experience_guidance(
            self.logger,
            task_description,
            project=project,
            operation_type=operation_type,
            skill_name=skill_name,
        )

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
        except (ImportError, AttributeError, RuntimeError, ValueError, KeyError) as e:
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
            except (
                ContextCoherenceError,
                ContextLoadError,
                OSError,
                RuntimeError,
                AttributeError,
                ValueError,
            ) as e:
                logger.debug("Failed to auto-load context: %s", e)

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
            except (AttributeError, RuntimeError, ValueError, TypeError) as e:
                logger.debug("Universe bridge start failed (non-blocking): %s", e)

        # Step 0.5: Classify task and apply context policy (adaptive breadth/depth)
        _task_profile = None
        _context_budget = None
        try:
            _context_budget = self.apply_policy(task_description, operation_type)
            if self._context_policy is not None and _context_budget is not None:
                _task_profile = self._context_policy.classify_task(task_description, operation_type)
        except Exception as e:
            logger.debug("Context policy classification failed (non-blocking): %s", e)

        # Step 1: Get experience guidance (enhanced with trajectory search)
        guidance = self.get_experience_guidance(
            task_description, project, operation_type, skill_name=skill_name
        )
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
            except (AttributeError, RuntimeError, ValueError, KeyError, TypeError) as e:
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

        # Step 3.5: JEPA pre-execution coherence gate (GIC Decision-making, JW1)
        # Predicts outcome quality before committing to the 11-step pipeline.
        _jepa_verdict = None
        if self._jepa_gate is not None:
            try:
                _jepa_verdict = self._jepa_gate.check(task_description)
                metrics["jepa_verdict"] = _jepa_verdict.value
                metrics["jepa_coherence"] = self._jepa_gate.last_coherence
                if _jepa_verdict.value == "skip":
                    logger.warning(
                        "JEPA gate SKIP: predicted coherence %.3f below threshold — skipping execution",
                        self._jepa_gate.last_coherence,
                    )
                    return ExecutionResult(
                        success=False,
                        output="Execution skipped: JEPA gate predicted insufficient coherence",
                        metrics={
                            "jepa_verdict": "skip",
                            "jepa_coherence": self._jepa_gate.last_coherence,
                        },
                        duration_seconds=time.time() - start_seconds,
                        vault_experiment_path=experiment_path,
                    )
                if _jepa_verdict.value == "reroute":
                    logger.info(
                        "JEPA gate REROUTE: predicted coherence %.3f — marking for tier consideration",
                        self._jepa_gate.last_coherence,
                    )
            except Exception as exc:
                logger.debug("JEPA gate check failed (non-blocking): %s", exc)

        # Step 3.6: Pre-execution tier routing hints (W3/W4 wiring completeness).
        # Collected before execute_fn so the hints survive even if execute_fn raises.
        # They are merged INTO the metrics dict returned by execute_fn after the call.
        _tier_hints: dict[str, str] = {}
        # (a) W3: DegradationDetector.suggest_routing_tier() — reactive, health-based tier hint.
        if self._degradation_detector is not None:
            try:
                _tier_hints["suggested_tier"] = self._degradation_detector.suggest_routing_tier()
            except Exception:
                pass
        # (b) W4: DifficultyEstimator.predict_tier() — predictive, skill-specific tier hint.
        # Use the lazy `skill_refiner` PROPERTY (not the raw `_skill_refiner` attr): the attr is None
        # until the property first fires at the post-execute_fn refinement step, so reading it here
        # skipped the predicted_tier hint — and thus the O9 cascade-entry routing — on the FIRST
        # execute_task. The property builds the refiner on demand, so the hint is available from call #1.
        _refiner = self.skill_refiner
        if _refiner is not None:
            _estimator = getattr(_refiner, "_difficulty_estimator", None)
            if _estimator is not None:
                try:
                    _tier_hints["predicted_tier"] = _estimator.predict_tier(
                        skill_name, operation_type
                    )
                except Exception:
                    pass
        # (d) OC1-OC3: CompoundHealthOracle.last_assessment.tier_recommendation — regime-driven,
        # rolling Higuchi-FD window (cross-session persistent). Reflects the PREVIOUS executions'
        # quality texture (HIHO/STUCK/CHAOTIC). STUCK (FD < 1.3) escalates the recommended tier
        # to break out of over-exploitation; CHAOTIC forces cpu (maximum reasoning depth, slow down).
        # Reading _last_assessment (not calling assess()) is intentional: assess() is called POST-
        # execution inside SkillRefiner._generate_learning_signal, so the current execution uses the
        # oracle's accumulated knowledge from all previous executions as a forward-looking hint.
        if _refiner is not None:
            _oracle = getattr(_refiner, "_health_oracle", None)
            if _oracle is not None:
                try:
                    _last = getattr(_oracle, "_last_assessment", None)
                    if _last is not None:
                        _tier_hints["oracle_tier"] = _last.tier_recommendation
                except Exception:
                    pass
        # (c) Synthesize ONE coherent tier recommendation from the predictive + reactive + regime
        # signals, escalating on a JEPA REROUTE (marginal coherence). H4 fix: this fused value now
        # DRIVES cascade entry (below) instead of only being logged — so health degradation, the
        # REROUTE verdict, and the HIHO regime assessment are actionable, not metric-only.
        _recommended = _resolve_tier(
            _tier_hints.get("predicted_tier"),
            _tier_hints.get("suggested_tier"),
            jepa_reroute=(_jepa_verdict is not None and _jepa_verdict.value == "reroute"),
            oracle_tier=_tier_hints.get("oracle_tier"),
        )
        if _recommended is not None:
            _tier_hints["recommended_tier"] = _recommended

        try:
            # O9 binding: enter the cascade at the FUSED recommendation (difficulty + health + REROUTE,
            # max-capability) when present, else the raw difficulty prediction. Signature-aware,
            # backward-compatible, conservative — see _call_execute_fn.
            output, metrics = _call_execute_fn(
                execute_fn, guidance, _recommended or _tier_hints.get("predicted_tier")
            )
            success = True
            logger.info("Task completed successfully")
        except Exception as e:
            # User-supplied execute_fn can raise anything; record failure metric and continue.
            # SystemExit/KeyboardInterrupt/MemoryError still propagate (they don't inherit Exception).
            error_msg = str(e)
            output = f"Error: {error_msg}"
            metrics = {"error": error_msg, "error_type": type(e).__name__}
            logger.error("Task failed: %s", error_msg, exc_info=True)
        # Merge W3/W4 tier hints — execute_fn may return a new dict so we must merge after the call.
        if _tier_hints:
            metrics.update(_tier_hints)

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
        except (OSError, RuntimeError, ValueError, AttributeError) as e:
            logger.debug("Execution trace logging failed (non-blocking): %s", e, exc_info=True)

        # Step 5: Detect anomalies (non-blocking)
        decision_paths = []
        try:
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
                except (OSError, RuntimeError, ValueError, AttributeError) as e:
                    logger.debug("Failed to log inflection point (non-blocking): %s", e)
        except (ImportError, AttributeError, RuntimeError, ValueError, KeyError) as e:
            logger.debug("Anomaly detection failed (non-blocking): %s", e, exc_info=True)

        # Step 5.5: Analyze request-execution alignment (if enabled)
        if self._enable_alignment_analysis and self.alignment_analyzer and parsed_request:
            try:
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
                logger.warning(
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

        # Step 5.85: V-Model DRR gate (non-blocking).
        # DRR checks file artifacts (skill PRIME .md + matching test .py). Only fire when both
        # can be resolved to real paths — passing runtime strings (skill_name, task_description)
        # caused false CRITICAL findings on every task execution (2 criticals per run).
        if self._drr_generator:
            try:
                from pathlib import Path as _Path

                from cohezion.compound.design_review_report import GateLevel

                _skills_dir = _Path(__file__).parent.parent / "skills"
                _sn = (skill_name or "").upper().replace("-", "_").replace(" ", "_")
                _skill_file = _skills_dir / f"{_sn}_PRIME.md"
                _test_file = (
                    _Path(__file__).parent.parent.parent.parent
                    / "tests"
                    / "compound"
                    / f"test_{(skill_name or '').replace('-', '_')}.py"
                )
                if _skill_file.exists() and _test_file.exists():
                    drr = self._drr_generator.generate(
                        gate=GateLevel.IMPLEMENTATION,
                        session_id=self._drr_session_id or "unknown",
                        left_artifact=str(_skill_file),
                        right_artifact=str(_test_file),
                    )
                    metrics["drr_gate"] = drr.gate.value
                    metrics["drr_passed"] = drr.passed
                    metrics["drr_findings"] = len(drr.findings)
                    if not drr.passed:
                        logger.warning("DRR-%s FAILED: %s", drr.gate.value, drr.summary)
                else:
                    metrics["drr_gate"] = GateLevel.IMPLEMENTATION.value
                    metrics["drr_passed"] = None
                    metrics["drr_findings"] = 0
            except Exception:
                logger.debug("DRR gate check failed (non-blocking)", exc_info=True)

        # Step 5.9: Natural capital valuation (non-blocking)
        # Maps HIHO proximity to habitat quality via InVEST-inspired model
        try:
            import numpy as np

            ncv = self._natural_capital_valuation
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
        except Exception:
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
            except Exception:
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
                    code_example=f"Result metrics: {json.dumps(metrics, indent=2, default=repr)}",
                    domain="compound-engineering",
                )
                if pattern_path:
                    decision_paths.append(pattern_path)
            except (OSError, RuntimeError, ValueError, AttributeError, KeyError, TypeError) as e:
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
            except (AttributeError, RuntimeError, ValueError, KeyError, TypeError) as e:
                logger.debug("Retrospection failed (non-blocking): %s", e, exc_info=True)

        # Step 7.2a: Mine failure signatures (Self-Harness §3.1) — non-blocking
        # CycleRetrospectionEngine accumulates per-cycle summaries as a lazy
        # sidecar; mine_failure_signatures clusters them into (terminal_cause,
        # causal_status, agent_mechanism) triples usable by SkillRefiner.
        if not success:
            try:
                from cohezion.compound.retrospection_summary import (
                    CycleMetrics,
                    CycleRetrospectionEngine,
                    mine_failure_signatures,
                )

                if not hasattr(self, "_cycle_retro_engine"):
                    self._cycle_retro_engine = CycleRetrospectionEngine()
                _cycle_metrics = CycleMetrics(
                    coherence_start=float(
                        metrics.get("coherence_start", metrics.get("coherence", 0.5))
                    ),
                    coherence_end=float(
                        metrics.get("coherence_end", metrics.get("coherence", 0.5))
                    ),
                    tokens_used=int(metrics.get("tokens_used", 0)),
                    skill_name=skill_name,
                    phase=operation_type,
                    success=False,
                    anomalies=metrics.get("anomalies", []),
                )
                _cycle_id = f"{skill_name}_{int(time.time())}"
                self._cycle_retro_engine.summarize(_cycle_id, _cycle_metrics)
                _sigs = mine_failure_signatures(self._cycle_retro_engine.summaries)
                if _sigs:
                    metrics["failure_signatures"] = [
                        {
                            "terminal_cause": s.terminal_cause,
                            "causal_status": s.causal_status,
                            "agent_mechanism": s.agent_mechanism,
                            "skill_name": s.skill_name,
                            "cycle_id": s.cycle_id,
                        }
                        for s in _sigs
                    ]
                    logger.debug("Mined %d failure signature(s) for %s", len(_sigs), skill_name)
            except Exception as _sig_err:
                logger.debug("Failure signature mining skipped: %s", _sig_err)

        # Step 7: Refine skills based on execution results (non-blocking)
        # Gated by retrospection AND DRR: only refine when both pass.
        # The DRR gate is only authoritative when a real V-Model session is
        # active (i.e., ``_drr_session_id`` has been set). When no session is
        # configured the DRR runs against placeholder artifact paths that
        # never exist, producing structural critical findings unrelated to
        # the skill outcome — those should not block refinement.
        drr_passed = metrics.get("drr_passed", True)  # Default True if DRR not run
        drr_authoritative = bool(self._drr_session_id)
        if drr_authoritative and not drr_passed:
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
                    failure_signatures=metrics.get("failure_signatures"),
                )

                if refined_path:
                    logger.info("Skill refined: %s", refined_path)
                    decision_paths.append(refined_path)

            except Exception as e:
                logger.warning("Skill refinement failed (non-blocking): %s", e, exc_info=True)

        # Step 7.3a: MGPO batch accumulation (wires _rubric_gated_accumulate + _check_mgpo_batch)
        if success:
            try:
                self._rubric_gated_accumulate(skill_name, output if output else "")
                self._check_mgpo_batch()
            except Exception as e:
                logger.debug("MGPO batch accumulation failed (non-blocking): %s", e)

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
            except (AttributeError, RuntimeError, ValueError, TypeError) as e:
                logger.warning("Skill health tracking failed (non-blocking): %s", e)

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
                # Fold JEPA pre-execution coherence into degradation metrics (JW1 routing feedback).
                if _jepa_verdict is not None and self._jepa_gate is not None:
                    degradation_metrics["jepa_coherence"] = self._jepa_gate.last_coherence
                    # Step 7.5b: AdaJEPA feedback — recalibrate world-model baseline from
                    # actual execution quality (2606.32026). Fail-open: any exception is
                    # suppressed so calibration never blocks the execution pipeline.
                    _wm = getattr(self._jepa_gate, "_world_model", None)
                    if _wm is not None and hasattr(_wm, "observe"):
                        _actual_quality = float(
                            metrics.get("quality_score", metrics.get("coherence", 0.5))
                        )
                        try:
                            _wm.observe(
                                task_description,
                                self._jepa_gate.last_coherence,
                                _actual_quality,
                            )
                        except Exception:  # never block on calibration
                            pass
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
                        except (OSError, RuntimeError, ValueError, AttributeError) as e:
                            logger.debug(
                                "Failed to log degradation alert (non-blocking): %s",
                                e,
                            )
            except (AttributeError, RuntimeError, ValueError, KeyError, TypeError) as e:
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

            bio_net = self._bioelectric_network
            # Map coherence [0,1] to membrane potentials [-1,1]
            bio_net.v_mem = np.full(8, coherence_val * 2 - 1)
            bio_net.simulate(n_steps=10, dt=0.01)
            bio_coherence = bio_net.coherence()
            metrics["bioelectric_coherence"] = float(bio_coherence)
            percolation = bio_net.percolation_analysis()
            metrics["bioelectric_percolated"] = percolation.is_percolated
        except Exception:
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
            except (AttributeError, RuntimeError, ValueError, TypeError) as e:
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
            except (AttributeError, RuntimeError, ValueError, TypeError) as e:
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
                    except (
                        TimeoutError,
                        AttributeError,
                        RuntimeError,
                        OSError,
                        ConnectionError,
                    ) as e:
                        logger.debug("Journey persistence failed (non-blocking): %s", e)
            except (AttributeError, RuntimeError, ValueError, KeyError, TypeError) as e:
                logger.debug("Journey tracking failed (non-blocking): %s", e)

        # Step 9.1: Persist universe snapshot (L183)
        # Record a universe state snapshot to SurrealDB for world model training
        try:
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
            except (AttributeError, RuntimeError, ValueError, TypeError) as e:
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
            except (AttributeError, RuntimeError, ValueError, TypeError) as e:
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
        except Exception:
            pass  # Non-blocking: ouroboros bridge may not be available

        # Step 10.6: Mycelium learning capture (non-blocking)
        # Auto-capture execution results into MyceliumRegistry for skill synthesis
        try:
            if success:
                from cohezion.learning.mycelium_registry import JournalEntry, MyceliumRegistry

                if not hasattr(self, "_mycelium_registry"):
                    # Shared singleton so synthesized skills are visible to the
                    # mycelium API reader (closes the recursion loop).
                    self._mycelium_registry = MyceliumRegistry.get_instance()
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
                    except (AttributeError, RuntimeError, ValueError, OSError) as e:
                        logger.debug("Mycelium audit failed (non-blocking): %s", e)
                logger.debug("Mycelium: captured execution as pattern entry")
        except Exception:
            pass  # Non-blocking: mycelium may not be available

        # Step 10.8: Unified learning-loop feedback (replaces/advances Step 10.6).
        # Emit a WITNESS_MARK, feed MyceliumRegistry, and drive Ouroboros on failure.
        try:
            from cohezion.learning.recorder import get_learning_recorder

            get_learning_recorder().record_executor_outcome(
                task_description=task_description,
                skill_name=skill_name,
                success=success,
                output=output,
                metrics=metrics,
                duration_seconds=duration_seconds,
                project=project,
            )
        except Exception:
            logger.debug("Learning recorder feedback failed (non-blocking)", exc_info=True)

        # Step 10.7: Persist prompt artifact (L183)
        # Record prompt/response pair to SurrealDB for retrospective analysis
        try:
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
        if (
            self._context_policy is not None
            and _task_profile is not None
            and _context_budget is not None
        ):
            try:
                self._context_policy.record_outcome(
                    profile=_task_profile,
                    budget=_context_budget,
                    execution_success=success,
                    coherence_final=metrics.get("coherence", 0.5),
                )
            except Exception as e:
                logger.debug("Context policy outcome recording failed (non-blocking): %s", e)

        # Compute compound_score = coherence × hiho_stability × skill_factor
        # hiho_stability = 1 - 2|coherence - 0.5| (max at 0.5, 0 at extremes)
        # skill_factor = max(0, 1 + skill_gain) (non-negative, penalizes regression)
        _coherence = float(metrics.get("coherence", 0.5))
        _skill_gain = float(metrics.get("skill_gain", 0.0))
        if retrospection_context is not None:
            _skill_gain = float(retrospection_context.get("compound_score", _skill_gain))
        _hiho_stability = max(0.0, 1.0 - 2.0 * abs(_coherence - 0.5))
        _skill_factor = max(0.0, 1.0 + _skill_gain)
        compound_score = _coherence * _hiho_stability * _skill_factor

        return ExecutionResult(
            success=success,
            output=output,
            metrics=metrics,
            duration_seconds=duration_seconds,
            vault_experiment_path=experiment_path,
            vault_decision_paths=decision_paths,
            token_metrics=token_metrics,
            compound_score=compound_score,
        )

    def _recompute_tier_at_compaction(
        self, skill_name: str, operation_type: str, active_tier: str
    ) -> str | None:
        """Fusion free-reroute (cognition.com/blog/devin-fusion): at a context-COMPACTION boundary —
        where the cache/context is rebuilt anyway, so a tier switch is effectively FREE — re-evaluate
        routing on the CURRENT state (reactive DegradationDetector health + predictive
        DifficultyEstimator) and reroute ONLY if the recommendation now DIFFERS from the active tier.
        Returns the new tier (a free mid-task switch) or None (stay). No-op-safe if components absent.

        INTENTIONALLY CALLER-SUPPLIED (no internal automatic caller). This is an operator /
        long-horizon-driver hook: the candidate in-process compaction boundaries do NOT carry the
        routing context (skill_name, operation_type, active_tier) this method needs —
        `VectorPruningEngine.should_compact()` is a generic cycle-count trigger not owned by the
        executor, and `LongHorizonTask._perform_step` is a stub with no tier/skill context. Rather
        than fabricate a context-less caller, expose it publicly (see the
        `recompute_tier_at_compaction` alias below) so a driver that DOES hold routing context — a
        long-horizon task loop or an operator-controlled compaction handler — can invoke it at its
        own boundary. Exercised by tests/compound/test_tier_resolution.py::TestCompactionReroute.
        """
        suggested = None
        if self._degradation_detector is not None:
            try:
                suggested = self._degradation_detector.suggest_routing_tier()
            except Exception:
                pass
        predicted = None
        estimator = (
            getattr(self._skill_refiner, "_difficulty_estimator", None)
            if self._skill_refiner
            else None
        )
        if estimator is not None:
            try:
                predicted = estimator.predict_tier(skill_name, operation_type)
            except Exception:
                pass
        # Adequate tier = the MORE CAPABLE of the difficulty prediction and the health suggestion
        # (either signal escalating wins — never under-route a hard task at the boundary). Unlike
        # RS1's cost-biased _resolve_tier (cheaper-of-two), the reroute ensures capability.
        candidates = [t for t in (predicted, suggested) if t in _TIER_ORDER]
        if not candidates:
            return None
        recommended = max(candidates, key=_TIER_ORDER.index)
        if recommended != active_tier:
            logger.info(
                "compaction reroute: %s -> %s (free switch at compaction boundary)",
                active_tier,
                recommended,
            )
            return recommended
        return None

    # Public alias for the caller-supplied compaction-boundary reroute hook (see the docstring on
    # _recompute_tier_at_compaction). The private name is retained for the existing test/invariant.
    def recompute_tier_at_compaction(
        self, skill_name: str, operation_type: str, active_tier: str
    ) -> str | None:
        """Public entry point for an external long-horizon/operator driver to request a free
        tier reroute at its own compaction boundary. Delegates to _recompute_tier_at_compaction."""
        return self._recompute_tier_at_compaction(skill_name, operation_type, active_tier)

    def start_session(self, max_cache_entries: int = 256) -> dict[str, Any]:
        """Start a compound session: warm-start autocontext and cache.

        Args:
            max_cache_entries: Maximum cache entries to warm (unused placeholder)

        Returns:
            Session summary dict
        """
        manifest_path = self.init_autocontext()
        summary: dict[str, Any] = {
            "autocontext_initialized": bool(manifest_path),
            "manifest_path": str(manifest_path) if manifest_path else None,
        }
        # Warm cache (best-effort, non-blocking)
        try:
            from cohezion.compound.cache_persistence import WarmCacheLoader
            from cohezion.swarm.compound_client import get_compound_client

            client = get_compound_client()
            loader = WarmCacheLoader()
            cache_loaded = loader.warm_client(client, max_cache_entries)
            summary["cache_entries_loaded"] = cache_loaded
        except Exception:
            logger.debug("Cache warm failed (non-critical)")
            summary["cache_entries_loaded"] = 0
        logger.info("Compound session started")
        return summary

    def end_session(self) -> dict[str, Any]:
        """End compound session: archive outcome and persist state.

        Returns:
            Session summary dict
        """
        # Gather outcome from context state if available
        outcome: dict[str, Any] = {}
        with contextlib.suppress(Exception):
            outcome = self.get_context_state()
        archived_path = self.archive_session(outcome=outcome)
        summary: dict[str, Any] = {
            "session_archived": bool(archived_path),
            "archive_path": str(archived_path) if archived_path else None,
        }
        # Persist cache (best-effort, non-blocking)
        try:
            from cohezion.compound.cache_persistence import CachePersistence
            from cohezion.swarm.compound_client import get_compound_client

            client = get_compound_client()
            cp = CachePersistence()
            cache_saved = cp.save_cache(client._cache)
            summary["cache_entries_saved"] = cache_saved
        except Exception:
            logger.debug("Cache save failed (non-critical)")
            summary["cache_entries_saved"] = 0
        logger.info("Compound session ended")
        return summary

    # Integration methods (_compute_token_delta, log_inflection_point,
    # compile_natural_language, validate_sandbox) inherited from
    # ExecutorIntegrationMixin — see executor_integration.py


def __getattr__(name: str) -> object:
    """Lazy re-export for ExecutorFactory to avoid circular imports."""
    if name == "ExecutorFactory":
        from cohezion.compound.executor_factory import ExecutorFactory

        return ExecutorFactory
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
