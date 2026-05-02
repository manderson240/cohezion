"""Ouroboros Architecture (Recursive Self-Improvement).

Consumes engine operation exhaust (failures, inefficiencies, context walls)
to systematically rewrite internal execution PRDs and system prompts.
"""

from __future__ import annotations

import logging
from typing import Any

from pydantic import BaseModel


logger = logging.getLogger(__name__)


class ExecutionExhaust(BaseModel):
    """Data collected from a failed or inefficient execution."""

    task_id: str
    error_message: str | None
    coherence_drop: float
    token_usage: int
    diagnostics: dict[str, Any]


class OuroborosEngine:
    """The recursive self-improvement loop for the Cohezion intelligence pipeline."""

    def __init__(self, target_coherence: float = 0.5):
        self.target_coherence = target_coherence
        self.rewrite_history: list[dict[str, Any]] = []

    async def consume_exhaust(self, exhaust: ExecutionExhaust) -> bool:
        """Analyze failure exhaust and determine if a rewrite is needed."""
        logger.info(f"Ouroboros consuming exhaust for Task {exhaust.task_id}")

        # Heuristic for triggering a self-improvement cycle
        needs_rewrite = False
        if exhaust.error_message:
            logger.warning(f"Task failed with error: {exhaust.error_message}")
            needs_rewrite = True
        elif exhaust.coherence_drop > 0.3:
            logger.warning(f"Massive coherence drop detected: {exhaust.coherence_drop}")
            needs_rewrite = True

        if needs_rewrite:
            return await self._trigger_rewrite_cycle(exhaust)

        logger.debug("Exhaust within acceptable parameters. No rewrite needed.")
        return False

    async def _trigger_rewrite_cycle(self, exhaust: ExecutionExhaust) -> bool:
        """Generate a new prompt or system alignment rules based on the failure."""
        logger.info("Initiating recursive rewrite cycle to prevent future failure.")

        # Simulate an LLM call analyzing the failure and updating the prompt
        new_rule = f"Prevent failure class observed in {exhaust.task_id} by limiting context window sizes."
        rewrite_entry = {
            "source_task": exhaust.task_id,
            "new_rule": new_rule,
            "metrics": exhaust.diagnostics,
        }
        self.rewrite_history.append(rewrite_entry)

        logger.info(f"Ouroboros rewrite successful. New dynamic rule: {new_rule}")
        return True

    def get_latest_system_rules(self) -> list[str]:
        """Fetch the accumulated, self-improved system rules."""
        return [entry["new_rule"] for entry in self.rewrite_history]
