"""Discriminating tests for the cross-loop telemetry instrument (item 25, 2026-06-06).

A read-only aggregator over the 3 self-improvement loop artifacts (IMPROVEMENT_BACKLOG status
counts, WIRING_SWEEP_LEDGER swept-package table, BLEEDING_EDGE_FEED round count). The falsifiable
check (item 25): returned counts EXACTLY match the source files. Tests use SYNTHETIC fixtures with
KNOWN counts so a hardcoded/stale-count impl fails, plus a read-only guard (the source bytes must
be unchanged after the call).
"""

from __future__ import annotations

from pathlib import Path

from cohezion.compound.loop_telemetry import LoopTelemetry, loop_telemetry


_BACKLOG = """\
| 1 | A | **x** | check | additive | DONE abc123 (did it) |
| 2 | B | **y** | check | additive | DONE def456 |
| 3 | C | **z** | check | additive | TODO |
| 18 | B | **blocked one** | check | needs | BLOCKED (assets) — needs HUMAN |
## Notes
- prose mentioning DONE and TODO that must NOT be counted as rows.
"""

_LEDGER = """\
## Swept packages
| Package | Swept | A wired |
|---|---|---|
| compound | **DONE** | 9 |
| inference | **DONE** | 1 |
| world_model | in progress | 1/3 |
### a section header that says DONE but is not a table row
"""

_FEED = """\
# Bleeding-edge feed
## 2026-06-06 (round 1)
some rows
## 2026-06-06 (round 2)
more rows
## Notes (not a round header)
"""


def _write(tmp: Path) -> tuple[Path, Path, Path]:
    b, l, f = tmp / "backlog.md", tmp / "ledger.md", tmp / "feed.md"
    b.write_text(_BACKLOG)
    l.write_text(_LEDGER)
    f.write_text(_FEED)
    return b, l, f


def test_counts_match_source_exactly(tmp_path: Path) -> None:
    b, l, f = _write(tmp_path)
    t = loop_telemetry(backlog_path=b, ledger_path=l, feed_path=f)
    assert isinstance(t, LoopTelemetry)
    # 2 DONE / 1 TODO / 1 BLOCKED rows (prose DONE/TODO in ## Notes must NOT count)
    assert t.backlog_done == 2
    assert t.backlog_todo == 1
    assert t.backlog_blocked == 1
    # 2 **DONE** table rows ("in progress" + the prose header must NOT count)
    assert t.swept_packages_done == 2
    # 2 round headers ("## Notes" must NOT count)
    assert t.research_rounds == 2


def test_is_read_only_source_bytes_unchanged(tmp_path: Path) -> None:
    b, l, f = _write(tmp_path)
    before = (b.read_bytes(), l.read_bytes(), f.read_bytes())
    loop_telemetry(backlog_path=b, ledger_path=l, feed_path=f)
    after = (b.read_bytes(), l.read_bytes(), f.read_bytes())
    assert before == after, "loop_telemetry must be READ-ONLY — it modified a source file"


def test_missing_files_are_zeros_not_a_crash(tmp_path: Path) -> None:
    t = loop_telemetry(
        backlog_path=tmp_path / "nope1.md",
        ledger_path=tmp_path / "nope2.md",
        feed_path=tmp_path / "nope3.md",
    )
    assert t.backlog_done == 0 and t.backlog_todo == 0 and t.backlog_blocked == 0
    assert t.swept_packages_done == 0 and t.research_rounds == 0


# --- item 39: loop_progress_delta (pure signed delta, mirrors CB11 diff_snapshots) -------------

from cohezion.compound.loop_telemetry import (
    LoopProgressDelta,
    loop_progress_delta,
)


def _lt(done: int, todo: int, blocked: int, swept: int, rounds: int) -> LoopTelemetry:
    return LoopTelemetry(
        backlog_done=done,
        backlog_todo=todo,
        backlog_blocked=blocked,
        swept_packages_done=swept,
        research_rounds=rounds,
    )


def test_identical_snapshots_yield_all_zero_delta() -> None:
    snap = _lt(10, 5, 1, 17, 3)
    d = loop_progress_delta(snap, snap)
    assert d == LoopProgressDelta(0, 0, 0, 0, 0)


def test_advanced_snapshot_exact_signed_deltas() -> None:
    before = _lt(done=10, todo=5, blocked=1, swept=16, rounds=3)
    after = _lt(done=12, todo=3, blocked=1, swept=17, rounds=4)
    d = loop_progress_delta(before, after)
    assert d.done_delta == 2
    assert d.todo_delta == -2  # TODO shrank as items completed — a real negative
    assert d.blocked_delta == 0
    assert d.swept_delta == 1
    assert d.rounds_delta == 1


def test_regression_is_negative_not_clamped() -> None:
    # A regressed count (DONE dropped, swept dropped) must show NEGATIVE — not max(0,..)/abs(..).
    before = _lt(done=12, todo=3, blocked=1, swept=17, rounds=4)
    after = _lt(done=10, todo=5, blocked=2, swept=16, rounds=4)
    d = loop_progress_delta(before, after)
    assert d.done_delta == -2, "regression must not be clamped to 0"
    assert d.swept_delta == -1
    assert d.todo_delta == 2
    assert d.blocked_delta == 1
    assert d.rounds_delta == 0


def test_each_field_maps_to_its_own_delta() -> None:
    # Change exactly ONE field at a time → only that delta is non-zero (kills a field-mixup impl).
    base = _lt(5, 5, 5, 5, 5)
    assert loop_progress_delta(base, _lt(6, 5, 5, 5, 5)).done_delta == 1
    assert loop_progress_delta(base, _lt(6, 5, 5, 5, 5)).todo_delta == 0
    assert loop_progress_delta(base, _lt(5, 6, 5, 5, 5)).todo_delta == 1
    assert loop_progress_delta(base, _lt(5, 5, 6, 5, 5)).blocked_delta == 1
    assert loop_progress_delta(base, _lt(5, 5, 5, 6, 5)).swept_delta == 1
    assert loop_progress_delta(base, _lt(5, 5, 5, 5, 6)).rounds_delta == 1
