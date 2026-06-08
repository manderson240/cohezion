"""Item 185: deduplicate_problems() — first-occurrence dedup (2026-06-08).

``deduplicate_problems(problems: list[Problem])`` → ``list[Problem]``:
Returns a new list with duplicate ``finding_id`` values removed.
The FIRST occurrence of each ID is kept; subsequent duplicates are dropped.
Insertion order is preserved for the survivors.  Empty list → ``[]``.
Pure; no I/O.

Discriminating tests — each kills a plausible wrong implementation:

  1. PRIMARY DISC.: list with one duplicate → shorter list, first occurrence kept.
     Kills an impl that keeps all duplicates (no-op dedup) or raises on duplicates.
  2. All-unique list → returned unchanged (same elements, same order).
     Kills an impl that always drops the last element.
  3. Empty list → ``[]`` (no raises).
     Kills an impl that raises IndexError on empty input.
  4. Order of survivors matches input order (not sorted).
     Kills an impl that sorts surviving elements instead of preserving insertion order.
  5. Third occurrence of a triplicate is also dropped (only first kept).
     Kills an impl that only deduplicates pairs (keeps 2 when there are 3).
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import (
    Problem,
    deduplicate_problems,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _p(cls: str, fid: str) -> Problem:
    return Problem(problem_class=cls, finding_id=fid)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_one_duplicate_kept_first_occurrence() -> None:
    """List with one duplicate finding_id → shorter list; first occurrence kept.

    PRIMARY DISCRIMINATOR: kills an impl that keeps all occurrences (no-op)
    or raises on duplicates (assert_no_duplicate_finding_ids behaviour).
    """
    dup_id = "complexity_outlier:src/foo.py:10"
    p_first = _p("complexity_outlier", dup_id)
    p_second = _p("complexity_outlier", dup_id)
    p_other = _p("nesting_outlier", "nesting_outlier:src/bar.py:5")
    problems = [p_first, p_other, p_second]

    result = deduplicate_problems(problems)

    assert len(result) == 2, f"Duplicate must be removed; expected 2 elements, got {len(result)}"
    # The first occurrence (p_first) must be kept, p_second dropped
    assert result[0] is p_first, f"First occurrence must be kept; got {result[0]!r}"
    assert result[1] is p_other, f"Other finding must be at index 1; got {result[1]!r}"


def test_all_unique_returned_unchanged() -> None:
    """All-unique finding_ids → list content returned unchanged (same order).

    Kills an impl that always drops the last element or alters unique lists.
    """
    problems = [
        _p("cls", "a"),
        _p("cls", "b"),
        _p("cls", "c"),
    ]

    result = deduplicate_problems(problems)

    assert len(result) == 3, f"All-unique list must be unchanged; got {len(result)}"
    assert [p.finding_id for p in result] == ["a", "b", "c"], (
        f"Order must be preserved; got {[p.finding_id for p in result]!r}"
    )


def test_empty_list_returns_empty() -> None:
    """Empty list → [] (no raises).

    Kills an impl that raises IndexError or similar on empty input.
    """
    result = deduplicate_problems([])

    assert result == [], f"Empty input must return []; got {result!r}"


def test_insertion_order_preserved_not_sorted() -> None:
    """Survivors keep insertion order (not sorted lexicographically).

    Kills an impl that sorts survivors instead of preserving input order.
    Insertion order is: "z_id" first, then "a_id" — the reverse of sorted.
    """
    problems = [
        _p("cls", "z_id"),
        _p("cls", "a_id"),
    ]

    result = deduplicate_problems(problems)

    assert [p.finding_id for p in result] == ["z_id", "a_id"], (
        f"Insertion order must be preserved; got {[p.finding_id for p in result]!r}"
    )


def test_triplicate_only_first_kept() -> None:
    """Three occurrences of the same finding_id → only first kept (2 dropped).

    Kills an impl that only deduplicates pairs (keeps 2 occurrences when 3 exist).
    """
    dup_id = "compound_smell:src/big.py:method"
    problems = [_p("compound_smell", dup_id) for _ in range(3)]

    result = deduplicate_problems(problems)

    assert len(result) == 1, (
        f"Triplicate must be reduced to 1 element; got {len(result)}: {result!r}"
    )
    assert result[0].finding_id == dup_id, (
        f"Surviving element must have the deduplicated ID; got {result[0].finding_id!r}"
    )
