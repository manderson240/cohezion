"""Discriminating tests for the loop stall detector (item 30, 2026-06-06).

`detect_loop_stall(before, after)` compares two LoopTelemetry snapshots and flags a STALLED
build loop (report-only). The subtlety: "backlog_done unchanged" is NOT itself a stall — it is
only a stall when there is OUTSTANDING work (TODO>0, or BLOCKED growing). Two empty snapshots
are quiescent, not stuck.

Each test fails a plausible wrong impl:
  - flag healthy progress as a stall → T_healthy,
  - never flag a real stall → T_stalled,
  - the naive "done unchanged ⇒ stalled" that false-flags an empty backlog → T_quiescent,
  - ignore BLOCKED growth → T_blocked.
"""

from __future__ import annotations

from cohezion.compound.loop_telemetry import LoopTelemetry, detect_loop_stall


def _snap(done: int, todo: int, blocked: int = 0) -> LoopTelemetry:
    return LoopTelemetry(
        backlog_done=done,
        backlog_todo=todo,
        backlog_blocked=blocked,
        swept_packages_done=0,
        research_rounds=0,
    )


def test_healthy_when_done_advances() -> None:
    # DONE went up between snapshots → progress → not stalled (even with TODO remaining).
    r = detect_loop_stall(_snap(5, 3), _snap(6, 2))
    assert r.stalled is False
    assert "healthy" in r.reason


def test_stalled_when_no_done_progress_and_todo_remains() -> None:
    # DONE unchanged AND work remains → the build loop is stuck.
    r = detect_loop_stall(_snap(5, 3), _snap(5, 3))
    assert r.stalled is True
    assert "TODO" in r.reason


def test_no_false_stall_on_quiescent_empty() -> None:
    # Two identical EMPTY snapshots (nothing done, nothing to do) → quiescent, NOT a stall.
    # The naive "done unchanged ⇒ stalled" impl wrongly flags this — this test kills it.
    r = detect_loop_stall(_snap(0, 0), _snap(0, 0))
    assert r.stalled is False
    assert "quiescent" in r.reason


def test_stalled_when_blocked_grows_without_done_progress() -> None:
    # No DONE progress, no TODO, but BLOCKED grew → work piling up unresolved → stalled.
    r = detect_loop_stall(_snap(5, 0, blocked=1), _snap(5, 0, blocked=2))
    assert r.stalled is True
    assert "BLOCKED" in r.reason


def test_all_done_no_todo_is_not_a_stall() -> None:
    # Everything finished (TODO=0), DONE unchanged, BLOCKED flat → quiescent, not stuck.
    r = detect_loop_stall(_snap(10, 0), _snap(10, 0))
    assert r.stalled is False
