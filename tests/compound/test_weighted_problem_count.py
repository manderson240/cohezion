"""Item 503: weighted_problem_count() -- global scalar total weight-load (2026-06-08).

``weighted_problem_count(problems, weights) -> float``:
Returns the sum of weights.get(p.severity, 0.0) across ALL Problem records
regardless of class or fid.  The global scalar cost of the entire scan.
0.0 for empty.  Pure; no I/O.

Discriminating tests -- each kills a plausible wrong implementation:

  1. PRIMARY DISC.: returns a float (scalar), not a dict.
     Kills impl returning all_severity_scores which is dict[str, float].
  2. Sums across ALL records regardless of class or fid.
     Kills impl returning only first class's total, or distinct count.
  3. Unknown severity contributes 0.0 (not raise, not 1.0).
     Kills impl raising KeyError or using a non-zero default.
  4. Empty input -> 0.0 (not raise).
     Kills impl without empty guard.
  5. Multiple records at same severity each contribute their weight.
     Kills impl that counts distinct severities instead of records.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import (
    Problem,
    weighted_problem_count,
)


def _p(cls: str, fid: str, sev: str) -> Problem:
    return Problem(problem_class=cls, finding_id=fid, severity=sev)


def test_returns_float_not_dict() -> None:
    """PRIMARY DISC.: returns float scalar, not dict.

    Kills impl returning all_severity_scores (dict[str, float]).
    """
    problems = [
        _p("ClassA", "f1", "HIGH"),
        _p("ClassB", "f2", "LOW"),
    ]
    weights = {"HIGH": 5.0, "LOW": 1.0}
    result = weighted_problem_count(problems, weights)
    assert isinstance(result, float), "Must return float; got " + repr(type(result))
    assert result == 6.0, "5.0 + 1.0 = 6.0; got " + repr(result)


def test_sums_across_all_records() -> None:
    """Scalar sums ALL records regardless of class.

    ClassA/HIGH (3.0) + ClassB/HIGH (3.0) + ClassC/LOW (1.0) = 7.0.
    Kills impl returning per-class or first-class only.
    """
    problems = [
        _p("ClassA", "f1", "HIGH"),
        _p("ClassB", "f2", "HIGH"),
        _p("ClassC", "f3", "LOW"),
    ]
    result = weighted_problem_count(problems, {"HIGH": 3.0, "LOW": 1.0})
    assert result == 7.0, "3.0+3.0+1.0=7.0; got " + repr(result)


def test_unknown_severity_contributes_zero() -> None:
    """Unknown severity -> 0.0 contribution (not raise, not 1.0).

    Kills impl raising KeyError on missing severity or using default=1.0.
    """
    problems = [
        _p("ClassA", "f1", "HIGH"),
        _p("ClassB", "f2", "MYSTERY"),  # not in weights
    ]
    result = weighted_problem_count(problems, {"HIGH": 5.0})
    assert result == 5.0, "MYSTERY contributes 0.0; got " + repr(result)


def test_empty_input_returns_zero() -> None:
    """Empty input -> 0.0 (not raise)."""
    result = weighted_problem_count([], {"HIGH": 3.0})
    assert result == 0.0, "Empty -> 0.0; got " + repr(result)
    assert isinstance(result, float), "Must be float; got " + repr(type(result))


def test_multiple_records_same_severity_each_contribute() -> None:
    """Each record contributes its weight, even if severity repeats.

    5 HIGH records at 2.0 each -> 10.0 (not 2.0 because distinct severities).
    Kills impl that counts distinct severities.
    """
    problems = [_p("C", f"f{i}", "HIGH") for i in range(5)]
    result = weighted_problem_count(problems, {"HIGH": 2.0})
    assert result == 10.0, "5 * 2.0 = 10.0; got " + repr(result)
