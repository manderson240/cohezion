"""Item 78: regressed backlog items (report-only, TDD red->green).

`regressed_backlog_items(before_text, after_text)` diffs two backlog snapshots
and returns item numbers whose status went from DONE to not-DONE (TODO/BLOCKED).

Each test fails a plausible wrong impl:
  - flags stable-DONE items as regressions       -> test_stable_done_not_listed
  - flags new items (never done) as regressions  -> test_new_item_not_a_regression
  - counts TODO->DONE as a regression            -> test_done_in_after_not_a_regression
  - non-zero on identical snapshots              -> test_identical_snapshots_empty
"""

from __future__ import annotations

from cohezion.compound.loop_telemetry import regressed_backlog_items

# ---------------------------------------------------------------------------
# Helpers — minimal backlog row fragments
# ---------------------------------------------------------------------------

_HEADER = "| # | Thread | Item | Check | Gating | Status |\n|---|---|---|---|---|---|\n"


def _row(num: int, status: str) -> str:
    """One minimal backlog row with the given item number and status."""
    return f"| {num} | A | desc | check | additive | {status} |\n"


def _snapshot(*rows: tuple[int, str]) -> str:
    """Build a minimal backlog text from (number, status) pairs."""
    return _HEADER + "".join(_row(n, s) for n, s in rows)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestRegressionDetection:
    """Core discriminating tests: the function must identify real regressions."""

    def test_done_to_todo_is_regression(self) -> None:
        """An item DONE in before and TODO in after is a regression."""
        before = _snapshot((5, "DONE abc123"), (10, "DONE def456"))
        after = _snapshot((5, "TODO"), (10, "DONE def456"))
        result = regressed_backlog_items(before, after)
        assert result == [5], f"expected [5], got {result}"

    def test_done_to_blocked_is_regression(self) -> None:
        """An item DONE in before and BLOCKED in after is a regression."""
        before = _snapshot((7, "DONE abc123"))
        after = _snapshot((7, "BLOCKED dependency_missing"))
        result = regressed_backlog_items(before, after)
        assert result == [7]

    def test_done_to_doing_is_regression(self) -> None:
        """An item DONE in before and DOING in after is a regression."""
        before = _snapshot((3, "DONE abc123"))
        after = _snapshot((3, "DOING"))
        result = regressed_backlog_items(before, after)
        assert result == [3]

    def test_multiple_regressions_all_listed(self) -> None:
        """All regressed items are returned, sorted ascending."""
        before = _snapshot((1, "DONE a"), (2, "DONE b"), (3, "DONE c"), (4, "TODO"))
        after = _snapshot((1, "TODO"), (2, "DONE b"), (3, "BLOCKED x"), (4, "TODO"))
        result = regressed_backlog_items(before, after)
        assert result == [1, 3], f"expected [1, 3], got {result}"


class TestNonRegressions:
    """The function must NOT flag items that are not true regressions."""

    def test_stable_done_not_listed(self) -> None:
        """An item DONE in both before and after is not a regression."""
        snap = _snapshot((5, "DONE abc123"), (6, "DONE def456"))
        result = regressed_backlog_items(snap, snap)
        assert result == [], f"stable DONE items must not be flagged: {result}"

    def test_new_item_not_a_regression(self) -> None:
        """An item absent from before (never done) is not a regression even if it's TODO."""
        before = _snapshot((1, "DONE abc"))
        after = _snapshot((1, "DONE abc"), (99, "TODO"))
        result = regressed_backlog_items(before, after)
        assert result == [], (
            f"a new TODO item with no before-entry is NOT a regression; got {result}"
        )

    def test_todo_to_done_not_a_regression(self) -> None:
        """Progress (TODO->DONE) is never a regression."""
        before = _snapshot((3, "TODO"), (4, "DONE abc"))
        after = _snapshot((3, "DONE xyz"), (4, "DONE abc"))
        result = regressed_backlog_items(before, after)
        assert result == [], f"expected [] (progress), got {result}"

    def test_todo_staying_todo_not_a_regression(self) -> None:
        """A stable TODO item does not appear in the regression list."""
        before = _snapshot((8, "TODO"), (9, "DONE abc"))
        after = _snapshot((8, "TODO"), (9, "DONE abc"))
        result = regressed_backlog_items(before, after)
        assert result == []

    def test_identical_snapshots_empty(self) -> None:
        """Identical snapshots always return an empty list."""
        snap = _snapshot((1, "DONE a"), (2, "TODO"), (3, "BLOCKED x"))
        assert regressed_backlog_items(snap, snap) == []


class TestEdgeCases:
    """Edge cases: empty inputs, missing items, ordering."""

    def test_empty_before_and_after(self) -> None:
        """Two empty texts produce an empty list."""
        assert regressed_backlog_items("", "") == []

    def test_item_removed_in_after_not_listed(self) -> None:
        """An item present in before but absent in after is NOT a regression."""
        before = _snapshot((5, "DONE abc"))
        after = _snapshot((6, "TODO"))  # item 5 deleted
        result = regressed_backlog_items(before, after)
        assert result == [], (
            "a deleted item is not a regression (can't regress from existence to non-existence)"
        )

    def test_result_is_sorted_ascending(self) -> None:
        """Returned item numbers are sorted ascending."""
        before = _snapshot((20, "DONE a"), (5, "DONE b"), (15, "DONE c"))
        after = _snapshot((20, "TODO"), (5, "TODO"), (15, "TODO"))
        result = regressed_backlog_items(before, after)
        assert result == sorted(result), f"result must be sorted, got {result}"
        assert result == [5, 15, 20]
