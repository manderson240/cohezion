"""Task-based model selection registry for SwarmService.

Non-destructive remediation of the V-Model audit §10 finding: `services/swarm_service.py`
(and transitively `cli`) imported `cohezion.models.model_registry.ModelRegistry`, a class
that was *intended but never built* — so both modules were dark with
`ModuleNotFoundError: No module named 'cohezion.models.model_registry'`.

Rather than stub it (an always-None registry would be a fake gate, the hazard flagged in
audit §12.2), this WIRES the intended `get_best_for_task` behavior to the real
`CostAwareRouter` (cost/quality task→model routing). It is fail-soft: any unavailability
returns `None`, and callers (e.g. swarm_service) fall back to their default model.
"""
from __future__ import annotations

import logging


logger = logging.getLogger(__name__)


class ModelRegistry:
    """Selects the best model for a task, delegating to CostAwareRouter.

    The router is built lazily on first use so construction stays cheap (swarm_service builds
    a ModelRegistry eagerly). `get_best_for_task` returns a model-name string, or ``None`` when
    routing is unavailable so the caller can fall back to a default.
    """

    def __init__(self, router: object | None = None) -> None:
        # `None` → build a real CostAwareRouter lazily on first use.
        # A non-None value (real router or test fake) is used as-is.
        self._router = router
        self._router_tried = router is not None

    def _ensure_router(self) -> object | None:
        if not self._router_tried:
            self._router_tried = True
            try:
                from cohezion.swarm.cost_aware_router import CostAwareRouter

                self._router = CostAwareRouter()
            except Exception as exc:
                logger.debug("CostAwareRouter unavailable, ModelRegistry inert: %s", exc)
                self._router = None
        return self._router

    def get_best_for_task(
        self, task: str, budget: float | None = None, prefer_fast: bool = True
    ) -> str | None:
        """Return the best model name for ``task`` within ``budget``, or ``None`` to fall back.

        ``prefer_fast`` biases toward cheaper/faster models via the router's cache-aware path
        (a high cache_hit_rate downgrades query complexity), mapping cleanly onto the existing
        CostAwareRouter API without a new code path.
        """
        router = self._ensure_router()
        if router is None:
            return None
        try:
            decision, _ = router.select_model(  # type: ignore[attr-defined]
                query=task,
                max_cost_usd=budget,
                cache_hit_rate=0.95 if prefer_fast else None,
            )
            return getattr(decision, "model", None)
        except Exception as exc:
            logger.debug("ModelRegistry.get_best_for_task failed: %s", exc)
            return None
