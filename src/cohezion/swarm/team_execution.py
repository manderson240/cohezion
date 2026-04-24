"""Team-aware compound execution bridge.

Connects :class:`ExecutionOrchestrator` to :class:`CompoundExecutor` so that
team execution gets per-operation model routing, a shared
:class:`TemplateEngine`, and optional feedback loop integration.
"""

from __future__ import annotations

import logging
import time
from typing import TYPE_CHECKING, Any

from cohezion.swarm.team_metrics import TeamMetricsAggregator


if TYPE_CHECKING:
    from cohezion.swarm.team_orchestrator import TaskSpec


logger = logging.getLogger(__name__)


class TeamCompoundExecutor:
    """Execute team tasks through the compound engineering layer.

    Shares a single :class:`TemplateEngine` across all tasks (instead of
    creating a fresh one per task) and delegates LLM calls through
    :class:`CompoundExecutor` for per-operation model routing.

    Parameters
    ----------
    compound_executor : CompoundExecutor | None
        Pre-configured compound executor. Uses singleton if ``None``.
    auto_feedback : bool
        Whether to run a feedback cycle after each skill execution.
    """

    def __init__(
        self,
        compound_executor: Any | None = None,
        auto_feedback: bool = False,
    ) -> None:
        self._compound_executor = compound_executor
        self._auto_feedback = auto_feedback
        self._engine = None

    @property
    def compound_executor(self) -> Any:
        """Lazy-load the CompoundExecutor."""
        if self._compound_executor is None:
            from cohezion.compound.executor import get_executor

            self._compound_executor = get_executor()
        return self._compound_executor

    @property
    def engine(self) -> Any:
        """Shared TemplateEngine instance."""
        if self._engine is None:
            from cohezion.core.template_engine import TemplateEngine

            self._engine = TemplateEngine()
        return self._engine

    async def execute_task(self, task: TaskSpec) -> dict[str, Any]:
        """Execute a single task through the compound layer.

        Looks up a matching PRIME skill by tag or keyword, then delegates
        to :meth:`CompoundExecutor.execute_skill` for model-routed execution.

        Parameters
        ----------
        task : TaskSpec
            The task to execute.

        Returns
        -------
        dict[str, Any]
            Result dict with keys: skill_name, output, tokens, duration_ms,
            model, status.
        """
        t0 = time.monotonic()

        # Find matching skill
        skill_name = self._find_skill_for_task(task)

        if skill_name:
            try:
                result = await self.compound_executor.execute_skill(skill_name, task.description)
                elapsed_ms = (time.monotonic() - t0) * 1000.0

                # Optional feedback loop
                if self._auto_feedback:
                    await self._run_feedback(skill_name, task.description)

                return {
                    "skill_name": skill_name,
                    "output": result.final_output,
                    "tokens": result.total_tokens,
                    "duration_ms": round(elapsed_ms, 2),
                    "model": next(iter(result.model_usage), ""),
                    "status": "completed",
                    "steps": len(result.steps),
                }
            except Exception as exc:
                logger.exception("Compound execution failed for task %s", task.id)
                elapsed_ms = (time.monotonic() - t0) * 1000.0
                return {
                    "skill_name": skill_name,
                    "output": "",
                    "tokens": 0,
                    "duration_ms": round(elapsed_ms, 2),
                    "model": "",
                    "status": "failed",
                    "error": str(exc),
                    "steps": 0,
                }

        # No matching skill — fall back to simple execution
        elapsed_ms = (time.monotonic() - t0) * 1000.0
        return {
            "skill_name": "direct",
            "output": f"Executed: {task.subject}",
            "tokens": 0,
            "duration_ms": round(elapsed_ms, 2),
            "model": "",
            "status": "completed",
            "steps": 0,
        }

    def _find_skill_for_task(self, task: TaskSpec) -> str | None:
        """Find a PRIME skill matching the task by tags or keywords.

        Parameters
        ----------
        task : TaskSpec
            The task to match.

        Returns
        -------
        str | None
            Skill name if found, else ``None``.
        """
        # Try tags first
        for tag in task.tags:
            spec = self.engine.get_spec_by_name(tag)
            if spec is not None:
                return str(spec.name)

        # Keyword search against cached specs
        try:
            self.engine.parse_all()
        except Exception as e:
            logger.debug("Skill spec parsing failed: %s", e)

        for skill_spec in self.engine._cache.values():
            if any(kw.lower() in task.subject.lower() for kw in skill_spec.name.split("_")[:3]):
                return str(skill_spec.name)

        return None

    async def _run_feedback(self, skill_name: str, input_text: str) -> None:
        """Run a single feedback cycle for the executed skill."""
        try:
            from cohezion.compound.feedback_loop import CompoundFeedbackLoop

            loop = CompoundFeedbackLoop(
                executor=self.compound_executor,
                auto_regenerate=False,
            )
            await loop.run_cycle(skill_name, input_text)
        except Exception:
            logger.debug("Feedback cycle failed for %s (non-critical)", skill_name)

    def create_metrics_aggregator(self, plan_name: str) -> TeamMetricsAggregator:
        """Create a metrics aggregator for this execution.

        Parameters
        ----------
        plan_name : str
            Name of the plan being executed.

        Returns
        -------
        TeamMetricsAggregator
            Fresh aggregator instance.
        """
        return TeamMetricsAggregator(plan_name=plan_name)
