"""Item 483: fid_total_severity_score() -- weighted severity aggregation per fid (2026-06-08).

``fid_total_severity_score(problems, finding_id, weights) -> float``:
Returns the total score for a finding_id by summing weights[p.severity] for each
matching Problem.  Symmetric to class_total_severity_score on the fid axis.
Unrecognised severities contribute 0.  Empty/absent fid -> 0.0.  Pure; no I/O.

Discriminating tests -- each kills a plausible wrong implementation:

  1. PRIMARY DISC.: weighted sum, not plain count.
     fid_a: HIGH x2 (weight 3.0), LOW x1 (weight 1.0) -> 7.0 not 3.
     Kills impl returning plain problem count.
  2. Unknown severity contributes 0 (not raise).
     Kills impl raising KeyError.
  3. Absent fid -> 0.0 (not raise).
     Kills impl raising on absent fid.
  4. Returns float (not int).
     Kills impl returning count int.
  5. Empty input -> 0.0.
     Kills impl with unguarded access.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import (
    Problem,
    fid_total_severity_score,
)


def _p(cls: str, fid: str, sev: str) -> Problem:
    return Problem(problem_class=cls, finding_id=fid, severity=sev)


def test_weighted_sum_not_plain_count() -> None:
    """PRIMARY DISC.: weighted sum (fid_a: HIGH x2 weight=3.0, LOW x1 weight=1.0 -> 7.0).

    Kills impl returning plain count (3 not 7.0).
    """
    problems = [
        _p("ClassA", "fid_a", "HIGH"),
        _p("ClassB", "fid_a", "HIGH"),
        _p("ClassC", "fid_a", "LOW"),
        _p("ClassA", "fid_b", "HIGH"),
    ]
    weights = {"HIGH": 3.0, "LOW": 1.0}
    result = fid_total_severity_score(problems, "fid_a", weights)
    assert result == 7.0, "2*3.0 + 1*1.0 = 7.0; got " + repr(result)


def test_unknown_severity_contributes_zero() -> None:
    """Unrecognised severity contributes 0 (not raise)."""
    problems = [
        _p("ClassA", "fid_a", "HIGH"),
        _p("ClassB", "fid_a", "UNKNOWN_SEV"),
    ]
    weights = {"HIGH": 5.0}
    result = fid_total_severity_score(problems, "fid_a", weights)
    assert result == 5.0, "HIGH=5.0, UNKNOWN_SEV=0.0 -> 5.0; got " + repr(result)


def test_absent_fid_returns_zero_float() -> None:
    """Absent fid -> 0.0 (not raise)."""
    problems = [_p("ClassA", "fid_a", "HIGH")]
    weights = {"HIGH": 3.0}
    result = fid_total_severity_score(problems, "NONEXISTENT_FID", weights)
    assert result == 0.0, "Absent fid -> 0.0; got " + repr(result)


def test_returns_float_not_int() -> None:
    """Result is float, not int."""
    problems = [_p("ClassA", "fid_a", "HIGH")]
    weights = {"HIGH": 2.0}
    result = fid_total_severity_score(problems, "fid_a", weights)
    assert isinstance(result, float), "Must return float; got " + repr(type(result))
    assert result == 2.0


def test_empty_input_returns_zero() -> None:
    """Empty input -> 0.0 (not raise)."""
    result = fid_total_severity_score([], "fid_a", {"HIGH": 3.0})
    assert result == 0.0, "Empty -> 0.0; got " + repr(result)
