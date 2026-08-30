"""Factory for creating CompoundExecutor instances.

Extracted from executor.py (Session 87) to keep files under 500 lines.
"""

from __future__ import annotations

import atexit
import logging
from typing import Any

from cohezion.compound.executor import CompoundExecutor
from cohezion.core.mcp_client import MCPClient
from cohezion.security.guardrail_pipeline import GuardrailPipeline


logger = logging.getLogger(__name__)


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
        jepa_gate: Any | None = None,
        quality_evaluator: Any | None = None,
        token_ledger: Any | None = None,
        # I1: CompoundExecutor accepts inference_provider so local silicon serves execute_fn.
        # `make_executor` below sets kwargs["inference_provider"] and then calls create(), but
        # create() had no such parameter and no **kwargs — so the ONLY factory path that wires
        # the RetrospectionEngine raised TypeError and was effectively uncallable. Everything
        # migrated to compound/__init__.make_executor, which hand-duplicates the auto-wiring
        # and omitted retrospection, silently dropping REFLECT from the loop.
        inference_provider: Any | None = None,
        # Ring-4 (2026-08-02 reconcile merge): `make_executor` below defaults this to True so
        # production executors persist real cycles to the compound graph. Declared explicitly
        # because create() has no **kwargs — forwarding an undeclared kwarg raises TypeError,
        # the same defect the inference_provider comment above records. Defaults to False so
        # direct ExecutorFactory.create() callers (notably tests) keep their current behavior.
        enable_cycle_persistence: bool = False,
    ) -> CompoundExecutor:
        """Create a new compound executor.

        When token_client is provided, attempts to use TokenEfficientCompoundExecutor
        for automatic API prompt caching (40-60% token savings).
        """
        # W2: JourneyTracker cross-session identity lifecycle (GIC Identity, #138).
        # restore_identity() reloads agent_id + lifetime op counts from ~/.cohezion/journey_identity.json.
        # save_identity() is registered via atexit so the identity persists across process restarts.
        if journey_tracker is not None:
            try:
                journey_tracker.restore_identity()
                atexit.register(journey_tracker.save_identity)
                logger.debug(
                    "ExecutorFactory: restored JourneyTracker identity; "
                    "save_identity registered via atexit"
                )
            except Exception:
                logger.debug("JourneyTracker identity lifecycle wiring failed (non-blocking)")

        # Auto-create RetrospectionEngine if not provided (closes middle loop)
        # N5: wire inference_provider into RetrospectionEngine so local silicon is used
        if retrospection_engine is None:
            try:
                from cohezion.core.compound.retrospection import RetrospectionEngine

                retrospection_engine = RetrospectionEngine(inference_provider=None)
                logger.debug("ExecutorFactory: auto-created RetrospectionEngine (middle loop)")
            except ImportError:
                logger.debug("RetrospectionEngine not available")

        # CB5: auto-create DegradationDetector when not provided (closes routing feedback loop).
        # Without this, suggest_routing_tier() and check_degradation() are never called and
        # the JepaGate REROUTE signal has nowhere to land.
        if degradation_detector is None:
            try:
                from cohezion.compound.degradation_detector import DegradationDetector

                degradation_detector = DegradationDetector()
                logger.debug("ExecutorFactory: auto-created DegradationDetector (CB5)")
            except Exception:
                logger.debug("DegradationDetector auto-creation failed (non-blocking)")

        # CB7: auto-restore baseline history and register end_session() for clean shutdown.
        if degradation_detector is not None:
            try:
                degradation_detector.start_session()
                atexit.register(degradation_detector.end_session)
                logger.debug(
                    "ExecutorFactory: DegradationDetector start_session restored; "
                    "end_session registered via atexit (CB7)"
                )
            except Exception:
                logger.debug("DegradationDetector CB7 lifecycle wiring failed (non-blocking)")

        # CH5 (CompoundHealthOracle): auto-create and inject into skill_refiner so quality scores
        # from every execution flow into the streaming HIHO regime tracker automatically.  The
        # oracle is seeded with the same DegradationDetector (already auto-created above) so
        # regime-driven tier recommendations also see the metric-based tier suggestion.
        _health_oracle: Any = None
        try:
            from cohezion.compound.compound_health_oracle import (
                _DEFAULT_STATE_PATH,
                CompoundHealthOracle,
            )

            _health_oracle = CompoundHealthOracle(degradation_detector=degradation_detector)
            # HO3: auto-restore cross-session state (non-blocking)
            if _DEFAULT_STATE_PATH.exists():
                _health_oracle.restore_state(_DEFAULT_STATE_PATH)
                logger.debug("ExecutorFactory: restored CompoundHealthOracle state from disk")
            # Register auto-save on clean shutdown (mirrors CB7 DegradationDetector pattern)
            atexit.register(_health_oracle.save_state, _DEFAULT_STATE_PATH)
            logger.debug("ExecutorFactory: auto-created CompoundHealthOracle (CH5)")
        except Exception:
            logger.debug("CompoundHealthOracle auto-creation failed (non-blocking)")

        # If caller supplied a skill_refiner, don't replace it; inject oracle into the default.
        if skill_refiner is None and _health_oracle is not None:
            try:
                from pathlib import Path

                from cohezion.compound.skill_refiner import SkillRefiner, SkillRefinerFactory

                skill_refiner = SkillRefinerFactory.create(
                    degradation_detector=degradation_detector,
                    health_oracle=_health_oracle,
                )
                # SRS3: cross-session durable spine — restore loop state from disk, register
                # auto-save on clean shutdown (mirrors HO3 CompoundHealthOracle pattern).
                _sr_state_path = Path(SkillRefiner._DEFAULT_STATE_PATH)
                if _sr_state_path.exists():
                    skill_refiner.restore_state(_sr_state_path)
                    logger.debug("ExecutorFactory: restored SkillRefiner loop state from disk")
                atexit.register(skill_refiner.save_state, _sr_state_path)
                logger.debug(
                    "ExecutorFactory: auto-created SkillRefiner with CompoundHealthOracle wired; "
                    "SRS atexit save registered"
                )
            except Exception:
                logger.debug("SkillRefiner auto-creation with oracle failed (non-blocking)")

        # Wire DegradationDetector → CostAwareRouter feedback callback (closes routing loop)
        if degradation_detector is not None:
            try:
                from cohezion.swarm.cost_aware_router import CostAwareRouter

                router = CostAwareRouter()
                degradation_detector.set_routing_callback(router.apply_degradation_feedback)
                logger.debug(
                    "ExecutorFactory: wired DegradationDetector → CostAwareRouter callback"
                )
            except Exception:
                logger.debug("CostAwareRouter callback wiring failed (non-blocking)")

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
            jepa_gate=jepa_gate,
            quality_evaluator=quality_evaluator,
            token_ledger=token_ledger,
            inference_provider=inference_provider,
            enable_cycle_persistence=enable_cycle_persistence,
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
        jepa_gate: Any | None = None,
        quality_evaluator: Any | None = None,
        token_ledger: Any | None = None,
    ) -> CompoundExecutor:
        """Get or create singleton executor."""
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
                jepa_gate=jepa_gate,
                quality_evaluator=quality_evaluator,
                token_ledger=token_ledger,
            )
        return ExecutorFactory._instance

    @staticmethod
    def reset_singleton() -> None:
        """Reset singleton for testing."""
        ExecutorFactory._instance = None


def make_executor(mcp_client: MCPClient, **kwargs: Any) -> CompoundExecutor:
    """Convenience factory: creates a CompoundExecutor with Triune local-inference pre-wired.

    Uses AMD OmniRouter on :13305 (NPU→iGPU→CPU) as inference_provider when available.
    Falls back to cloud-only if lemonade is offline.
    """
    try:
        from cohezion.inference.triune_orchestrator import build_triune_omni_orchestrator

        exec_provider = build_triune_omni_orchestrator()
    except Exception:
        exec_provider = None

    # Wire the local inference provider into RetrospectionEngine (N5 harness invariant).
    # Only inject if the caller hasn't already supplied a retrospection_engine.
    if exec_provider is not None and "retrospection_engine" not in kwargs:
        try:
            from cohezion.core.compound.retrospection import RetrospectionEngine

            kwargs["retrospection_engine"] = RetrospectionEngine(inference_provider=exec_provider)
        except Exception:
            pass

    # W1 + JG2: JepaGate auto-injection. build_live_jepa_gate wires a LEMONADE-backed world model
    # (GAIA SDK, :13305) + k-step lookahead when local inference is reachable — planning-before-
    # acting delegated to local silicon — else falls back to a fail-open gate (world_model=None).
    if "jepa_gate" not in kwargs:
        try:
            from cohezion.compound.lemonade_world_model import build_live_jepa_gate

            kwargs["jepa_gate"] = build_live_jepa_gate()
        except Exception:
            try:
                from cohezion.compound.jepa_gate import JepaGate

                kwargs["jepa_gate"] = JepaGate(world_model=None)
            except Exception:
                pass

    # AQ5: auto-inject the output-quality evaluator. AutoDQA -> quality_eval.evaluate
    # is pure-heuristic (task_classifier documents "< 0.1ms, no model calls"; the
    # scorers are regex/AST only) and no peer_outputs are passed, so the semantic
    # agreement path never runs and no embedder traffic is generated.
    #
    # notify_on_reject=False: the executor already owns alerting via
    # DegradationDetector, and a Telegram message per terse answer would be noise.
    #
    # persist=False, MEASURED not assumed (2026-08-30): 0.04 ms/eval with
    # persistence off vs 2167 ms/eval with it on — AutoDQA._persist_result builds a
    # fresh SurrealClient per call and run_sync blocks on it. A 2.2 s write on every
    # execution is disqualifying for this path.
    #
    # Note the trap this closes: persistence used to look free because it was BROKEN
    # (an un-awaited coroutine, discarded — see AQ7). Fixing that bug made the cost
    # real. So `autodqa_results` still has no producer, and model/training_data.py's
    # read of it (score >= 0.45) is still reading an empty source. Giving it one
    # needs batched or off-thread persistence + a connection-reuse fix first; do not
    # "enable" it by flipping this flag.
    if "quality_evaluator" not in kwargs:
        try:
            from cohezion.compound.autodqa import AutoDQA

            kwargs["quality_evaluator"] = AutoDQA(persist=False, notify_on_reject=False)
            logger.debug("make_executor: auto-created AutoDQA quality evaluator (AQ5)")
        except Exception:
            logger.debug("AutoDQA auto-creation failed (non-blocking)")

    # Pass exec_provider as inference_provider so execute_task injects it into compatible
    # execute_fns (signature-aware, backward-compatible — closes CB dormancy gap).
    if exec_provider is not None and "inference_provider" not in kwargs:
        kwargs["inference_provider"] = exec_provider

    # TL3: Auto-inject TokenLedger for Quarter-on-a-String token accounting ($0 vs cloud audit).
    if "token_ledger" not in kwargs:
        try:
            from cohezion.compound.token_ledger import TokenLedger

            kwargs["token_ledger"] = TokenLedger()
            logger.debug("make_executor: auto-created TokenLedger (TL3)")
        except Exception:
            logger.debug("TokenLedger auto-creation failed (non-blocking)")

    # Ring-4: production executors persist real cycles to the compound graph. Ported here during
    # the 2026-08-02 reconcile merge: `compound/__init__.make_executor` used to be a hand-rolled
    # duplicate of this function and set this default itself; that duplicate is now an alias to
    # this function (test_reflect_wiring: "duplicated wiring diverges, that is the lesson"), so
    # the default has to live at the single surviving implementation or it is silently dropped.
    # Direct CompoundExecutor() construction stays off by default — test isolation, CB4 pattern.
    kwargs.setdefault("enable_cycle_persistence", True)

    return ExecutorFactory.create(mcp_client, **kwargs)
