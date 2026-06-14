"""Item 408: max_problems_in_any_class() — maximum record count in any single class (2026-06-08).

``max_problems_in_any_class(problems) -> int``:
Returns the maximum class record count from the class histogram.
Empty -> 0 (no ValueError from max()).  Pure; no I/O.

Discriminating tests — each kills a plausible wrong implementation:

  1. PRIMARY DISC.: returns INTEGER max count (not class name, not total).
     Kills impl returning the class name with highest count.
  2. Empty input -> 0 (no ValueError).
     Kills impl calling max() without guard on empty sequence.
  3. All classes have equal counts -> that count (not 1 or total).
     Kills impl returning number of classes.
  4. Single record -> 1.
     Edge case: trivially correct.
  5. Max is NOT total (multiple classes) -> correct max count.
     Kills impl returning len(problems).
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import (
    Problem,
    max_problems_in_any_class,
)


def _p(cls: str, fid: str = "f") -> Problem:
    return Problem(problem_class=cls, finding_id=fid)


def test_returns_integer_max_count() -> None:
    """Returns integer maximum class count, not class name.

    PRIMARY DISCRIMINATOR: kills impl returning class name.
    """
    problems = [_p("alpha"), _p("alpha"), _p("alpha"), _p("beta"), _p("beta")]
    result = max_problems_in_any_class(problems)
    assert isinstance(result, int), "Must return int; got " + repr(type(result))
    assert result == 3, "alpha has 3 records (max); got " + repr(result)


def test_empty_returns_zero_no_valueerror() -> None:
    """Empty input returns 0, not ValueError.

    Kills impl calling max() without guard.
    """
    result = max_problems_in_any_class([])
    assert result == 0, "Empty -> 0; got " + repr(result)
    assert isinstance(result, int)


def test_equal_distribution_returns_count_per_class() -> None:
    """Equal class counts -> that count (not 1 or number of classes).

    Kills impl returning number of classes.
    """
    problems = [_p("a"), _p("a"), _p("b"), _p("b"), _p("c"), _p("c")]
    result = max_problems_in_any_class(problems)
    assert result == 2, "Each class has 2 records; max=2; got " + repr(result)


def test_single_record_returns_one() -> None:
    """Single record -> 1."""
    assert max_problems_in_any_class([_p("only")]) == 1


def test_max_is_not_total_record_count() -> None:
    """Max is the heaviest class, not len(problems).

    Kills impl returning len(problems).
    """
    problems = [_p("big"), _p("big"), _p("small")]
    result = max_problems_in_any_class(problems)
    assert result == 2, "big has 2, max=2; total=3; got " + repr(result)
    assert result != len(problems), "Must NOT return len(problems)"
