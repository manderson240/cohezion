"""Execution orchestrator: runs TeamOrchestrator plans with dependency tracking.

Takes a :class:`TeamPlan` from :class:`TeamOrchestrator`, topologically sorts
tasks by dependency, runs independent tasks in parallel, and aggregates
results into an :class:`ExecutionReport`.
"""

from __future__ import annotations

import asyncio
import logging
import time
import uuid
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from cohezion.core.instruction_expander import InstructionExpander
from cohezion.core.plan_executor import ExecutionResult, PlanExecutor


if TYPE_CHECKING:
    from cohezion.swarm.team_orchestrator import TaskSpec, TeamPlan


logger = logging.getLogger(__name__)


@dataclass
class TaskResult:
    """Result of executing a single task from a team plan.

    Attributes
    ----------
    task_id : str
        Identifier matching the :class:`TaskSpec`.
    subject : str
        Human-readable task title.
    status : str
        One of ``"completed"``, ``"failed"``, ``"skipped"``.
    execution : ExecutionResult | None
        Detailed plan execution result if the task ran.
    error : str | None
        Error message if the task failed.
    duration_ms : float
        Wall-clock time in milliseconds.
    """

    task_id: str
    subject: str
    status: str = "completed"
    execution: ExecutionResult | None = None
    error: str | None = None
    duration_ms: float = 0.0


@dataclass
class ExecutionReport:
    """Aggregated report from executing an entire team plan.

    Attributes
    ----------
    report_id : str
        Unique identifier for this execution run.
    plan_name : str
        Name of the executed team plan.
    intent : str
        Original intent string.
    task_results : list[TaskResult]
        Per-task results in execution order.
    total_tokens : int
        Sum of tokens across all tasks.
    total_duration_ms : float
        Total wall-clock time.
    status : str
        Overall status: ``"completed"``, ``"partial"``, ``"failed"``.
    """

    report_id: str = ""
    plan_name: str = ""
    intent: str = ""
    task_results: list[TaskResult] = field(default_factory=list)
    total_tokens: int = 0
    total_duration_ms: float = 0.0
    status: str = "completed"

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a plain dictionary."""
        return {
            "report_id": self.report_id,
            "plan_name": self.plan_name,
            "intent": self.intent,
            "status": self.status,
            "total_tokens": self.total_tokens,
            "total_duration_ms": round(self.total_duration_ms, 2),
            "tasks": [
                {
                    "task_id": tr.task_id,
                    "subject": tr.subject,
                    "status": tr.status,
                    "error": tr.error,
                    "duration_ms": round(tr.duration_ms, 2),
                    "tokens": tr.execution.total_tokens if tr.execution else 0,
                }
                for tr in self.task_results
            ],
        }


def _topological_sort(tasks: list[TaskSpec]) -> list[list[TaskSpec]]:
    """Group tasks into waves respecting ``blocked_by`` dependencies.

    Returns
    -------
    list[list[TaskSpec]]
        Each inner list contains tasks that can run in parallel.
    """
    task_map = {t.id: t for t in tasks}
    completed: set[str] = set()
    waves: list[list[TaskSpec]] = []
    remaining = set(task_map.keys())

    while remaining:
        # Find tasks whose dependencies are all satisfied
        ready = [
            tid for tid in remaining if all(dep in completed for dep in task_map[tid].blocked_by)
        ]
        if not ready:
            # Break cycle: force remaining tasks into one wave
            logger.warning(
                "Dependency cycle detected, forcing %d remaining tasks",
                len(remaining),
            )
            ready = list(remaining)

        waves.append([task_map[tid] for tid in sorted(ready)])
        completed.update(ready)
        remaining -= set(ready)

    return waves


class ExecutionOrchestrator:
    """Execute a :class:`TeamPlan` with dependency tracking and parallelism.

    Parameters
    ----------
    token_client : TokenClient | None
        Optional LLM client for plan execution.
    compound_executor : TeamCompoundExecutor | None
        If provided, delegates task execution to the compound layer with
        per-operation model routing. Falls back to direct PlanExecutor
        when ``None``.
    """

    def __init__(
        self,
        token_client: Any | None = None,
        compound_executor: Any | None = None,
    ) -> None:
        self._token_client = token_client
        self._compound_executor = compound_executor
        self._expander = InstructionExpander()
        self._active_reports: dict[str, ExecutionReport] = {}

    async def execute(self, plan: TeamPlan) -> ExecutionReport:
        """Execute all tasks in *plan*, respecting dependencies.

        Independent tasks within the same wave run in parallel.

        Parameters
        ----------
        plan : TeamPlan
            The team plan to execute.

        Returns
        -------
        ExecutionReport
            Aggregated execution report.
        """
        report_id = f"exec_{uuid.uuid4().hex[:8]}"
        report = ExecutionReport(
            report_id=report_id,
            plan_name=plan.name,
            intent=plan.intent,
        )
        self._active_reports[report_id] = report

        t0 = time.monotonic()
        waves = _topological_sort(plan.tasks)

        logger.info(
            "Executing plan %s: %d tasks in %d waves",
            plan.name,
            len(plan.tasks),
            len(waves),
        )

        for wave_idx, wave in enumerate(waves):
            logger.info(
                "Wave %d: %d tasks (%s)",
                wave_idx + 1,
                len(wave),
                ", ".join(t.id for t in wave),
            )
            results = await asyncio.gather(
                *[self._execute_task(task) for task in wave],
                return_exceptions=True,
            )
            for task, result in zip(wave, results, strict=True):
                if isinstance(result, Exception):
                    tr = TaskResult(
                        task_id=task.id,
                        subject=task.subject,
                        status="failed",
                        error=str(result),
                    )
                else:
                    tr = result
                report.task_results.append(tr)

        elapsed = (time.monotonic() - t0) * 1000.0
        report.total_duration_ms = elapsed
        report.total_tokens = sum(
            tr.execution.total_tokens for tr in report.task_results if tr.execution
        )

        # Determine overall status
        statuses = {tr.status for tr in report.task_results}
        if not statuses or statuses == {"completed"}:
            report.status = "completed"
        elif "completed" in statuses:
            report.status = "partial"
        else:
            report.status = "failed"

        logger.info(
            "Plan %s %s: %d tasks, %d tokens, %.0f ms",
            plan.name,
            report.status,
            len(report.task_results),
            report.total_tokens,
            elapsed,
        )

        return report

    async def _execute_task(self, task: TaskSpec) -> TaskResult:
        """Execute a single task.

        When a :class:`TeamCompoundExecutor` is configured, delegates to
        it for per-operation model routing. Otherwise falls back to the
        original TemplateEngine + PlanExecutor path.
        """
        if self._compound_executor is not None:
            return await self._execute_task_compound(task)
        return await self._execute_task_direct(task)

    async def _execute_task_compound(self, task: TaskSpec) -> TaskResult:
        """Execute via TeamCompoundExecutor (per-operation model routing)."""
        t0 = time.monotonic()
        try:
            result = await self._compound_executor.execute_task(task)
            elapsed_ms = (time.monotonic() - t0) * 1000.0

            # Build an ExecutionResult from the compound result
            exec_result = ExecutionResult(
                skill_name=result.get("skill_name", "direct"),
                final_output=result.get("output", ""),
                total_tokens=result.get("tokens", 0),
                total_duration_ms=round(elapsed_ms, 2),
            )

            return TaskResult(
                task_id=task.id,
                subject=task.subject,
                status=result.get("status", "completed"),
                execution=exec_result,
                error=result.get("error"),
                duration_ms=elapsed_ms,
            )
        except Exception as exc:
            elapsed_ms = (time.monotonic() - t0) * 1000.0
            logger.exception("Compound execution failed for task %s", task.id)
            return TaskResult(
                task_id=task.id,
                subject=task.subject,
                status="failed",
                error=str(exc),
                duration_ms=elapsed_ms,
            )

    async def _execute_task_direct(self, task: TaskSpec) -> TaskResult:
        """Execute via direct TemplateEngine + PlanExecutor (original path)."""
        t0 = time.monotonic()

        try:
            from cohezion.core.template_engine import TemplateEngine

            engine = TemplateEngine()
            engine.parse_all()

            spec = None
            for tag in task.tags:
                spec = engine.get_spec_by_name(tag)
                if spec is not None:
                    break

            if spec is None:
                for skill_spec in engine._cache.values():
                    if any(
                        kw.lower() in task.subject.lower() for kw in skill_spec.name.split("_")[:3]
                    ):
                        spec = skill_spec
                        break

            if spec is not None:
                plan = self._expander.expand(spec)
                executor = PlanExecutor(token_client=self._token_client)
                exec_result = await executor.execute(plan, task.description)
            else:
                exec_result = ExecutionResult(
                    skill_name="direct",
                    final_output=f"Executed: {task.subject}",
                    total_tokens=0,
                    total_duration_ms=0.0,
                )

            elapsed_ms = (time.monotonic() - t0) * 1000.0
            return TaskResult(
                task_id=task.id,
                subject=task.subject,
                status="completed",
                execution=exec_result,
                duration_ms=elapsed_ms,
            )

        except Exception as exc:
            elapsed_ms = (time.monotonic() - t0) * 1000.0
            logger.exception("Task %s failed", task.id)
            return TaskResult(
                task_id=task.id,
                subject=task.subject,
                status="failed",
                error=str(exc),
                duration_ms=elapsed_ms,
            )

    def get_report(self, report_id: str) -> ExecutionReport | None:
        """Retrieve a cached execution report by ID."""
        return self._active_reports.get(report_id)
