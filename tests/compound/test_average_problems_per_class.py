"""Item 407: average_problems_per_class() — mean record count per class (2026-06-08).

``average_problems_per_class(problems) -> float``:
Returns total records / distinct class count as a float.
Empty -> 0.0 (no ZeroDivisionError).  Pure; no I/O.

Discriminating tests — each kills a plausible wrong implementation:

  1. PRIMARY DISC.: returns a FLOAT, not int.
     Kills impl returning integer division result.
  2. Empty input -> 0.0 (not ZeroDivisionError).
     Kills impl with unguarded division.
  3. Single class with N records -> float(N).
     Validates single-class edge case.
  4. Two classes with unequal counts -> correct float average.
     Kills impl returning max count or total count.
  5. Computes records/classes (not records/records or classes/classes).
     Kills impl using wrong denominator.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import (
    Problem,
    average_problems_per_class,
)


def _p(cls: str, fid: str = "f") -> Problem:
    return Problem(problem_class=cls, finding_id=fid)


def test_returns_float_not_int() -> None:
    """Returns float, not int.

    PRIMARY DISCRIMINATOR: kills impl using integer division.
    """
    problems = [_p("alpha"), _p("alpha"), _p("beta")]
    result = average_problems_per_class(problems)
    assert isinstance(result, float), "Must return float; got " + repr(type(result))
    assert abs(result - 1.5) < 1e-9, "3 records / 2 classes = 1.5; got " + repr(result)


def test_empty_returns_zero_float() -> None:
    """Empty input returns 0.0, not ZeroDivisionError."""
    result = average_problems_per_class([])
    assert result == 0.0, "Empty -> 0.0; got " + repr(result)
    assert isinstance(result, float)


def test_single_class_returns_record_count_as_float() -> None:
    """Single class with N records -> float(N)."""
    problems = [_p("only", str(i)) for i in range(4)]
    result = average_problems_per_class(problems)
    assert abs(result - 4.0) < 1e-9, "4 records / 1 class = 4.0; got " + repr(result)


def test_two_classes_unequal_counts_correct_average() -> None:
    """Two classes with unequal counts -> correct average.

    Kills impl returning max count or total count.
    alpha=3, beta=1 -> (3+1)/2 = 2.0
    """
    problems = [_p("alpha"), _p("alpha"), _p("alpha"), _p("beta")]
    result = average_problems_per_class(problems)
    assert abs(result - 2.0) < 1e-9, "4 records / 2 classes = 2.0; got " + repr(result)


def test_computes_records_divided_by_classes() -> None:
    """Computes total_records / distinct_classes, not any other ratio.

    alpha=2, beta=2, gamma=2 -> 6/3 = 2.0
    """
    problems = [_p("alpha"), _p("alpha"), _p("beta"), _p("beta"), _p("gamma"), _p("gamma")]
    result = average_problems_per_class(problems)
    assert abs(result - 2.0) < 1e-9, "6 records / 3 classes = 2.0; got " + repr(result)
