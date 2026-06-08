"""Item 187: count_problems() — named scalar count accessor (2026-06-08).

``count_problems(problems: list[Problem])`` → ``int``:
Returns the total number of findings in *problems*.  Equivalent to
``len(problems)`` but names the concept explicitly for CI scripts.

Discriminating tests — each kills a plausible wrong implementation:

  1. PRIMARY DISC.: non-empty list → correct count (not 0, not always 1).
     Kills an impl that always returns 0 or always returns 1.
  2. Empty list → 0 (no raises).
     Kills an impl that raises on empty input.
  3. Single element → 1.
     Kills an impl that returns 0 for length-1 lists.
  4. Count matches the actual list length for varied sizes.
     Kills an impl that hard-codes a specific value.
  5. Multiple classes counted together (not per-class).
     Kills an impl that counts only distinct classes instead of total findings.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import (
    Problem,
    count_problems,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _p(cls: str, idx: int = 0) -> Problem:
    return Problem(problem_class=cls, finding_id=f"{cls}:{idx}")


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_non_empty_list_correct_count() -> None:
    """Non-empty list → correct total count.

    PRIMARY DISCRIMINATOR: kills an impl that always returns 0 (never counts)
    or always returns 1 (ignores list length).
    '3' findings must yield 3, not 0, 1, or 2.
    """
    problems = [_p("complexity_outlier"), _p("nesting_outlier"), _p("long_function")]

    result = count_problems(problems)

    assert result == 3, f"3 findings must return 3; got {result!r}"


def test_empty_list_returns_zero() -> None:
    """Empty list → 0 (no raises).

    Kills an impl that raises IndexError or returns None on empty input.
    """
    result = count_problems([])

    assert result == 0, f"Empty list must return 0; got {result!r}"


def test_single_element_returns_one() -> None:
    """Single-element list → 1.

    Kills an impl that returns 0 for length-1 lists (off-by-one error).
    """
    result = count_problems([_p("complexity_outlier")])

    assert result == 1, f"Single element must return 1; got {result!r}"


def test_count_matches_length_for_varied_size() -> None:
    """Count equals len(problems) for multiple list sizes.

    Kills an impl that hard-codes a specific value (e.g. always returns 3).
    """
    for n in (2, 5, 7):
        problems = [_p("complexity_outlier", i) for i in range(n)]
        result = count_problems(problems)
        assert result == n, f"count_problems with {n} elements must return {n}; got {result!r}"


def test_counts_all_findings_not_distinct_classes() -> None:
    """Multiple findings per class → total count includes all, not just distinct classes.

    Kills an impl that counts unique problem_class values instead of total
    findings (i.e. returns 2 for 5 findings across 2 classes instead of 5).
    """
    problems = [_p("complexity_outlier", i) for i in range(4)] + [
        _p("nesting_outlier", i) for i in range(3)
    ]

    result = count_problems(problems)

    assert result == 7, f"7 total findings across 2 classes must return 7 (not 2); got {result!r}"
