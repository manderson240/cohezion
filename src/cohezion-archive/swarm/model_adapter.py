"""Adapter bridging SmartRouter to TokenEfficientClient's router interface.

SmartRouter uses TaskType enums and scores models based on capabilities.
TokenEfficientClient expects a router with ``select_optimal_model()``
returning an object with a ``.name`` attribute.  This adapter translates
between the two interfaces.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from cohezion.swarm.smart_router import SmartRouter, TaskType


logger = logging.getLogger(__name__)

# Map free-form task_type strings to SmartRouter TaskType enums
_TASK_TYPE_MAP: dict[str, TaskType] = {
    "general": TaskType.ANALYSIS,
    "analysis": TaskType.ANALYSIS,
    "synthesis": TaskType.SYNTHESIS,
    "creative": TaskType.CREATIVE,
    "coding": TaskType.CODING,
    "code": TaskType.CODING,
    "factual": TaskType.FACTUAL,
    "debate": TaskType.DEBATE,
    "summary": TaskType.SUMMARY,
}


@dataclass
class ModelSelection:
    """Minimal model selection result with a ``name`` attribute."""

    name: str


class SmartRouterAdapter:
    """Adapt :class:`SmartRouter` for use as ``TokenEfficientClient._router``.

    TokenEfficientClient calls::

        config = await self._router.select_optimal_model(
            {"task_type": task_type, "context_length": len(prompt)}
        )
        model_name = config.name

    This adapter translates that interface into SmartRouter's
    ``classify_task`` / ``route`` pipeline.

    Parameters
    ----------
    smart_router : SmartRouter
        The underlying router with model profiles and scoring.
    """

    def __init__(self, smart_router: SmartRouter) -> None:
        self._router = smart_router

    async def select_optimal_model(self, context: dict[str, Any]) -> ModelSelection:
        """Select the best model given a task context dict.

        Parameters
        ----------
        context : dict[str, Any]
            Must contain ``"task_type"`` (str) and optionally
            ``"context_length"`` (int).

        Returns
        -------
        ModelSelection
            Object with a ``.name`` attribute for the selected model.

        Raises
        ------
        RuntimeError
            If SmartRouter has no available models and no fallback.
        """
        task_type_str = context.get("task_type", "general")
        task_type = _TASK_TYPE_MAP.get(task_type_str, TaskType.ANALYSIS)

        # Ensure models are refreshed at least once
        if not self._router.available_models:
            try:
                await self._router.refresh_models()
            except Exception:
                logger.warning("SmartRouter refresh_models failed; using static fallback")

        decision = self._router.route(task_type)
        logger.debug(
            "SmartRouterAdapter: %s -> %s (confidence=%.2f)",
            task_type_str,
            decision.selected_model,
            decision.confidence,
        )
        return ModelSelection(name=decision.selected_model)
