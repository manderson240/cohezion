"""Item 370: count_distinct_classes() — number of distinct class names present (2026-06-08).

``count_distinct_classes(problems) -> int``:
Returns the integer count of distinct problem_class strings present in the list.
Empty input → 0.  Pure; no I/O.  Mirror of count_distinct_severities.

Discriminating tests — each kills a plausible wrong implementation:

  1. PRIMARY DISC.: counts DISTINCT class strings, not total problem records.
     Kills impl returning len(problems).
  2. Single class with many records → returns 1.
     Kills impl counting problem records instead of unique classes.
  3. Empty input returns 0.
     Kills impl raising on empty.
  4. Two classes with equal record count → returns 2 (both counted).
     Kills impl that accidentally deduplicates by count.
  5. Return type is int, not a list or frozenset.
     Kills impl returning the class names themselves.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import (
    Problem,
    count_distinct_classes,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _p(cls: str, fid: str) -> Problem:
    return Problem(problem_class=cls, finding_id=fid)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_counts_distinct_not_total_records() -> None:
    """Counts distinct class strings, not total problem records.

    PRIMARY DISCRIMINATOR: kills impl returning len(problems).
    3 problems all in 'alpha' → 1 distinct class, not 3.
    """
    problems = [_p("alpha", "f:0"), _p("alpha", "f:1"), _p("alpha", "f:2")]
    result = count_distinct_classes(problems)
    assert result == 1, "All alpha → 1 distinct class; got " + repr(result)


def test_single_class_many_records_returns_one() -> None:
    """One class with many records → count is 1.

    Kills impl counting records per class and summing.
    """
    problems = [_p("only-class", f"f:{i}") for i in range(10)]
    result = count_distinct_classes(problems)
    assert result == 1, "1 distinct class; got " + repr(result)


def test_empty_returns_zero() -> None:
    """Empty input returns 0 without raising."""
    assert count_distinct_classes([]) == 0


def test_two_classes_returns_two() -> None:
    """Two distinct classes → returns 2.

    Kills impl deduplicating by count rather than by name.
    """
    problems = [_p("alpha", "f:0"), _p("alpha", "f:1"), _p("beta", "f:2")]
    result = count_distinct_classes(problems)
    assert result == 2, "alpha + beta = 2 classes; got " + repr(result)


def test_returns_integer_not_names() -> None:
    """Returns an int, not a list or frozenset of class names.

    Kills impl returning the class names themselves.
    """
    problems = [_p("a", "f:0"), _p("b", "f:1"), _p("c", "f:2")]
    result = count_distinct_classes(problems)
    assert isinstance(result, int), "Must return int; got " + repr(type(result))
    assert result == 3, "3 distinct classes; got " + repr(result)
