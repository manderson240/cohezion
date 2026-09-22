"""LoopCoordinator — compound improvement loop with local/cloud routing.

When the local executor supports execute_batch(), tasks are fanned out
concurrently across NPU/iGPU/CPU tiers (one batch per sprint tick).
Cloud escalation still runs sequentially for tasks that have exceeded
the local failure threshold.
"""

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
    batch_size: int = 3  # max local tasks fanned out in parallel per iteration
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
    # ACT spec (additive, all optional): a human-written pytest node id the change must
    # turn green, plus the ONE src/ file and top-level defs the model may replace. A task
    # without them is `needs_oracle` -- never completion. See act_loop.py.
    oracle_test: str = ""
    edit_file: str = ""
    edit_targets: list[str] = field(default_factory=list)


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
    def __init__(
        self,
        config: LoopConfig,
        degradation_detector: Any = None,
        *,
        difficulty_estimator: Any = None,
    ) -> None:
        self.config = config
        # Receives measured ACT outcomes (see _record_act_difficulty). None -> run() borrows
        # the executor's SkillRefiner estimator, the one CompoundExecutor.predict_tier reads.
        self._difficulty_estimator = difficulty_estimator
        self._backlog: list[LoopTask] = []
        self._sprint_results: list[SprintResult] = []
        # Episodic records accumulated this run, fed to MemoryConsolidator at end-of-cycle.
        self._episodes: list[dict[str, Any]] = []
        # CB5 pattern: auto-create DegradationDetector if not supplied
        if degradation_detector is None:
            with contextlib.suppress(Exception):
                from cohezion.compound.degradation_detector import DegradationDetector

                degradation_detector = DegradationDetector()
        self._degradation_detector = degradation_detector

    def run(self, executor: Any = None) -> RunReport:
        from cohezion.compound.autonomous_loop.executor import ImprovementExecutor
        from cohezion.compound.autonomous_loop.local_executor import LocalImprovementExecutor

        report = RunReport()
        fail_counts: dict[str, int] = {}
        category_stats: dict[str, dict[str, int]] = {}

        local_exec = None
        cloud_exec = executor
        if self._difficulty_estimator is None and executor is not None:
            with contextlib.suppress(Exception):
                refiner = getattr(executor, "skill_refiner", None)
                self._difficulty_estimator = getattr(refiner, "_difficulty_estimator", None)

        if self.config.use_local_inference:
            local_exec = LocalImprovementExecutor(
                self.config.local_base_url,
                degradation_detector=self._degradation_detector,
            )
            local_exec.start(self.config.worktree_path)
        else:
            cloud_exec = cloud_exec or ImprovementExecutor(self.config)
            cloud_exec.start(self.config.worktree_path)

        sprint_start = time.monotonic()
        sprint = SprintResult()

        try:
            remaining = list(self._backlog)
            while remaining:
                total_tokens = sum(r.get("tokens", 0) for r in report.results)
                if total_tokens >= self.config.max_tokens:
                    break

                # Batch-window: collect local-eligible tasks up to batch_size and fan
                # them across NPU/iGPU/CPU in parallel via execute_batch(). Cloud-due
                # tasks are processed one-at-a-time (they're already at the failure
                # threshold and rare; sequential is correct for ordered escalation).
                batch: list[Any] = []
                cloud_task = None

                next_task = remaining[0]  # safe: outer while guarantees non-empty
                if (
                    fail_counts.get(next_task.id, 0) >= self.config.cloud_escalation_threshold
                    or local_exec is None
                ):
                    cloud_task = remaining.pop(0)
                else:
                    while remaining and len(batch) < self.config.batch_size:
                        candidate = remaining[0]
                        if (
                            fail_counts.get(candidate.id, 0)
                            < self.config.cloud_escalation_threshold
                            and local_exec is not None
                        ):
                            remaining.pop(0)
                            batch.append(candidate)
                        else:
                            break  # cloud-due task at head — stop building batch

                if batch and local_exec is not None:
                    results = local_exec.execute_batch(batch, self.config.worktree_path)
                    result_by_id = {r["task_id"]: r for r in results}
                    for task in batch:
                        result = result_by_id.get(
                            task.id,
                            {
                                "success": False,
                                "tokens_used": 0,
                                "node": "?",
                                "model": "?",
                                "elapsed_ms": 0,
                                "tried_models": [],
                            },
                        )
                        tokens = result.get("tokens_used", 0)
                        sprint.local_tokens += tokens
                        self._record_result(
                            result, task, False, tokens, report, fail_counts, category_stats, sprint
                        )
                    # Re-queue ONE instance per unique task ID that hit the cloud threshold —
                    # preserves escalation semantics when multiple copies share a task.id.
                    cloud_escalate_ids: set[str] = set()
                    for task in batch:
                        if (
                            fail_counts.get(task.id, 0) >= self.config.cloud_escalation_threshold
                            and task.id not in cloud_escalate_ids
                        ):
                            remaining.insert(0, task)
                            cloud_escalate_ids.add(task.id)

                if cloud_task is not None and cloud_exec is not None:
                    if not getattr(cloud_exec, "_started", False):
                        cloud_exec.start(self.config.worktree_path)
                    result = cloud_exec.execute_task(cloud_task, self.config.worktree_path)
                    tokens = result.get("tokens_used", 0)
                    sprint.cloud_tokens += tokens
                    self._record_result(
                        result,
                        cloud_task,
                        True,
                        tokens,
                        report,
                        fail_counts,
                        category_stats,
                        sprint,
                    )

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

        # End-of-cycle deferred consolidation: promote this run's episodes to durable semantic
        # facts (local-Gemma $0, fail-open). This is the production trigger for MemoryConsolidator.
        with contextlib.suppress(Exception):
            self._consolidate_episodes(report)

        return report

    def _consolidate_episodes(self, report: RunReport) -> None:
        """Run the automated episode -> semantic-fact consolidation pass over this cycle's episodes.

        Fires once per loop cycle (the Elastic deferred-consolidation cadence). No-op when no
        episodes were recorded; the consolidator itself is idempotent + fail-open."""
        if not self._episodes:
            return
        from cohezion.memory.consolidator import MemoryConsolidator

        consolidator = MemoryConsolidator()
        consolidator.consolidate(self._episodes)

    def _record_result(
        self,
        result: dict[str, Any],
        task: Any,
        is_cloud: bool,
        tokens: int,
        report: RunReport,
        fail_counts: dict[str, int],
        category_stats: dict[str, dict[str, int]],
        sprint: SprintResult,
    ) -> None:
        """Update all tracking state for a completed task result."""
        # Episodic record for end-of-cycle MemoryConsolidator promotion (provenance source).
        self._episodes.append(
            {
                "id": task.id,
                "text": getattr(task, "description", ""),
                "operation_type": task.category,
            }
        )
        success = result.get("success", False)
        task_fail_count = fail_counts.get(task.id, 0)
        if success:
            fail_counts[task.id] = 0
            report.tasks_completed += 1
            sprint.tasks_done += 1
        else:
            # needs_oracle is not a model failure: escalating it to cloud cannot help.
            if result.get("status") != "needs_oracle":
                fail_counts[task.id] = task_fail_count + 1
            report.tasks_failed += 1
            sprint.tasks_failed += 1

        cat = task.category
        if cat not in category_stats:
            category_stats[cat] = {"done": 0, "failed": 0}
        category_stats[cat]["done" if success else "failed"] += 1

        if "cascade_quality_score" in result:
            # PQ1: the producer measured quality (ACT: oracle GREEN 1.0 / EXHAUSTED 0.0) or
            # declared it UNKNOWN (None: instrument failure, flaky oracle). Authoritative --
            # an instrument failure must not be scored 0.0 as if the model had failed.
            quality_score: float | None = result["cascade_quality_score"]
            self._record_act_difficulty(task, result, quality_score)
        # Long2Short quality score: success/tokens (sparse — None when undefined)
        elif not success:
            quality_score = 0.0
        elif tokens > 0:
            quality_score = 1.0 / tokens
        else:
            quality_score = None  # success=True, tokens=0 → undefined

        report.results.append(
            {
                "task_id": task.id,
                "tokens": tokens,
                "is_cloud": is_cloud,
                "success": success,
                "node": result.get("node", "cloud" if is_cloud else "?"),
                "model": result.get("model", "?"),
                "elapsed_ms": result.get("elapsed_ms", 0),
                "fallback": len(result.get("tried_models") or []) > 1,
                "quality_score": quality_score,
            }
        )

        # CB5: wire DegradationDetector per-result (non-blocking)
        if self._degradation_detector is not None:
            with contextlib.suppress(Exception):
                sparse: dict[str, Any] = {
                    "elapsed_seconds": result.get("elapsed_ms", 0) / 1000.0,
                    "success_rate": 1.0 if success else 0.0,
                    "token_surprisal": result.get("token_surprisal"),
                }
                if quality_score is not None:
                    sparse["quality_score"] = quality_score
                self._degradation_detector.check_degradation(sparse)

    def _record_act_difficulty(
        self, task: Any, result: dict[str, Any], quality_score: float | None
    ) -> None:
        """Credit a measured ACT outcome to the engine that produced it.

        Recorded directly, not via SkillRefiner.refine(): refine() learns only from
        successes, so an EXHAUSTED 0.0 would never reach the estimator. Skipped when quality
        is UNKNOWN or the engine tier is unmapped (the estimator would coerce it to "cpu").
        """
        tier = result.get("tier_used")
        if self._difficulty_estimator is None or quality_score is None:
            return
        if tier not in ("npu", "igpu", "cpu"):
            return
        with contextlib.suppress(Exception):
            self._difficulty_estimator.record(
                "act_loop",
                task.category,
                tier,
                0,  # act_loop iterations are attempts on one model, not tier escalations
                quality_score,
                latency_s=result.get("elapsed_ms", 0) / 1000.0,
            )
