"""needs_oracle is a third outcome: neither completion nor failure.

Review 2026-09-22 (C2/ops #3): a task with no ACT oracle returns ``needs_oracle`` with
``success=False``. The coordinator counted it in ``tasks_failed`` (and as a category failure),
so the daemon's batch read as failed: DaemonHealth.record_failure every cycle and the prose lane
re-run MAX_TASK_ATTEMPTS times for a task that can never complete without an oracle. It now has
its own counter, is not a failure, does not bump fail_counts (no retry/escalation) and is
surfaced in the per-result record. No live inference: results are hand-built dicts.
"""

from __future__ import annotations

from unittest.mock import MagicMock

from cohezion.compound.autonomous_loop.coordinator import (
    LoopConfig,
    LoopCoordinator,
    LoopTask,
    RunReport,
    SprintResult,
)


def _task(tid: str = "t1") -> LoopTask:
    return LoopTask(tid, "d", "bugfix", 1, "", 10)


def _record(result: dict):
    coord = LoopCoordinator(LoopConfig(), degradation_detector=MagicMock())
    report, sprint = RunReport(), SprintResult()
    fail_counts: dict[str, int] = {}
    cats: dict[str, dict[str, int]] = {}
    coord._record_result(result, _task(), False, 0, report, fail_counts, cats, sprint)
    return report, sprint, fail_counts, cats


def test_needs_oracle_is_neither_done_nor_failed():
    report, sprint, fail_counts, cats = _record({"success": False, "status": "needs_oracle"})
    assert report.tasks_failed == 0 and report.tasks_completed == 0
    assert report.tasks_needs_oracle == 1
    assert sprint.tasks_failed == 0 and sprint.tasks_needs_oracle == 1
    assert fail_counts.get("t1", 0) == 0  # no retry / cloud escalation
    assert cats["bugfix"].get("failed", 0) == 0 and cats["bugfix"]["needs_oracle"] == 1
    assert report.results[-1]["outcome"] == "needs_oracle"


def test_a_real_failure_is_still_a_failure():
    """Discriminating pair: only needs_oracle leaves the failure ledger."""
    report, sprint, fail_counts, cats = _record({"success": False, "status": "act_exhausted"})
    assert report.tasks_failed == 1 and report.tasks_needs_oracle == 0
    assert fail_counts["t1"] == 1 and cats["bugfix"]["failed"] == 1
    assert report.results[-1]["outcome"] == "failed"


def test_all_needs_oracle_batch_is_not_reported_as_failed(monkeypatch):
    """End-to-end through run(): the batch summary distinguishes the third outcome."""
    import cohezion.compound.autonomous_loop.local_executor as le

    local = MagicMock()
    local.execute_batch.side_effect = lambda batch, _wt: [
        {"task_id": t.id, "success": False, "status": "needs_oracle", "tokens_used": 0}
        for t in batch
    ]
    monkeypatch.setattr(le, "LocalImprovementExecutor", lambda *a, **k: local)
    coord = LoopCoordinator(
        LoopConfig(cloud_escalation_threshold=1, sprint_duration_seconds=1e9),
        degradation_detector=MagicMock(),
    )
    monkeypatch.setattr(coord, "_consolidate_episodes", lambda _r: None)
    coord._backlog = [_task("a"), _task("b")]
    report = coord.run(executor=None)
    assert (report.tasks_completed, report.tasks_failed, report.tasks_needs_oracle) == (0, 0, 2)
    # threshold=1: had needs_oracle counted as a failure each task would re-run on "cloud"
    assert local.execute_batch.call_count == 1
    # zero tokens: the sprint must still be kept, or the outcome vanishes from sprint_results
    assert sum(s.tasks_needs_oracle for s in report.sprint_results) == 2
