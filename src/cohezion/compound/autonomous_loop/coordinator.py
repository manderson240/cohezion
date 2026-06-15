"""Autonomous compound engineering loop — subprocess-based execution.

Each loop iteration is a fresh Claude Code subprocess, so context never grows
within a single process. The coordinator manages budget (wall-clock + token),
checkpoint/resume, and sprint tracking.

Architecture:
  LoopCoordinator → TaskGenerator → ImprovementExecutor → Claude Code subprocess
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from .executor import ImprovementExecutor


logger = logging.getLogger(__name__)

# ── Data types ────────────────────────────────────────────────────────────────


@dataclass
class LoopTask:
    """One unit of autonomous improvement work."""

    id: str
    description: str
    priority: int  # 0 = highest
    category: str  # "test_fix", "lint_fix", "type_fix", "refactor", "feature"
    verification: str  # pytest command or other verification step
    estimated_tokens: int  # rough token budget for this task
    status: str = "pending"  # pending | running | done | failed | skipped
    result: str = ""  # outcome summary
    duration_seconds: float = 0.0
    tokens_used: int = 0


@dataclass
class SprintResult:
    """Outcome of one sprint (15-min window)."""

    sprint_number: int
    tasks_completed: int
    tasks_failed: int
    tasks_skipped: int
    tokens_used: int
    wall_clock_seconds: float
    checkpoint_path: str = ""


@dataclass
class LoopCheckpoint:
    """Persisted state for checkpoint/resume."""

    started_at: str
    last_updated: str
    total_sprints: int
    tasks_completed: int
    tasks_failed: int
    tasks_total: int
    tokens_used: int
    wall_clock_seconds: float
    current_task_id: str = ""
    backlog: list[dict] = field(default_factory=list)
    sprint_results: list[dict] = field(default_factory=list)


@dataclass
class LoopConfig:
    """Configuration for the autonomous loop."""

    # Budget
    max_wall_clock_hours: float = 3.0
    max_tokens: int = 1_000_000  # per-iteration cap, not global
    sprint_duration_seconds: int = 900  # 15 minutes

    # Execution
    claude_model: str = "sonnet"
    claude_max_tokens: int = 16384
    checkpoint_interval_seconds: int = 900  # save state every 15 min

    # Paths
    worktree_path: str = "/home/mike-anderson/dev/cohezion"
    checkpoint_path: str = "/tmp/cohezion-autonomous-loop/checkpoint.json"
    backlog_path: str = "/tmp/cohezion-autonomous-loop/backlog.json"
    results_path: str = "/tmp/cohezion-autonomous-loop/results.json"

    # Behavior
    parallel_tasks: int = 1  # sequential by default (subprocess-based)
    fail_fast: bool = False  # stop on first failure
    resume_from_checkpoint: bool = True


# ── LoopCoordinator ──────────────────────────────────────────────────────────


class LoopCoordinator:
    """Master orchestrator for the autonomous compound engineering loop.

    Manages:
    - Wall-clock and token budget tracking
    - Sprint lifecycle (15-min windows)
    - Checkpoint/resume via JSON persistence
    - Task dispatch to ImprovementExecutor
    - Result aggregation and final reporting
    """

    def __init__(self, config: LoopConfig | None = None):
        self.config = config or LoopConfig()
        self._start_time: float = 0.0
        self._last_checkpoint: float = 0.0
        self._sprint_number: int = 0
        self._tasks_completed: int = 0
        self._tasks_failed: int = 0
        self._tasks_skipped: int = 0
        self._total_tokens: int = 0
        self._backlog: list[LoopTask] = []
        self._sprint_results: list[SprintResult] = []
        self._current_task: LoopTask | None = None
        self._results: list[dict] = []

        # Ensure directories exist
        Path(self.config.checkpoint_path).parent.mkdir(parents=True, exist_ok=True)

    @property
    def elapsed_seconds(self) -> float:
        if not self._start_time:
            return 0.0
        return time.time() - self._start_time

    @property
    def elapsed_hours(self) -> float:
        return self.elapsed_seconds / 3600.0

    @property
    def budget_remaining(self) -> dict[str, float]:
        """Return remaining budget as fractions (0.0-1.0)."""
        wall_fraction = 1.0 - (self.elapsed_hours / self.config.max_wall_clock_hours)
        token_fraction = 1.0 - (self._total_tokens / self.config.max_tokens)
        return {
            "wall_clock": max(0.0, min(1.0, wall_fraction)),
            "tokens": max(0.0, min(1.0, token_fraction)),
        }

    @property
    def budget_exhausted(self) -> bool:
        bw = self.budget_remaining
        return bw["wall_clock"] <= 0.0 or bw["tokens"] <= 0.0

    def start(self) -> None:
        """Initialize the loop — load checkpoint if resuming, or create fresh state."""
        self._start_time = time.time()
        self._last_checkpoint = self._start_time

        # Try to resume from checkpoint
        if self.config.resume_from_checkpoint:
            checkpoint = self._load_checkpoint()
            if checkpoint:
                logger.info("Resuming from checkpoint: %s", checkpoint.checkpoint_path)
                self._sprint_number = checkpoint.total_sprints
                self._tasks_completed = checkpoint.tasks_completed
                self._tasks_failed = checkpoint.tasks_failed
                self._total_tokens = checkpoint.tokens_used
                self._backlog = [LoopTask(**t) for t in checkpoint.backlog]
                self._sprint_results = [SprintResult(**s) for s in checkpoint.sprint_results]
                self._last_checkpoint = time.time()  # reset checkpoint timer
                return

        logger.info("Starting fresh autonomous loop")

    def run(self, executor: ImprovementExecutor) -> LoopReport:
        """Main loop: run until budget exhausted.

        Each sprint:
        1. Check budget
        2. Pick next pending task (highest priority)
        3. Dispatch to executor
        4. Record results
        5. Checkpoint if needed
        """
        self.start()
        executor.start(self.config.worktree_path)

        while not self._budget_exhausted:
            # Checkpoint if needed
            self._maybe_checkpoint()

            # Pick next task
            task = self._pick_next_task()
            if task is None:
                logger.info("No more tasks to process — loop complete")
                break

            self._current_task = task
            self._run_task(task, executor)

            # Check budget after each task
            if self.config.fail_fast and self._tasks_failed > 0:
                logger.warning("Fail-fast triggered, stopping loop")
                break

        # Final checkpoint and report
        self._save_checkpoint()
        executor.stop()
        return self._build_report()

    def _pick_next_task(self) -> LoopTask | None:
        """Pick highest-priority pending task."""
        pending = sorted(
            [t for t in self._backlog if t.status == "pending"],
            key=lambda t: t.priority,
        )
        if not pending:
            return None
        return pending[0]

    def _run_task(self, task: LoopTask, executor: ImprovementExecutor) -> None:
        """Execute one task through the improvement pipeline."""
        logger.info("Running task %s (%s, priority=%d)", task.id, task.category, task.priority)
        task.status = "running"
        task_start = time.time()

        try:
            result = executor.execute_task(task, self.config.worktree_path)
            task.status = "done" if result["success"] else "failed"
            task.result = result.get("summary", "")
            task.tokens_used = result.get("tokens_used", 0)
            task.duration_seconds = time.time() - task_start

            if result["success"]:
                self._tasks_completed += 1
            else:
                self._tasks_failed += 1

            self._total_tokens += task.tokens_used
            self._results.append(
                {
                    "task_id": task.id,
                    "status": task.status,
                    "result": task.result,
                    "tokens": task.tokens_used,
                    "duration": task.duration_seconds,
                }
            )

        except Exception as exc:
            task.status = "failed"
            task.result = str(exc)
            task.duration_seconds = time.time() - task_start
            self._tasks_failed += 1
            logger.error("Task %s crashed: %s", task.id, exc)

    def _maybe_checkpoint(self) -> None:
        """Save checkpoint if enough time has passed."""
        if time.time() - self._last_checkpoint >= self.config.checkpoint_interval_seconds:
            self._save_checkpoint()

    def _save_checkpoint(self) -> None:
        """Persist loop state to disk."""
        checkpoint = LoopCheckpoint(
            started_at=datetime.fromisoformat(datetime.fromtimestamp(self._start_time).isoformat()),
            last_updated=datetime.now().isoformat(),
            total_sprints=self._sprint_number,
            tasks_completed=self._tasks_completed,
            tasks_failed=self._tasks_failed,
            tasks_total=len(self._backlog),
            tokens_used=self._total_tokens,
            wall_clock_seconds=self.elapsed_seconds,
            current_task_id=self._current_task.id if self._current_task else "",
            backlog=[asdict(t) for t in self._backlog],
            sprint_results=[asdict(s) for s in self._sprint_results],
        )
        Path(self.config.checkpoint_path).write_text(json.dumps(asdict(checkpoint), indent=2))
        self._last_checkpoint = time.time()
        logger.debug("Checkpoint saved at %.1fs elapsed", self.elapsed_seconds)

    def _load_checkpoint(self) -> LoopCheckpoint | None:
        """Load checkpoint from disk if it exists."""
        path = Path(self.config.checkpoint_path)
        if not path.exists():
            return None
        try:
            data = json.loads(path.read_text())
            return LoopCheckpoint(**data)
        except (json.JSONDecodeError, KeyError, TypeError):
            logger.warning("Corrupt checkpoint, starting fresh")
            return None

    def _build_report(self) -> LoopReport:
        """Build final loop report."""
        return LoopReport(
            started_at=datetime.fromtimestamp(self._start_time).isoformat(),
            elapsed_hours=self.elapsed_hours,
            total_sprints=self._sprint_number,
            tasks_completed=self._tasks_completed,
            tasks_failed=self._tasks_failed,
            tasks_skipped=self._tasks_skipped,
            tasks_total=len(self._backlog),
            tokens_used=self._total_tokens,
            budget_remaining=self.budget_remaining,
            results=self._results,
        )


@dataclass
class LoopReport:
    """Final report after loop completion."""

    started_at: str
    elapsed_hours: float
    total_sprints: int
    tasks_completed: int
    tasks_failed: int
    tasks_skipped: int
    tasks_total: int
    tokens_used: int
    budget_remaining: dict[str, float]
    results: list[dict]

    @property
    def success_rate(self) -> float:
        done = self.tasks_completed + self.tasks_failed
        if done == 0:
            return 0.0
        return self.tasks_completed / done

    def summary(self) -> str:
        lines = [
            "### Autonomous Loop Report",
            "",
            f"**Duration:** {self.elapsed_hours:.1f}h | **Tasks:** {self.tasks_completed}/{self.tasks_total} completed, {self.tasks_failed} failed",
            f"**Success rate:** {self.success_rate:.0%} | **Tokens used:** {self.tokens_used:,}",
            "",
            "| Metric | Value |",
            "|--------|-------|",
            f"| Wall-clock budget | {self.budget_remaining['wall_clock']:.0%} remaining |",
            f"| Token budget | {self.budget_remaining['tokens']:.0%} remaining |",
            f"| Sprint count | {self.total_sprints} |",
            "|",
        ]
        if self.results:
            lines.append("#### Task Results")
            lines.append("")
            lines.append("| Task | Status | Tokens | Duration |")
            lines.append("|------|--------|--------|----------|")
            for r in self.results[-20:]:  # last 20
                lines.append(
                    f"| {r['task_id']} | {r['status']} | {r['tokens']:,} | {r['duration']:.0f}s |"
                )
        return "\n".join(lines)
