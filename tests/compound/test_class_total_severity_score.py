"""Item 482: class_total_severity_score() -- weighted severity aggregation per class (2026-06-08).

``class_total_severity_score(problems, problem_class, weights) -> float``:
Returns the aggregate score for a class by summing weights[p.severity] for each
matching Problem.  Unrecognised severities contribute 0.  Empty/absent class -> 0.0.
Pure; no I/O.

Discriminating tests -- each kills a plausible wrong implementation:

  1. PRIMARY DISC.: score is weighted sum, not plain count.
     ClassA: HIGH x2 (weight 3.0), LOW x1 (weight 1.0) -> 7.0 not 3.
     Kills impl returning plain problem count.
  2. Unknown severity contributes 0 (not raise).
     Kills impl that raises KeyError on missing weight key.
  3. Absent class -> 0.0 (not raise).
     Kills impl raising on absent class.
  4. Returns float (not int).
     Kills impl returning int count instead of float score.
  5. Empty input -> 0.0.
     Kills impl with unguarded access.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import (
    Problem,
    class_total_severity_score,
)


def _p(cls: str, fid: str, sev: str) -> Problem:
    return Problem(problem_class=cls, finding_id=fid, severity=sev)


def test_weighted_sum_not_plain_count() -> None:
    """PRIMARY DISC.: score is weighted sum (HIGH x2 weight=3.0, LOW x1 weight=1.0 -> 7.0).

    Plain count would return 3 (ClassA has 3 records).
    Kills impl returning problem count.
    """
    problems = [
        _p("ClassA", "f1", "HIGH"),
        _p("ClassA", "f2", "HIGH"),
        _p("ClassA", "f3", "LOW"),
        _p("ClassB", "f4", "HIGH"),
    ]
    weights = {"HIGH": 3.0, "LOW": 1.0}
    result = class_total_severity_score(problems, "ClassA", weights)
    assert result == 7.0, "2*3.0 + 1*1.0 = 7.0; got " + repr(result)


def test_unknown_severity_contributes_zero() -> None:
    """Unrecognised severity contributes 0 (not raise).

    Kills impl raising KeyError on missing weight key.
    """
    problems = [
        _p("ClassA", "f1", "HIGH"),
        _p("ClassA", "f2", "UNKNOWN_SEV"),
    ]
    weights = {"HIGH": 5.0}
    result = class_total_severity_score(problems, "ClassA", weights)
    assert result == 5.0, "HIGH=5.0, UNKNOWN_SEV=0.0 -> 5.0; got " + repr(result)


def test_absent_class_returns_zero_float() -> None:
    """Absent class -> 0.0 (not raise)."""
    problems = [_p("ClassA", "f1", "HIGH")]
    weights = {"HIGH": 3.0}
    result = class_total_severity_score(problems, "NONEXISTENT", weights)
    assert result == 0.0, "Absent class -> 0.0; got " + repr(result)


def test_returns_float_not_int() -> None:
    """Result is float, not int.

    Kills impl returning plain count int.
    """
    problems = [_p("ClassA", "f1", "HIGH")]
    weights = {"HIGH": 2.0}
    result = class_total_severity_score(problems, "ClassA", weights)
    assert isinstance(result, float), "Must return float; got " + repr(type(result))
    assert result == 2.0


def test_empty_input_returns_zero() -> None:
    """Empty input -> 0.0 (not raise)."""
    result = class_total_severity_score([], "ClassA", {"HIGH": 3.0})
    assert result == 0.0, "Empty -> 0.0; got " + repr(result)
