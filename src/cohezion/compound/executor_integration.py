"""Integration methods for CompoundExecutor.

Extracted from executor.py (Session 87) to keep files under 500 lines.
Contains: NL compilation (vibe/), sandbox validation (vanguard/),
inflection point logging, and token delta computation.
"""

from __future__ import annotations

import logging
from typing import Any


logger = logging.getLogger(__name__)


class ExecutorIntegrationMixin:
    """Mixin providing integration methods for CompoundExecutor.

    These methods connect the executor to external modules (vibe/, vanguard/)
    and provide utility computations (token deltas, inflection logging).
    """

    def _compute_token_delta(
        self,
        metrics_before: dict[str, Any] | None,
        metrics_after: dict[str, Any],
    ) -> dict[str, Any]:
        """Compute token metric deltas (tokens used in this execution)."""
        if not metrics_before:
            return metrics_after

        delta: dict[str, Any] = {}

        if "total_tokens" in metrics_after and "total_tokens" in metrics_before:
            delta["tokens_used"] = metrics_after["total_tokens"] - metrics_before["total_tokens"]
        if "api_calls" in metrics_after and "api_calls" in metrics_before:
            delta["api_calls_made"] = metrics_after["api_calls"] - metrics_before["api_calls"]
        if "cache_hits" in metrics_after and "cache_hits" in metrics_before:
            delta["cache_hits"] = metrics_after["cache_hits"] - metrics_before["cache_hits"]
        if "cache_misses" in metrics_after and "cache_misses" in metrics_before:
            delta["cache_misses"] = metrics_after["cache_misses"] - metrics_before["cache_misses"]

        if "cache_hit_rate" in metrics_after:
            delta["cache_hit_rate"] = metrics_after["cache_hit_rate"]
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
        """Log a critical decision point (called by InflectionDetector)."""
        logger.info("Logging inflection point: %s", title)
        result: str = self.logger.log_decision_point(
            project=project,
            title=title,
            context=context,
            decision=decision,
            rationale=rationale,
        )
        return result

    def compile_natural_language(self, nl_text: str) -> Any:
        """Compile natural language to a WorkflowSpec via vibe/ orchestrator.

        Wires vibe/ NL->workflow compiler into the compound loop.
        """
        try:
            from cohezion.vibe.orchestrator import VibeOrchestrator

            orchestrator = VibeOrchestrator()
            import asyncio

            try:
                loop = asyncio.get_running_loop()
                import concurrent.futures

                with concurrent.futures.ThreadPoolExecutor() as pool:
                    spec = loop.run_in_executor(
                        pool, lambda: asyncio.run(orchestrator.vibe(nl_text, execute=False))
                    )
                return spec
            except RuntimeError:
                return asyncio.run(orchestrator.vibe(nl_text, execute=False))
        except ImportError:
            logger.debug("vibe/ module not available for NL compilation")
            return None
        except Exception:
            logger.debug("NL compilation failed (non-blocking)", exc_info=True)
            return None

    def validate_sandbox(self, task_description: str) -> bool:
        """Pre-execution sandbox validation via vanguard/ module."""
        try:
            from cohezion.vanguard.sandbox_validation import validate_sandbox_task

            return validate_sandbox_task(task_description)
        except ImportError:
            return True
        except Exception:
            logger.debug("Sandbox validation failed (non-blocking)", exc_info=True)
            return True
