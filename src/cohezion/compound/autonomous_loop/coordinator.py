"""LoopCoordinator — compound improvement loop with local/cloud routing."""

from __future__ import annotations

import contextlib
import time
from dataclasses import dataclass, field
from typing import Any


@dataclass
class LoopConfig:
    use_local_inference: bool = True
    local_base_url: str = "http://localhost:13305"
    worktree_path: str = "/tmp/worktree"
    checkpoint_path: str = "/tmp/checkpoint.json"
    backlog_path: str = "/tmp/backlog.json"
    results_path: str = "/tmp/results.json"
    max_tokens: int = 1_000_000
    max_wall_clock_hours: float = 8.0
    sprint_duration_seconds: float = 300.0
    cloud_escalation_threshold: int = 3
    min_free_ram_gb: float = 8.0
    resume_from_checkpoint: bool = False
    fail_fast: bool = False


@dataclass
class LoopTask:
    id: str
    description: str
    category: str
    priority: int
    verification: str
    estimated_tokens: int


@dataclass
class SprintResult:
    local_tokens: int = 0
    cloud_tokens: int = 0
    tasks_done: int = 0
    tasks_failed: int = 0

    @property
    def tokens_used(self) -> int:
        return self.local_tokens + self.cloud_tokens


@dataclass
class RunReport:
    tasks_completed: int = 0
    tasks_failed: int = 0
    results: list[dict[str, Any]] = field(default_factory=list)
    sprint_results: list[SprintResult] = field(default_factory=list)


class LoopCoordinator:
    def __init__(self, config: LoopConfig) -> None:
        self.config = config
        self._backlog: list[LoopTask] = []
        self._sprint_results: list[SprintResult] = []

    def run(self, executor: Any = None) -> RunReport:
        from cohezion.compound.autonomous_loop.executor import ImprovementExecutor
        from cohezion.compound.autonomous_loop.local_executor import LocalImprovementExecutor

        report = RunReport()
        fail_counts: dict[str, int] = {}
        category_stats: dict[str, dict[str, int]] = {}

        local_exec = None
        cloud_exec = executor

        if self.config.use_local_inference:
            local_exec = LocalImprovementExecutor(self.config.local_base_url)
            local_exec.start(self.config.worktree_path)
        else:
            cloud_exec = cloud_exec or ImprovementExecutor(self.config)
            cloud_exec.start(self.config.worktree_path)

        sprint_start = time.monotonic()
        sprint = SprintResult()

        try:
            for task in list(self._backlog):
                total_tokens = sum(r.get("tokens", 0) for r in report.results)
                if total_tokens >= self.config.max_tokens:
                    break

                task_fail_count = fail_counts.get(task.id, 0)
                use_cloud = task_fail_count >= self.config.cloud_escalation_threshold

                route_to_cloud = use_cloud or local_exec is None
                if route_to_cloud and cloud_exec is not None:
                    if not cloud_exec._started:
                        cloud_exec.start(self.config.worktree_path)
                    result = cloud_exec.execute_task(task, self.config.worktree_path)
                    is_cloud = True
                    tokens = result.get("tokens_used", 0)
                    sprint.cloud_tokens += tokens
                elif local_exec is not None:
                    result = local_exec.execute_task(task, self.config.worktree_path)
                    is_cloud = False
                    tokens = result.get("tokens_used", 0)
                    sprint.local_tokens += tokens
                else:
                    continue

                success = result.get("success", False)
                if success:
                    fail_counts[task.id] = 0
                    report.tasks_completed += 1
                    sprint.tasks_done += 1
                else:
                    fail_counts[task.id] = task_fail_count + 1
                    report.tasks_failed += 1
                    sprint.tasks_failed += 1

                cat = task.category
                if cat not in category_stats:
                    category_stats[cat] = {"done": 0, "failed": 0}
                if success:
                    category_stats[cat]["done"] += 1
                else:
                    category_stats[cat]["failed"] += 1

                report.results.append({
                    "task_id": task.id,
                    "tokens": tokens,
                    "is_cloud": is_cloud,
                    "success": success,
                })

                elapsed = time.monotonic() - sprint_start
                if elapsed >= self.config.sprint_duration_seconds:
                    self._sprint_results.append(sprint)
                    if local_exec is not None and hasattr(local_exec, "_sweeper"):
                        with contextlib.suppress(Exception):
                            local_exec._sweeper.course_correct(
                                list(self._sprint_results), dict(category_stats)
                            )
                    sprint = SprintResult()
                    sprint_start = time.monotonic()

        finally:
            if local_exec is not None:
                local_exec.stop()
            if cloud_exec is not None and getattr(cloud_exec, "_started", False):
                cloud_exec.stop()

        if sprint.tokens_used > 0 or sprint.tasks_done > 0 or sprint.tasks_failed > 0:
            self._sprint_results.append(sprint)

        report.sprint_results = list(self._sprint_results)
        return report
