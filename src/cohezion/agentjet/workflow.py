"""CohezionWorkflow: wraps CompoundExecutor as an AgentJet-compatible workflow.

AgentJet calls run(task) which executes via CompoundExecutor and returns the
output alongside a reward metadata dict containing phi_score, skill_name, and
coherence. The phi_score is derived from JourneyTracker trajectory analysis.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, TYPE_CHECKING

from cohezion.compound.journey_tracker import JourneyTracker

if TYPE_CHECKING:
    from cohezion.compound.executor import CompoundExecutor


logger = logging.getLogger(__name__)


class CohezionWorkflow:
    """Wraps CompoundExecutor as an AgentJet Workflow.

    AgentJet calls ``run(task)`` which delegates to CompoundExecutor and
    tracks the execution trajectory via JourneyTracker to produce a phi_score
    reward signal.

    Parameters
    ----------
    executor : CompoundExecutor
        Configured compound executor to delegate task execution to.
    tracker : JourneyTracker, optional
        Journey tracker for phi_score computation. A default instance is
        created if not provided.
    default_operation_type : str
        Default operation type used when task dict omits ``operation_type``.
        Must be one of: generate, analyze, search, transform, persist.
    """

    def __init__(
        self,
        executor: CompoundExecutor,
        tracker: JourneyTracker | None = None,
        default_operation_type: str = "generate",
    ) -> None:
        self._executor = executor
        self._tracker = tracker if tracker is not None else JourneyTracker()
        self._default_operation_type = default_operation_type

    async def run(self, task: dict[str, Any]) -> tuple[str, dict[str, Any]]:
        """Execute a task and return output with phi_score reward metadata.

        Parameters
        ----------
        task : dict
            Task specification. Expected keys:

            * ``description`` (str, required) — human-readable task description
            * ``skill_name`` (str) — skill to apply (default: ``"general"``)
            * ``operation_type`` (str) — operation type (default: ``"generate"``)
            * ``project`` (str) — vault project scope (default: ``"cohezion"``)
            * Any additional keys are forwarded as task context.

        Returns
        -------
        tuple[str, dict]
            ``(output, metadata)`` where metadata contains:

            * ``phi_score`` (float) — trajectory quality [0.0, 1.0]
            * ``skill_name`` (str) — skill used for execution
            * ``coherence`` (float) — execution coherence [0.0, 1.0]
            * ``success`` (bool) — whether execution succeeded
            * ``duration_seconds`` (float) — wall-clock execution time
        """
        description: str = task.get("description", "")
        skill_name: str = task.get("skill_name", "general")
        operation_type: str = task.get("operation_type", self._default_operation_type)
        project: str = task.get("project", "cohezion")

        if not description:
            logger.warning("CohezionWorkflow.run() called with empty task description")

        # Build a synchronous execute function that captures task context.
        # CompoundExecutor.execute_task is synchronous; it calls execute_fn
        # internally in a sync context.
        def _execute_fn() -> tuple[str, dict[str, Any]]:
            output_text = description  # Minimal fallback — executor enriches this.
            exec_metrics: dict[str, Any] = {"coherence": 0.5}
            return output_text, exec_metrics

        logger.info(
            "CohezionWorkflow.run: skill=%s operation=%s description=%r",
            skill_name,
            operation_type,
            description[:80],
        )

        # Execute via CompoundExecutor (synchronous call wrapped in async context)
        try:
            result = await asyncio.get_running_loop().run_in_executor(
                None,
                lambda: self._executor.execute_task(
                    task_description=description,
                    skill_name=skill_name,
                    operation_type=operation_type,
                    execute_fn=_execute_fn,
                    project=project,
                ),
            )
        except Exception as exc:
            logger.error("CohezionWorkflow execution failed: %s", exc, exc_info=True)
            return (
                f"[error] {exc}",
                {
                    "phi_score": 0.0,
                    "skill_name": skill_name,
                    "coherence": 0.0,
                    "success": False,
                    "duration_seconds": 0.0,
                },
            )

        # Track execution trajectory to compute phi_score
        try:
            trajectory_point = self._tracker.track_execution(
                execution_result=result,
                task_description=description,
                operation_type=operation_type,
            )
            phi_score: float = float(trajectory_point.metadata.get("phi_score", 0.0))
            coherence: float = float(trajectory_point.coherence)
        except Exception as exc:
            logger.warning("Journey tracking failed (non-blocking): %s", exc, exc_info=True)
            phi_score = float(result.metrics.get("coherence", 0.0))
            coherence = phi_score

        metadata: dict[str, Any] = {
            "phi_score": phi_score,
            "skill_name": skill_name,
            "coherence": coherence,
            "success": result.success,
            "duration_seconds": result.duration_seconds,
        }

        logger.debug(
            "CohezionWorkflow.run complete: phi=%.3f coherence=%.3f success=%s",
            phi_score,
            coherence,
            result.success,
        )

        return result.output, metadata
