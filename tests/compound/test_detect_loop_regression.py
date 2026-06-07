"""Discriminating tests for the loop regression detector (item 58, 2026-06-06).

`detect_loop_regression(before, after)` consumes item-39 `loop_progress_delta` and flags a REGRESSION
— a monotone-should-increase count (done/swept/rounds) that moved BACKWARD: completed/swept/researched
work became un-done. Distinct from item-30's STALL (no progress); a regression is NEGATIVE progress.
It is the predicate that justifies item 39's unclamped-signed delta (a clamped delta couldn't express it).

Each test fails a plausible wrong impl:
  - misses a backward done/swept/rounds → test_done/swept/rounds_dropped,
  - treats new TODO work as a regression → test_todo_growth_not_regression,
  - treats growing BLOCKED as a regression (that is stall territory) → test_blocked_growth_not_regression,
  - flags forward/flat progress → test_forward_and_flat_not_regression.
"""

from __future__ import annotations

from cohezion.compound.loop_telemetry import LoopTelemetry, detect_loop_regression


def _lt(done: int, todo: int, blocked: int, swept: int, rounds: int) -> LoopTelemetry:
    return LoopTelemetry(
        backlog_done=done,
        backlog_todo=todo,
        backlog_blocked=blocked,
        swept_packages_done=swept,
        research_rounds=rounds,
    )


def test_done_dropped_is_regression() -> None:
    r = detect_loop_regression(_lt(12, 3, 1, 17, 4), _lt(10, 3, 1, 17, 4))
    assert r.regressed is True
    assert "done" in r.reason.lower()


def test_swept_dropped_is_regression() -> None:
    r = detect_loop_regression(_lt(12, 3, 1, 17, 4), _lt(12, 3, 1, 16, 4))
    assert r.regressed is True
    assert "swept" in r.reason.lower()


def test_rounds_dropped_is_regression() -> None:
    r = detect_loop_regression(_lt(12, 3, 1, 17, 5), _lt(12, 3, 1, 17, 4))
    assert r.regressed is True
    assert "round" in r.reason.lower()


def test_todo_growth_not_regression() -> None:
    # New work queued (todo↑) with done/swept/rounds flat → healthy growth, NOT a regression.
    r = detect_loop_regression(_lt(12, 3, 1, 17, 4), _lt(12, 9, 1, 17, 4))
    assert r.regressed is False


def test_blocked_growth_not_regression() -> None:
    # BLOCKED growing is item-30 STALL territory, not a regression of completed work.
    r = detect_loop_regression(_lt(12, 3, 1, 17, 4), _lt(12, 3, 5, 17, 4))
    assert r.regressed is False


def test_forward_and_flat_not_regression() -> None:
    assert detect_loop_regression(_lt(10, 5, 1, 16, 3), _lt(12, 3, 1, 17, 4)).regressed is False
    snap = _lt(12, 3, 1, 17, 4)
    assert detect_loop_regression(snap, snap).regressed is False
