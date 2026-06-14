"""Item 405: unique_classes_count() — distinct problem_class cardinality (2026-06-08).

``unique_classes_count(problems) -> int``:
Returns the count of distinct problem_class values across all records.
Each distinct class counted once, regardless of record count.
Empty -> 0.  Pure; no I/O.

Discriminating tests — each kills a plausible wrong implementation:

  1. PRIMARY DISC.: returns INTEGER count (not frozenset, not set).
     Kills impl returning distinct_problem_classes().
  2. Each distinct class counted once, not once per record.
     Kills impl returning len(problems).
  3. Empty input -> 0.
     Kills impl raising on empty.
  4. Single class with many records -> 1.
     Kills impl using len(problems) directly.
  5. Result matches len(distinct_problem_classes(problems)).
     Validates composition invariant.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import (
    Problem,
    unique_classes_count,
)


def _p(cls: str, fid: str = "f") -> Problem:
    return Problem(problem_class=cls, finding_id=fid)


def test_returns_integer_not_frozenset() -> None:
    """Returns an integer, not frozenset or set.

    PRIMARY DISCRIMINATOR: kills impl returning distinct_problem_classes().
    """
    problems = [_p("alpha"), _p("beta"), _p("alpha")]
    result = unique_classes_count(problems)
    assert isinstance(result, int), "Must return int; got " + repr(type(result))
    assert result == 2, "2 distinct classes (alpha, beta); got " + repr(result)


def test_each_class_counted_once_not_per_record() -> None:
    """Each class counted once, not once per record.

    Kills impl returning len(problems).
    """
    problems = [_p("alpha"), _p("alpha"), _p("alpha")]
    result = unique_classes_count(problems)
    assert result == 1, "Only 1 distinct class; got " + repr(result)
    assert result != len(problems), "Must NOT return len(problems)"


def test_empty_returns_zero() -> None:
    """Empty input returns 0."""
    assert unique_classes_count([]) == 0


def test_single_class_many_records_returns_one() -> None:
    """Single class with many records returns 1."""
    problems = [_p("only", str(i)) for i in range(10)]
    assert unique_classes_count(problems) == 1


def test_matches_frozenset_of_problem_classes() -> None:
    """Result equals len of the set of distinct class names.

    Validates composition invariant against manual frozenset computation.
    """
    problems = [_p("a"), _p("b"), _p("c"), _p("a"), _p("b")]
    result = unique_classes_count(problems)
    expected = len(frozenset(p.problem_class for p in problems))
    assert result == expected, "Must equal manual frozenset cardinality; got " + repr(result)
