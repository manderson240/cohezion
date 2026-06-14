"""Item 451: severity_labelling_ratio() -- fraction of records with non-empty severity (2026-06-08).

``severity_labelling_ratio(problems) -> float``:
Returns the fraction of Problem records whose severity field is non-empty.
0.0 for empty input.  Result in [0.0, 1.0].  Pure; no I/O.

Discriminating tests -- each kills a plausible wrong implementation:

  1. PRIMARY DISC.: scalar float (not dict) -- distinct from severity_coverage_ratio().
     Kills impl reusing severity_coverage_ratio which returns dict[str, float].
  2. 1.0 when ALL records are labelled (fully covered).
     Kills impl returning fraction of distinct severities over total possible.
  3. 0.0 when ALL records have empty severity (unlabelled scan).
     Kills impl that ignores empty-severity records in denominator.
  4. Partial labelling returns correct float in (0, 1).
     Validates the division: labelled_count / total_count.
  5. 0.0 on empty input (not raise, not ZeroDivisionError).
     Kills impl with unguarded division.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import (
    Problem,
    severity_labelling_ratio,
)


def _p(cls: str, fid: str, sev: str) -> Problem:
    return Problem(problem_class=cls, finding_id=fid, severity=sev)


def test_returns_scalar_float_not_dict() -> None:
    """PRIMARY DISC.: returns float, not dict.

    severity_coverage_ratio() returns dict[str, float] -- severity_labelling_ratio
    returns a single scalar float.  All records have severity='HIGH'.
    Kills impl reusing severity_coverage_ratio.
    """
    problems = [
        _p("BUG", "f1", "HIGH"),
        _p("BUG", "f2", "HIGH"),
    ]
    result = severity_labelling_ratio(problems)
    assert isinstance(result, float), "Must return float; got " + repr(type(result))
    assert abs(result - 1.0) < 1e-9, "All labelled -> 1.0; got " + repr(result)


def test_all_labelled_returns_one() -> None:
    """All records have non-empty severity -> 1.0."""
    problems = [_p("c", f"f{i}", "MED") for i in range(5)]
    result = severity_labelling_ratio(problems)
    assert abs(result - 1.0) < 1e-9, "All labelled -> 1.0; got " + repr(result)


def test_all_unlabelled_returns_zero() -> None:
    """All records have severity='' -> 0.0."""
    problems = [_p("c", f"f{i}", "") for i in range(3)]
    result = severity_labelling_ratio(problems)
    assert abs(result - 0.0) < 1e-9, "All unlabelled -> 0.0; got " + repr(result)


def test_partial_labelling_correct_ratio() -> None:
    """3 labelled out of 5 total -> 3/5 = 0.6."""
    problems = [
        _p("c", "f1", "HIGH"),
        _p("c", "f2", "HIGH"),
        _p("c", "f3", "HIGH"),
        _p("c", "f4", ""),
        _p("c", "f5", ""),
    ]
    result = severity_labelling_ratio(problems)
    assert abs(result - 0.6) < 1e-9, "3/5=0.6; got " + repr(result)


def test_empty_returns_zero() -> None:
    """Empty input returns 0.0 (no ZeroDivisionError)."""
    result = severity_labelling_ratio([])
    assert isinstance(result, float)
    assert abs(result - 0.0) < 1e-9, "Empty -> 0.0; got " + repr(result)
