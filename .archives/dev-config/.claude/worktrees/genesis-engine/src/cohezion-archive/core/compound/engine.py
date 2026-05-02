"""Compound Logic Engine — discovers reusable patterns across tasks.

Analyzes incoming queries against the capability registry to find existing
skills and hooks that can accelerate the current task (compound engineering).
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any


if TYPE_CHECKING:
    from cohezion.registry.capability_registry import CapabilityRegistry

logger = logging.getLogger(__name__)


class CompoundLogicEngine:
    """Discover and leverage existing capabilities for task compounding.

    Parameters
    ----------
    registry : CapabilityRegistry
        The capability registry to search for reusable patterns.
    """

    def __init__(self, registry: CapabilityRegistry | None = None) -> None:
        self._registry = registry

    def analyze_task_for_compounding(self, query: str) -> list[dict[str, Any]]:
        """Find existing capabilities that can accelerate the given task.

        Parameters
        ----------
        query : str
            The task description to analyze.

        Returns
        -------
        list[dict[str, Any]]
            List of compound patterns, each with 'name' and 'hooks' keys.
        """
        if not self._registry or not query:
            return []

        try:
            matches = self._registry.find(query, top_k=3)
            return [{"name": m.name, "hooks": getattr(m, "hooks", [])} for m in matches if m is not None]
        except Exception as e:
            logger.debug("Compound analysis failed: %s", e)
            return []
