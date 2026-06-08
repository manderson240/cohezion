"""Item 426: class_balance_score() — normalized class balance ratio (2026-06-08).

``class_balance_score(problems) -> float``:
Returns class_entropy / log2(num_distinct_classes).
0.0 = maximally imbalanced, 1.0 = perfectly balanced.
Empty -> 1.0.  Single class -> 1.0.  Pure; no I/O.

Discriminating tests -- each kills a plausible wrong implementation:

  1. PRIMARY DISC.: perfectly equal classes -> 1.0 (normalized max entropy).
     Kills impl returning raw entropy (would give log2(n) not 1.0).
  2. Single class -> 1.0 (trivially balanced, not 0.0).
     Kills impl where single class = 0 impurity = 0 balance.
  3. Empty -> 1.0 (vacuously balanced, not raise).
     Kills impl with unguarded log(0) or ZeroDivisionError.
  4. Unequal distribution -> value in (0, 1).
     Validates normalization is meaningful.
  5. Returns float in [0.0, 1.0].
     Kills impl returning values outside this range.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import (
    Problem,
    class_balance_score,
)


def _p(cls: str, fid: str = "f") -> Problem:
    return Problem(problem_class=cls, finding_id=fid)


def test_equal_distribution_returns_one() -> None:
    """Perfectly equal class distribution -> 1.0.

    PRIMARY DISCRIMINATOR: kills impl returning raw entropy (log2(n)).
    Two equal classes -> H=1.0, max_H=log2(2)=1.0, score=1.0/1.0=1.0.
    """
    problems = [_p("a"), _p("a"), _p("b"), _p("b")]
    result = class_balance_score(problems)
    assert isinstance(result, float), "Must return float; got " + repr(type(result))
    assert abs(result - 1.0) < 1e-9, "Equal classes -> 1.0; got " + repr(result)


def test_single_class_returns_one() -> None:
    """Single class -> 1.0 (trivially balanced, no disorder to speak of)."""
    problems = [_p("only"), _p("only"), _p("only")]
    result = class_balance_score(problems)
    assert abs(result - 1.0) < 1e-9, "Single class -> 1.0; got " + repr(result)


def test_empty_returns_one() -> None:
    """Empty input returns 1.0, not ZeroDivisionError."""
    result = class_balance_score([])
    assert result == 1.0, "Empty -> 1.0; got " + repr(result)
    assert isinstance(result, float)


def test_unequal_distribution_returns_value_between_zero_and_one() -> None:
    """Unequal distribution -> score in (0, 1)."""
    # 3 records in 'big', 1 in 'small' — unequal, should be < 1.0
    problems = [_p("big"), _p("big"), _p("big"), _p("small")]
    result = class_balance_score(problems)
    assert 0.0 < result < 1.0, "Unequal -> (0, 1); got " + repr(result)


def test_returns_float_in_unit_interval() -> None:
    """Returns float in [0.0, 1.0] for any valid input."""
    # Four equal classes -> max balance -> 1.0
    problems = [_p("a"), _p("b"), _p("c"), _p("d")]
    result = class_balance_score(problems)
    assert isinstance(result, float)
    assert 0.0 <= result <= 1.0, "Score must be in [0, 1]; got " + repr(result)
    assert abs(result - 1.0) < 1e-9, "Four equal classes -> 1.0; got " + repr(result)
