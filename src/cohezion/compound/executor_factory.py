"""Factory for creating CompoundExecutor instances.

Extracted from executor.py (Session 87) to keep files under 500 lines.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from cohezion.compound.executor import CompoundExecutor


if TYPE_CHECKING:
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
        memory_service: Any | None = None,
        enable_memory: bool = False,
        enable_daily_researcher: bool = True,
    ) -> CompoundExecutor:
        """Create a new compound executor.

        When token_client is provided, attempts to use TokenEfficientCompoundExecutor
        for automatic API prompt caching (40-60% token savings).

        memory_service / enable_memory wire in CohezionMemory (mem0 + SurrealDB): when
        enable_memory=True the executor remembers each successful turn so executions
        compound into the project's memory. Opt-in (default off) so arbitrary callers
        don't pay the synchronous mem0.add tax; best-effort and self-disabling when the
        memory extra is absent or local nodes are offline.

        enable_daily_researcher (WS2C, default True): when True, the executor
        schedules the four-lane daily researcher (model_scout, harness_paper,
        datamesh_synthesis, verify_evolve) once at startup. The researcher
        runs in a background task with the fleet_lock:modelload held for
        the whole run. The flag is OFF by default in tests (where the
        background task would race the test), but the production default
        is ON per the WS2 plan decision.
        """
        # Auto-create RetrospectionEngine if not provided (closes middle loop)
        if retrospection_engine is None:
            try:
                from cohezion.core.compound.retrospection import RetrospectionEngine

                retrospection_engine = RetrospectionEngine()
                logger.debug("ExecutorFactory: auto-created RetrospectionEngine (middle loop)")
            except ImportError:
                logger.debug("RetrospectionEngine not available")

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

        # WS2C: schedule the daily researcher when the flag is on. This is
        # best-effort — a failure to start the researcher (e.g. the
        # researcher module isn't installed, or preflight fails) does
        # NOT block executor creation. The researcher runs in a fire-
        # and-forget background task.
        if enable_daily_researcher:
            try:
                import asyncio

                from cohezion.researcher.daily_researcher import DailyResearcher

                # The executor is created synchronously; the researcher
                # needs an event loop. We schedule the first run for the
                # next event loop iteration. Subsequent runs are the
                # 04:00 cron's job (see crontab.example).
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    loop.create_task(DailyResearcher().run_dry_run())
                logger.info("ExecutorFactory: daily researcher enabled (dry-run at startup)")
            except Exception as e:
                logger.debug("Daily researcher wiring failed (non-blocking): %s", e)

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
            memory_service=memory_service,
            enable_memory=enable_memory,
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
        memory_service: Any | None = None,
        enable_memory: bool = False,
        enable_daily_researcher: bool = True,
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
                memory_service=memory_service,
                enable_memory=enable_memory,
                enable_daily_researcher=enable_daily_researcher,
            )
        return ExecutorFactory._instance

    @staticmethod
    def reset_singleton() -> None:
        """Reset singleton for testing."""
        ExecutorFactory._instance = None
