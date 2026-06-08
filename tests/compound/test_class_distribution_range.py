"""Item 410: class_distribution_range() — spread between max and min class counts (2026-06-08).

``class_distribution_range(problems) -> int``:
Returns max_problems_in_any_class - min_problems_in_any_class.
Empty -> 0.  All-equal distribution -> 0.  Pure; no I/O.

Discriminating tests -- each kills a plausible wrong implementation:

  1. PRIMARY DISC.: returns INTEGER spread (not the pair (max, min)).
     Kills impl returning a tuple.
  2. All-equal distribution -> 0 (range of uniform dist is 0).
     Kills impl always returning max count.
  3. Empty -> 0 (not ZeroDivisionError or ValueError).
     Kills impl with unguarded min/max.
  4. Uneven distribution -> correct max-min difference.
     Kills impl returning max/min ratio.
  5. Single class -> 0 (max == min == record count).
     Edge case: max - min = count - count = 0.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import (
    Problem,
    class_distribution_range,
)


def _p(cls: str, fid: str = "f") -> Problem:
    return Problem(problem_class=cls, finding_id=fid)


def test_returns_integer_spread() -> None:
    """Returns integer spread (max - min), not tuple or float.

    PRIMARY DISCRIMINATOR: kills impl returning (max, min) tuple.
    """
    problems = [_p("big"), _p("big"), _p("big"), _p("small")]
    result = class_distribution_range(problems)
    assert isinstance(result, int), "Must return int; got " + repr(type(result))
    assert result == 2, "big=3, small=1, range=2; got " + repr(result)


def test_uniform_distribution_returns_zero() -> None:
    """All-equal class counts -> 0 (range of uniform dist is 0).

    Kills impl returning max count.
    """
    problems = [_p("a"), _p("a"), _p("b"), _p("b"), _p("c"), _p("c")]
    result = class_distribution_range(problems)
    assert result == 0, "All classes have 2 records; range=0; got " + repr(result)


def test_empty_returns_zero() -> None:
    """Empty input -> 0, not ValueError."""
    result = class_distribution_range([])
    assert result == 0, "Empty -> 0; got " + repr(result)
    assert isinstance(result, int)


def test_uneven_distribution_correct_difference() -> None:
    """Returns max - min, not max / min or any other ratio."""
    # heavy=5, light=1 -> range=4 (not 5.0 or 5/1=5)
    problems = [_p("heavy", str(i)) for i in range(5)] + [_p("light")]
    result = class_distribution_range(problems)
    assert result == 4, "5-1=4; got " + repr(result)


def test_single_class_returns_zero() -> None:
    """Single class -> 0 (max == min == record count -> range = 0)."""
    problems = [_p("only"), _p("only"), _p("only")]
    result = class_distribution_range(problems)
    assert result == 0, "Single class: max=min=3, range=0; got " + repr(result)
