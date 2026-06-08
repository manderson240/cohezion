"""Discriminating tests for regressed_backlog_items (backlog item 78, 2026-06-08).

`regressed_backlog_items(before_text, after_text)` is the actionable detail behind item-58's
`detect_loop_regression` boolean: WHICH item numbers went DONE -> not-DONE between two backlog
snapshots. Composes item-25's tested row/status parsing (`_BACKLOG_NUM` + `_status_first_word`).
Report-only, pure (text diff, no I/O).

Each test fails a plausible wrong impl:
  - an impl that diffs only PRESENCE (not status) flags new TODO items → test_new_item_not_regression,
  - an impl that ignores the DONE-in-before guard flags any TODO → test_new_item_not_regression,
  - an impl that flags stable DONE rows → test_stable_done_not_listed,
  - an impl that treats a deleted row as a regression → test_deleted_item_not_flagged.
"""

from __future__ import annotations

from cohezion.compound.loop_telemetry import regressed_backlog_items


def _row(num: int, status: str) -> str:
    # Mirrors a real backlog row: ``| <n> | <prio> | **desc** | crit | class | <STATUS …> |``.
    return f"| {num} | A | **thing {num}** | crit | additive | {status} |"


def test_done_to_todo_is_regression() -> None:
    before = _row(10, "DONE abc123 (shipped)")
    after = _row(10, "TODO")
    assert regressed_backlog_items(before, after) == [10]


def test_stable_done_not_listed() -> None:
    # DISCRIMINATING: a row DONE in both snapshots is NOT a regression.
    before = _row(10, "DONE abc123 (shipped)")
    after = _row(10, "DONE abc123 (shipped)")
    assert regressed_backlog_items(before, after) == []


def test_new_item_not_regression() -> None:
    # DISCRIMINATING: an item absent from `before` (brand-new TODO) is NOT a regression —
    # it was never DONE. A presence-only or status-only diff would wrongly flag it.
    before = _row(10, "DONE abc123")
    after = _row(10, "DONE abc123") + "\n" + _row(11, "TODO")
    assert regressed_backlog_items(before, after) == []


def test_deleted_item_not_flagged() -> None:
    # DISCRIMINATING: a DONE row DELETED in `after` (absent, not TODO/BLOCKED) is a different
    # event than a status reversal — it must NOT be flagged as a regression.
    before = _row(10, "DONE abc123") + "\n" + _row(11, "DONE def456")
    after = _row(10, "DONE abc123")  # item 11 removed entirely
    assert regressed_backlog_items(before, after) == []


def test_done_to_blocked_is_regression() -> None:
    before = _row(7, "DONE xyz")
    after = _row(7, "BLOCKED waiting on lane")
    assert regressed_backlog_items(after_text=after, before_text=before) == [7]


def test_multiple_regressions_sorted() -> None:
    before = "\n".join([_row(30, "DONE a"), _row(5, "DONE b"), _row(12, "DONE c")])
    after = "\n".join([_row(30, "TODO"), _row(5, "DONE b"), _row(12, "BLOCKED")])
    assert regressed_backlog_items(before, after) == [12, 30]


def test_identical_snapshots_empty() -> None:
    snap = "\n".join([_row(1, "DONE a"), _row(2, "TODO"), _row(3, "BLOCKED x")])
    assert regressed_backlog_items(snap, snap) == []


def test_live_backlog_self_diff_is_empty() -> None:
    # Non-fabricated: the real backlog diffed against itself has zero regressions.
    from pathlib import Path

    text = Path("docs/IMPROVEMENT_BACKLOG.md").read_text(encoding="utf-8", errors="replace")
    assert regressed_backlog_items(text, text) == []
