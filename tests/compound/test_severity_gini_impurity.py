"""Item 438: severity_gini_impurity() -- Gini impurity of the severity distribution (2026-06-08).

``severity_gini_impurity(problems) -> float``:
Returns G = 1 - sum(p^2) where p = severity_count / total.
Single severity -> 0.0 (pure).  Two equal severities -> 0.5.  Empty -> 0.0.  Pure; no I/O.

Discriminating tests -- each kills a plausible wrong implementation:

  1. PRIMARY DISC.: two equal severities -> 0.5 (NOT 1.0 as entropy gives).
     Kills impl reusing severity_entropy (log-based formula).
  2. Single severity -> 0.0 (perfect purity).
     Kills impl returning > 0 for single severity.
  3. Empty -> 0.0 (not ZeroDivisionError).
     Kills impl with unguarded division.
  4. Keyed on severity (not class/fid).
     Kills impl reusing class_gini_impurity on wrong field.
  5. Unequal distribution -> correct Gini value.
     Validates core formula precision.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import (
    Problem,
    severity_gini_impurity,
)


def _p(cls: str, fid: str, sev: str) -> Problem:
    return Problem(problem_class=cls, finding_id=fid, severity=sev)


def test_two_equal_severities_returns_half() -> None:
    """Two equal severities -> G = 0.5 (NOT 1.0).

    PRIMARY DISCRIMINATOR: kills impl reusing entropy formula.
    G = 1 - (0.5^2 + 0.5^2) = 1 - 0.5 = 0.5.
    """
    problems = [_p("cls", "f1", "HIGH"), _p("cls", "f2", "LOW")]
    result = severity_gini_impurity(problems)
    assert isinstance(result, float), "Must return float; got " + repr(type(result))
    assert abs(result - 0.5) < 1e-9, "Two equal severities -> 0.5; got " + repr(result)


def test_single_severity_returns_zero() -> None:
    """Single severity -> G = 0.0 (pure)."""
    problems = [_p("a", "f1", "HIGH"), _p("b", "f2", "HIGH")]
    result = severity_gini_impurity(problems)
    assert abs(result - 0.0) < 1e-9, "Single severity -> 0.0; got " + repr(result)


def test_empty_returns_zero() -> None:
    """Empty input returns 0.0, not ZeroDivisionError."""
    result = severity_gini_impurity([])
    assert result == 0.0, "Empty -> 0.0; got " + repr(result)
    assert isinstance(result, float)


def test_keyed_on_severity_not_class() -> None:
    """Gini is over severity distribution, not class distribution.

    Two classes but one severity -> severity Gini = 0.0, class Gini = 0.5.
    Kills impl reusing class_gini_impurity on wrong field.
    """
    problems = [
        _p("alpha", "f1", "HIGH"),
        _p("beta", "f2", "HIGH"),
    ]
    result = severity_gini_impurity(problems)
    # One severity ('HIGH') -> Gini = 0.0
    # class_gini_impurity would return 0.5 (two equal classes)
    assert abs(result - 0.0) < 1e-9, (
        "Single severity 'HIGH' -> Gini=0.0 (not class Gini=0.5); got " + repr(result)
    )


def test_unequal_severity_distribution_correct_gini() -> None:
    """Unequal severity distribution returns correct Gini.

    HIGH=2/3, LOW=1/3.
    G = 1 - ((2/3)^2 + (1/3)^2) = 1 - (4/9 + 1/9) = 4/9.
    """
    problems = [
        _p("cls", "f1", "HIGH"),
        _p("cls", "f2", "HIGH"),
        _p("cls", "f3", "LOW"),
    ]
    result = severity_gini_impurity(problems)
    expected = 4 / 9
    assert abs(result - expected) < 1e-9, "G=4/9; got " + repr(result)
