"""Autonomous compound engineering loop — local-inference-first execution.

Each loop iteration uses LocalImprovementExecutor (Lemonade :13305) by default.
Claude Code subprocess is reserved for escalation after repeated local failures.
The coordinator manages budget (wall-clock + token), checkpoint/resume, and sprint tracking.

Architecture:
  LoopCoordinator → LocalImprovementExecutor (Lemonade) → escalate → ImprovementExecutor (Claude CLI)
"""

from __future__ import annotations

import json
import logging
import os
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any


if TYPE_CHECKING:
    from .executor import ImprovementExecutor
    from .local_executor import LocalImprovementExecutor


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
    # Multi-label categories (superset of category). Derived from category when not
    # supplied explicitly — allows callers to set e.g. ("test_fix", "type_fix") for
    # tasks that span both repair types so model selection finds the best intersection.
    categories: tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if not self.categories:
            self.categories = (self.category,)


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
    local_tokens: int = 0
    cloud_tokens: int = 0


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
    checkpoint_path: str = ""
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

    # Local inference (quarter-on-a-string) — defaults ON
    use_local_inference: bool = True
    local_model: str = "Qwen3.6-35B-A3B-MTP-GGUF"
    local_fallback_model: str = "Gemma-4-E4B-it-GGUF"
    # Resolved at instantiation time so LEMONADE_BASE_URL is honored per-process.
    local_base_url: str = field(
        default_factory=lambda: os.environ.get("LEMONADE_BASE_URL", "http://localhost:13305")
    )
    cloud_escalation_threshold: int = 2  # escalate after N consecutive local failures

    # Paths
    worktree_path: str = "/home/mike-anderson/dev/cohezion"
    checkpoint_path: str = "/tmp/cohezion-autonomous-loop/checkpoint.json"
    backlog_path: str = "/tmp/cohezion-autonomous-loop/backlog.json"
    results_path: str = "/tmp/cohezion-autonomous-loop/results.json"

    # Behavior
    parallel_tasks: int = 1  # sequential by default
    fail_fast: bool = False  # stop on first failure
    resume_from_checkpoint: bool = True
    min_free_ram_gb: float = 20.0  # refuse heavy inference below this threshold


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
                logger.info("Resuming from checkpoint: %s", self.config.checkpoint_path)
                self._sprint_number = checkpoint.total_sprints
                self._tasks_completed = checkpoint.tasks_completed
                self._tasks_failed = checkpoint.tasks_failed
                self._total_tokens = checkpoint.tokens_used
                self._backlog = [LoopTask(**t) for t in checkpoint.backlog]
                self._sprint_results = [SprintResult(**s) for s in checkpoint.sprint_results]
                self._last_checkpoint = time.time()  # reset checkpoint timer
                return

        logger.info("Starting fresh autonomous loop")

    @staticmethod
    def _check_ram_before_load(min_free_gb: float = 20.0) -> bool:
        """Return True if enough RAM is free for a heavy model inference call."""
        try:
            import psutil

            free_gb = psutil.virtual_memory().available / 1e9
            if free_gb < min_free_gb:
                logger.warning(
                    "Low RAM: %.1f GB free (need %.1f GB) — skipping heavy model inference",
                    free_gb,
                    min_free_gb,
                )
                return False
            return True
        except ImportError:
            return True  # psutil unavailable, proceed without guard

    def run(self, executor: Any | None = None) -> LoopReport:
        """Main loop: run until budget exhausted.

        Uses LocalImprovementExecutor (Lemonade) by default when use_local_inference=True.
        Escalates to Claude CLI executor after cloud_escalation_threshold consecutive local
        failures on the same task.

        Each iteration:
        1. RAM check (C2 — skip heavy tasks if RAM too low)
        2. Checkpoint if needed
        3. Pick next pending task
        4. Dispatch to local executor; on repeated failure → cloud escalation
        5. Record results
        """
        from .executor import ImprovementExecutor
        from .local_executor import LocalImprovementExecutor

        self.start()

        # Build executors
        if self.config.use_local_inference:
            local_exec: LocalImprovementExecutor = LocalImprovementExecutor(self.config)
            local_exec.start(self.config.worktree_path)
            cloud_exec: ImprovementExecutor | None = executor  # type: ignore[assignment]
        else:
            local_exec = None  # type: ignore[assignment]
            if executor is None:
                executor = ImprovementExecutor(self.config)
            cloud_exec = executor  # type: ignore[assignment]
            cloud_exec.start(self.config.worktree_path)  # type: ignore[union-attr]

        # Per-task consecutive local failure counter (reset on success or task change)
        _local_failures: dict[str, int] = {}
        # Sprint window tracking
        _sprint_start = time.time()
        _sprint_local_tokens: int = 0
        _sprint_cloud_tokens: int = 0
        _sprint_completed: int = 0
        _sprint_failed: int = 0
        _sprint_skipped: int = 0
        _category_stats: dict[str, dict[str, int]] = {}

        while not self.budget_exhausted:
            # C2: pre-sprint RAM guard
            if self.config.use_local_inference and not self._check_ram_before_load(
                self.config.min_free_ram_gb
            ):
                logger.warning(
                    "RAM below %.0f GB — routing to lightweight NPU model only this sprint",
                    self.config.min_free_ram_gb,
                )

            # Checkpoint if needed
            self._maybe_checkpoint()

            # Pick next task
            task = self._pick_next_task()
            if task is None:
                logger.info("No more tasks to process — loop complete")
                break

            self._current_task = task
            consecutive_failures = _local_failures.get(task.id, 0)
            use_cloud = (not self.config.use_local_inference) or (
                cloud_exec is not None
                and consecutive_failures >= self.config.cloud_escalation_threshold
            )

            tokens_before = self._total_tokens

            if use_cloud and cloud_exec is not None:
                logger.info(
                    "Escalating task %s to cloud executor (local failures: %d)",
                    task.id,
                    consecutive_failures,
                )
                if not getattr(cloud_exec, "_started", False):
                    cloud_exec.start(self.config.worktree_path)
                self._run_task(task, cloud_exec, is_cloud=True)
                _local_failures.pop(task.id, None)
                _sprint_cloud_tokens += self._total_tokens - tokens_before
            elif local_exec is not None:
                self._run_task(task, local_exec, is_cloud=False)
                if task.status == "failed":
                    _local_failures[task.id] = consecutive_failures + 1
                    # If cloud escalation is available, this failure is provisional.
                    # Reset to pending so the task can be re-dispatched or escalated
                    # on the next iteration. Only mark failed permanently when there
                    # is no cloud executor to escalate to.
                    if cloud_exec is not None:
                        task.status = "pending"
                        self._tasks_failed -= 1  # undo premature final-failure count
                else:
                    _local_failures.pop(task.id, None)
                _sprint_local_tokens += self._total_tokens - tokens_before
            else:
                break

            # Update per-sprint counters
            if task.status == "done":
                _sprint_completed += 1
            elif task.status == "failed":
                _sprint_failed += 1
            else:
                _sprint_skipped += 1

            # Update category stats for sweeper course correction
            # Keys must match LoopTickSweeper.course_correct() expectations: attempts/successes
            cat = task.category
            if cat not in _category_stats:
                _category_stats[cat] = {"attempts": 0, "successes": 0}
            _category_stats[cat]["attempts"] += 1
            if task.status == "done":
                _category_stats[cat]["successes"] += 1

            # Sprint boundary: flush when sprint window elapsed
            sprint_elapsed = time.time() - _sprint_start
            if sprint_elapsed >= self.config.sprint_duration_seconds:
                sprint_result = SprintResult(
                    sprint_number=self._sprint_number,
                    tasks_completed=_sprint_completed,
                    tasks_failed=_sprint_failed,
                    tasks_skipped=_sprint_skipped,
                    tokens_used=_sprint_local_tokens + _sprint_cloud_tokens,
                    wall_clock_seconds=sprint_elapsed,
                    local_tokens=_sprint_local_tokens,
                    cloud_tokens=_sprint_cloud_tokens,
                )
                self._sprint_results.append(sprint_result)
                self._sprint_number += 1
                logger.info(
                    "Sprint %d complete — %d done, %d failed, %d local tokens, %d cloud tokens",
                    sprint_result.sprint_number,
                    _sprint_completed,
                    _sprint_failed,
                    _sprint_local_tokens,
                    _sprint_cloud_tokens,
                )

                # Course correction from tick sweeper (uses per-category success rates)
                if local_exec is not None:
                    try:
                        recommendations = local_exec._sweeper.course_correct(
                            [asdict(sprint_result)], _category_stats
                        )
                        if recommendations:
                            logger.info("Sweeper course corrections: %s", recommendations)
                    except Exception as exc:
                        logger.debug("Sweeper course_correct skipped: %s", exc)

                # Reset sprint accumulators
                _sprint_start = time.time()
                _sprint_local_tokens = 0
                _sprint_cloud_tokens = 0
                _sprint_completed = 0
                _sprint_failed = 0
                _sprint_skipped = 0

            if self.config.fail_fast and self._tasks_failed > 0:
                logger.warning("Fail-fast triggered, stopping loop")
                break

        # Final checkpoint and report
        self._save_checkpoint()
        if local_exec is not None:
            local_exec.stop()
        if cloud_exec is not None and getattr(cloud_exec, "_started", False):
            cloud_exec.stop()
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

    def _run_task(self, task: LoopTask, executor: Any, *, is_cloud: bool = False) -> None:
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
                    "category": task.category,
                    "success": task.status == "done",
                    "status": task.status,
                    "result": task.result,
                    "tokens": task.tokens_used,
                    "duration": task.duration_seconds,
                    "is_cloud": is_cloud,
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
            started_at=datetime.fromtimestamp(self._start_time).isoformat(),
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
