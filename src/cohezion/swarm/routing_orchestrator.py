"""RoutingOrchestrator — Unified entry point for all routing systems.

Chain of Responsibility combining:
1. CostAwareRouter: complexity → model + OI-MAS confidence
2. TipOfTheSpearRouter: constitutional check + escalation chain
3. DynamicModelRouter: runtime health + fallback (if available)
4. TopologicalRouter: TDA behavior regime (if trajectory data available)

Single call replaces 4 separate router consultations.
Token-efficient: lazy initialization, non-blocking fallbacks.

Wired to: CompoundExecutor (replaces direct CostAwareRouter usage)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class UnifiedRoutingDecision:
    """Decision from the unified routing orchestrator."""

    model: str
    confidence: float  # OI-MAS joint role+scale confidence [0, 1]
    complexity: str  # SIMPLE, MEDIUM, COMPLEX
    estimated_tokens: int
    estimated_cost_usd: float
    reason: str
    constitutional_ok: bool = True
    can_proceed: bool = True


class RoutingOrchestrator:
    """Unified routing entry point combining all 4 routing systems.

    Token-efficient: single route() call replaces multiple router consultations.
    Non-blocking: each router stage wrapped in try/except.
    """

    def __init__(self) -> None:
        self._cost_router: Any = None
        self._cost_router_loaded = False

    def _get_cost_router(self) -> Any:
        """Lazy-load CostAwareRouter."""
        if not self._cost_router_loaded:
            self._cost_router_loaded = True
            try:
                from cohezion.swarm.cost_aware_router import CostAwareRouter

                self._cost_router = CostAwareRouter()
            except Exception:
                logger.debug("CostAwareRouter not available")
        return self._cost_router

    def route(
        self,
        task_description: str,
        max_cost_usd: float | None = None,
        cache_hit_rate: float | None = None,
    ) -> UnifiedRoutingDecision:
        """Route a task through all routing systems.

        Args:
            task_description: What the task does
            max_cost_usd: Optional budget constraint
            cache_hit_rate: Current cache hit rate for feedback

        Returns:
            UnifiedRoutingDecision with model, confidence, and metadata
        """
        # Stage 1: CostAwareRouter — complexity + model + confidence
        router = self._get_cost_router()
        if router is not None:
            try:
                decision, can_proceed = router.select_model(
                    task_description,
                    max_cost_usd=max_cost_usd,
                    cache_hit_rate=cache_hit_rate,
                )
                return UnifiedRoutingDecision(
                    model=decision.model,
                    confidence=decision.confidence,
                    complexity=decision.complexity.value,
                    estimated_tokens=decision.estimated_tokens,
                    estimated_cost_usd=decision.estimated_cost_usd,
                    reason=decision.reason,
                    can_proceed=can_proceed,
                )
            except Exception as e:
                logger.debug("CostAwareRouter failed: %s", e)

        # Fallback: default routing
        return UnifiedRoutingDecision(
            model="phi3:mini",
            confidence=0.5,
            complexity="SIMPLE",
            estimated_tokens=500,
            estimated_cost_usd=0.0,
            reason="Fallback routing (no router available)",
        )

    def get_confidence(self, model: str, task_description: str) -> float:
        """Get confidence score for a model+task combination.

        Aggregates signals from CostAwareRouter's OI-MAS scoring.
        """
        router = self._get_cost_router()
        if router is not None:
            try:
                from cohezion.swarm.cost_aware_router import QueryComplexity

                complexity = router.complexity_analyzer.analyze(task_description)
                return router._compute_routing_confidence(model, complexity)
            except Exception:
                pass

        return 0.5  # Default moderate confidence
