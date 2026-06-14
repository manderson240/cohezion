"""Item 381: labelled_fraction() -- fraction of problems with a severity label (2026-06-08).

``labelled_fraction(problems) -> float``:
Returns labelled_count / total_count as a float in [0.0, 1.0].
1.0 when all problems are labelled; 0.0 when none are.
Empty input -> 0.0 (no ZeroDivisionError).  Pure; no I/O.

Discriminating tests:

  1. PRIMARY DISC.: returns a SINGLE FLOAT in [0, 1], not a dict or count.
     Kills impl returning labelled_problem_count or severity_coverage_ratio.
  2. Empty input returns 0.0, not ZeroDivisionError or 1.0.
     Kills impl with unguarded division.
  3. All-labelled returns 1.0.
     Kills impl with off-by-one.
  4. None-labelled returns 0.0.
     Kills impl treating unlabelled '' as labelled.
  5. Mixed case: correct ratio computed.
     Kills impl that counts wrong (e.g. distinct IDs instead of records).
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import (
    Problem,
    labelled_fraction,
)


def _p(cls: str, fid: str, sev: str = "") -> Problem:
    return Problem(problem_class=cls, finding_id=fid, severity=sev)


def test_returns_single_float_not_dict() -> None:
    """Returns a single float, not a dict or integer count.

    PRIMARY DISCRIMINATOR: kills impl returning severity_coverage_ratio or labelled_problem_count.
    """
    problems = [_p("sec", "CVE-001", "HIGH"), _p("style", "STY-001")]
    result = labelled_fraction(problems)
    assert isinstance(result, float), "Must return float; got " + repr(type(result))
    assert 0.0 <= result <= 1.0, "Must be in [0, 1]; got " + repr(result)
    assert abs(result - 0.5) < 1e-9, "1 labelled / 2 total = 0.5; got " + repr(result)


def test_empty_returns_zero_not_error() -> None:
    """Empty input returns 0.0 without ZeroDivisionError.

    Kills impl with unguarded division.
    """
    result = labelled_fraction([])
    assert result == 0.0, "Empty -> 0.0; got " + repr(result)
    assert isinstance(result, float), "Must be float, not int; got " + repr(type(result))


def test_all_labelled_returns_one() -> None:
    """All problems labelled -> 1.0.

    Kills impl with off-by-one in denominator.
    """
    problems = [_p("a", "f:0", "HIGH"), _p("b", "f:1", "LOW"), _p("c", "f:2", "CRITICAL")]
    result = labelled_fraction(problems)
    assert abs(result - 1.0) < 1e-9, "All labelled -> 1.0; got " + repr(result)


def test_none_labelled_returns_zero() -> None:
    """All problems unlabelled -> 0.0.

    Kills impl treating empty severity '' as labelled.
    """
    problems = [_p("a", "f:0"), _p("b", "f:1"), _p("c", "f:2")]
    result = labelled_fraction(problems)
    assert result == 0.0, "All unlabelled -> 0.0; got " + repr(result)


def test_mixed_ratio_correct() -> None:
    """3 labelled out of 5 total = 0.6 (counts records, not distinct IDs)."""
    problems = [
        _p("a", "f:0", "HIGH"),
        _p("b", "f:1", "LOW"),
        _p("c", "f:2", "MEDIUM"),
        _p("d", "f:3"),  # unlabelled
        _p("e", "f:4"),  # unlabelled
    ]
    result = labelled_fraction(problems)
    assert abs(result - 0.6) < 1e-9, "3 of 5 = 0.6; got " + repr(result)
