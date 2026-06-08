"""Item 351: severity_ratio() -- fraction of ALL problems at a given severity (2026-06-08).

``severity_ratio(problems, severity) -> float``:
Returns count(severity) / len(problems).  Denominator is ALL problems
(labelled + unlabelled), NOT just labelled.  Unknown severity -> 0.0.
Empty -> 0.0.  Result in [0.0, 1.0].  Pure; no I/O.

Discriminating tests:

  1. PRIMARY DISC.: denominator is ALL problems not just labelled.
     Kills impl dividing by labelled-only count (gives inflated ratio).
  2. Returns float in [0.0, 1.0].
     Kills impl returning percentage 0-100.
  3. Unknown severity returns 0.0 not an error.
     Kills impl raising KeyError.
  4. Empty problems returns 0.0 (no ZeroDivisionError).
     Kills impl dividing by zero.
  5. Correct arithmetic: 2 HIGH out of 5 total = 0.4.
     Kills off-by-one or integer division.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import (
    Problem,
    severity_ratio,
)


def _ps(cls: str, idx: int, sev: str) -> Problem:
    return Problem(problem_class=cls, finding_id=f"{cls}:{idx}", severity=sev)


def _p(cls: str, idx: int) -> Problem:
    return Problem(problem_class=cls, finding_id=f"{cls}:{idx}")


def test_denominator_is_all_problems_not_just_labelled() -> None:
    """Denominator includes unlabelled problems.

    PRIMARY DISCRIMINATOR: kills impl dividing by labelled-count only.
    2 HIGH, 1 unlabelled, total=3 -> 2/3 not 2/2=1.0.
    """
    problems = [_ps("a", 0, "HIGH"), _ps("b", 0, "HIGH"), _p("c", 0)]
    result = severity_ratio(problems, "HIGH")
    assert abs(result - 2 / 3) < 1e-9, "2/3 total; got " + repr(result)
    assert result < 1.0, "Must be < 1.0 (unlabelled in denominator); got " + repr(result)


def test_returns_float_in_unit_interval() -> None:
    """Returns float in [0.0, 1.0], not percentage.

    Kills impl returning 0-100 range.
    """
    problems = [_ps("a", 0, "HIGH"), _p("b", 0)]
    result = severity_ratio(problems, "HIGH")
    assert isinstance(result, float), "Must return float; got " + repr(type(result))
    assert 0.0 <= result <= 1.0, "Must be in [0,1]; got " + repr(result)


def test_unknown_severity_returns_zero() -> None:
    """Unknown severity returns 0.0 without raising."""
    problems = [_ps("a", 0, "HIGH")]
    result = severity_ratio(problems, "UNKNOWN_SEV")
    assert result == 0.0, "unknown -> 0.0; got " + repr(result)


def test_empty_problems_returns_zero() -> None:
    """Empty list returns 0.0 (no ZeroDivisionError)."""
    assert severity_ratio([], "HIGH") == 0.0


def test_correct_fraction_arithmetic() -> None:
    """2 HIGH out of 5 total = 0.4."""
    problems = (
        [_ps("a", i, "HIGH") for i in range(2)]
        + [_ps("b", i, "LOW") for i in range(2)]
        + [_p("c", 0)]
    )
    result = severity_ratio(problems, "HIGH")
    assert abs(result - 0.4) < 1e-9, "2/5 = 0.4; got " + repr(result)
