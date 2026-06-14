"""Item 439: severity_balance_score() -- normalized severity balance ratio (2026-06-08).

``severity_balance_score(problems) -> float``:
Returns severity_entropy / log2(num_distinct_severities).
0.0 = maximally imbalanced, 1.0 = perfectly balanced.
Empty -> 1.0.  Single severity -> 1.0.  Pure; no I/O.

Discriminating tests -- each kills a plausible wrong implementation:

  1. PRIMARY DISC.: perfectly equal severities -> 1.0 (normalized max entropy).
     Kills impl returning raw entropy (would give log2(n) not 1.0).
  2. Single severity -> 1.0 (trivially balanced, not 0.0).
     Kills impl where single severity = 0 impurity = 0 balance.
  3. Empty -> 1.0 (vacuously balanced, not raise).
     Kills impl with unguarded log(0) or ZeroDivisionError.
  4. Unequal distribution -> value in (0, 1).
     Validates normalization is meaningful.
  5. Keyed on severity field (not class/fid).
     Kills impl reusing class_balance_score or finding_id_balance_score.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import (
    Problem,
    severity_balance_score,
)


def _p(cls: str, fid: str, sev: str) -> Problem:
    return Problem(problem_class=cls, finding_id=fid, severity=sev)


def test_equal_severities_returns_one() -> None:
    """Perfectly equal severity distribution -> 1.0.

    PRIMARY DISCRIMINATOR: kills impl returning raw entropy (log2(n)).
    Two equal severities -> H=1.0, max_H=log2(2)=1.0, score=1.0/1.0=1.0.
    """
    problems = [
        _p("cls", "f1", "HIGH"),
        _p("cls", "f2", "HIGH"),
        _p("cls", "f3", "LOW"),
        _p("cls", "f4", "LOW"),
    ]
    result = severity_balance_score(problems)
    assert isinstance(result, float), "Must return float; got " + repr(type(result))
    assert abs(result - 1.0) < 1e-9, "Equal severities -> 1.0; got " + repr(result)


def test_single_severity_returns_one() -> None:
    """Single severity -> 1.0 (trivially balanced)."""
    problems = [_p("a", "f1", "HIGH"), _p("b", "f2", "HIGH")]
    result = severity_balance_score(problems)
    assert abs(result - 1.0) < 1e-9, "Single severity -> 1.0; got " + repr(result)


def test_empty_returns_one() -> None:
    """Empty input returns 1.0, not ZeroDivisionError."""
    result = severity_balance_score([])
    assert result == 1.0, "Empty -> 1.0; got " + repr(result)
    assert isinstance(result, float)


def test_unequal_severities_in_unit_interval() -> None:
    """Unequal severity distribution -> score in (0, 1)."""
    problems = [
        _p("cls", "f1", "HIGH"),
        _p("cls", "f2", "HIGH"),
        _p("cls", "f3", "HIGH"),
        _p("cls", "f4", "LOW"),
    ]
    result = severity_balance_score(problems)
    assert 0.0 < result < 1.0, "Unequal -> (0, 1); got " + repr(result)


def test_keyed_on_severity_not_class() -> None:
    """Severity axis balance (not class axis).

    Two classes, one severity -> severity_balance=1.0 (trivially balanced),
    class_balance_score would also be 1.0 for equal classes.
    But with UNEQUAL classes and single severity: severity=1.0, class < 1.0.
    Kills impl reusing class_balance_score.
    """
    # 3 alpha, 1 beta (class imbalanced) but only one severity -> sev_balance=1.0
    problems = [
        _p("alpha", "f1", "HIGH"),
        _p("alpha", "f2", "HIGH"),
        _p("alpha", "f3", "HIGH"),
        _p("beta", "f4", "HIGH"),
    ]
    result = severity_balance_score(problems)
    # severity = only "HIGH" -> trivially balanced -> 1.0
    # class_balance_score would return < 1.0 (3:1 imbalance)
    assert abs(result - 1.0) < 1e-9, (
        "Single severity -> sev_balance=1.0 (not class_balance); got " + repr(result)
    )
