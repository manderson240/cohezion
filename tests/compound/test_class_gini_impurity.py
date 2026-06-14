"""Item 425: class_gini_impurity() — Gini impurity of the class distribution (2026-06-08).

``class_gini_impurity(problems) -> float``:
Returns G = 1 - sum(p^2) where p = class_count / total_count.
Single class -> 0.0 (pure).  Two equal classes -> 0.5.  Empty -> 0.0.  Pure; no I/O.

Discriminating tests -- each kills a plausible wrong implementation:

  1. PRIMARY DISC.: two equal classes -> 0.5 (NOT 1.0 as entropy gives).
     Kills impl reusing class_entropy formula (log-based).
  2. Single class -> 0.0 (perfect purity).
     Kills impl returning > 0 for single class.
  3. Empty -> 0.0 (not ZeroDivisionError).
     Kills impl with unguarded division.
  4. Returns float in [0.0, 1.0).
     Kills impl returning int or values >= 1.
  5. Unequal distribution -> correct Gini value.
     Validates core formula (not entropy formula).
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import (
    Problem,
    class_gini_impurity,
)


def _p(cls: str, fid: str = "f") -> Problem:
    return Problem(problem_class=cls, finding_id=fid)


def test_two_equal_classes_returns_half() -> None:
    """Two equal classes -> G = 0.5 (NOT 1.0).

    PRIMARY DISCRIMINATOR: kills impl reusing entropy formula (which gives 1.0).
    G = 1 - (0.5^2 + 0.5^2) = 1 - 0.5 = 0.5.
    """
    problems = [_p("a"), _p("b")]
    result = class_gini_impurity(problems)
    assert isinstance(result, float), "Must return float; got " + repr(type(result))
    assert abs(result - 0.5) < 1e-9, "Two equal classes -> 0.5; got " + repr(result)


def test_single_class_returns_zero() -> None:
    """Single class -> G = 0.0 (pure node, no impurity)."""
    problems = [_p("only"), _p("only"), _p("only")]
    result = class_gini_impurity(problems)
    assert abs(result - 0.0) < 1e-9, "Single class -> 0.0; got " + repr(result)


def test_empty_returns_zero() -> None:
    """Empty input returns 0.0, not ZeroDivisionError."""
    result = class_gini_impurity([])
    assert result == 0.0, "Empty -> 0.0; got " + repr(result)
    assert isinstance(result, float)


def test_returns_float_in_unit_interval() -> None:
    """Returns float in [0, 1) — Gini impurity is bounded."""
    problems = [_p("a"), _p("a"), _p("b"), _p("c")]
    result = class_gini_impurity(problems)
    assert isinstance(result, float), "Must return float; got " + repr(type(result))
    assert 0.0 <= result < 1.0, "Gini must be in [0, 1); got " + repr(result)


def test_unequal_distribution_correct_gini() -> None:
    """Unequal distribution returns correct Gini impurity.

    2 records 'big', 1 record 'small'. p_big=2/3, p_small=1/3.
    G = 1 - ((2/3)^2 + (1/3)^2) = 1 - (4/9 + 1/9) = 1 - 5/9 = 4/9 ≈ 0.4444.
    """
    problems = [_p("big"), _p("big"), _p("small")]
    result = class_gini_impurity(problems)
    expected = 4 / 9
    assert abs(result - expected) < 1e-9, "G=4/9; got " + repr(result)
