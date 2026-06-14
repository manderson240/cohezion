"""Item 409: min_problems_in_any_class() — minimum record count in any class (2026-06-08).

``min_problems_in_any_class(problems) -> int``:
Returns the minimum value in the problem_class_histogram.
Empty -> 0.  Pure; no I/O.

Discriminating tests — each kills a plausible wrong implementation:

  1. PRIMARY DISC.: returns MINIMUM count (not class name, not maximum).
     Kills impl reusing max_problems_in_any_class logic.
  2. Empty input -> 0 (not ValueError from min([])).
     Kills impl with unguarded min() on empty.
  3. All classes equal -> that count.
     Distinguishes min from any other statistic.
  4. Multiple classes with different counts -> minimum count.
     Validates with alpha=3, beta=1, gamma=2 -> 1.
  5. Single class -> its record count.
     Validates single-class edge case.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import (
    Problem,
    min_problems_in_any_class,
)


def _p(cls: str, fid: str = "f") -> Problem:
    return Problem(problem_class=cls, finding_id=fid)


def test_returns_minimum_count_not_class_name() -> None:
    """Returns the minimum count integer, not class name.

    PRIMARY DISCRIMINATOR: kills impl returning class name or max.
    alpha=3, beta=1 -> min=1 (beta).
    """
    problems = [_p("alpha"), _p("alpha"), _p("alpha"), _p("beta")]
    result = min_problems_in_any_class(problems)
    assert isinstance(result, int), "Must return int; got " + repr(type(result))
    assert result == 1, "beta has 1 record (min); got " + repr(result)


def test_empty_returns_zero() -> None:
    """Empty input returns 0, not ValueError from min([])."""
    result = min_problems_in_any_class([])
    assert result == 0, "Empty -> 0; got " + repr(result)
    assert isinstance(result, int)


def test_equal_distribution_returns_count_per_class() -> None:
    """All classes equal count -> that count.

    Distinguishes min from other statistics.
    """
    problems = [_p("a"), _p("a"), _p("b"), _p("b"), _p("c"), _p("c")]
    result = min_problems_in_any_class(problems)
    assert result == 2, "Each class has 2 records; min=2; got " + repr(result)


def test_multiple_classes_returns_minimum_count() -> None:
    """Multiple classes with different counts -> minimum count.

    alpha=3, beta=1, gamma=2 -> min=1.
    """
    problems = [
        _p("alpha"),
        _p("alpha"),
        _p("alpha"),
        _p("beta"),
        _p("gamma"),
        _p("gamma"),
    ]
    result = min_problems_in_any_class(problems)
    assert result == 1, "beta has 1 (min); got " + repr(result)


def test_single_class_returns_its_record_count() -> None:
    """Single class -> its record count."""
    problems = [_p("only", str(i)) for i in range(3)]
    result = min_problems_in_any_class(problems)
    assert result == 3, "1 class with 3 records -> 3; got " + repr(result)
