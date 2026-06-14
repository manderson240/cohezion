"""Item 547: class_score_max() -- maximum per-class total weighted score (2026-06-08).

``class_score_max(problems, weights) -> float``:
Returns the maximum of per-class total weighted scores.
Identifies the most-burdened class.  0.0 for empty.
Single class -> that class total (not 0.0).  Pure; no I/O.

Discriminating tests -- each kills a plausible wrong implementation:

  1. PRIMARY DISC.: returns MAX (not min, not mean, not sum).
     Three classes [1,2,3]: max=3.0, min=1.0, mean=2.0.
     Kills impl reusing class_score_min (returns 1.0).
  2. Single class -> that class total (not 0.0 guard).
     Kills impl applying n<2 guard that returns 0.0 for single class.
  3. Uses class TOTAL scores, not individual severities.
     Class A: 2x HIGH(5.0) -> total 10.0; B=1.0 -> max = 10.0, not 5.0.
     Kills impl returning raw severity max.
  4. Monotonically increases when heaviest class grows.
     Kills impl returning mean/range/other non-max statistic.
  5. 0.0 for empty (not raise).
     Kills impl without empty guard.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import Problem, class_score_max


def _p(cls: str, fid: str, sev: str) -> Problem:
    return Problem(problem_class=cls, finding_id=fid, severity=sev)


def test_returns_max_not_min() -> None:
    """PRIMARY DISC.: returns max (not min, not mean).

    Three classes [1.0, 2.0, 3.0]: max=3.0, min=1.0, mean=2.0.
    Kills impl reusing class_score_min (returns 1.0, not 3.0).
    """
    problems = [
        _p("A", "f1", "S1"),  # A total = 1.0
        _p("B", "f2", "S2"),  # B total = 2.0
        _p("C", "f3", "S3"),  # C total = 3.0
    ]
    weights = {"S1": 1.0, "S2": 2.0, "S3": 3.0}
    result = class_score_max(problems, weights)
    assert isinstance(result, float), "Must return float; got " + repr(type(result))
    # max=3.0; min=1.0; mean=2.0 -- must not be 1.0 or 2.0
    assert abs(result - 3.0) < 1e-9, (
        f"Max of class totals [1,2,3] = 3.0; got {result} (1.0 = min is wrong; 2.0 = mean is wrong)"
    )


def test_single_class_returns_its_total() -> None:
    """Single class -> return that class total (not 0.0).

    Kills impl applying n<2 guard that short-circuits to 0.0.
    """
    problems = [
        _p("OnlyClass", "f1", "HIGH"),
        _p("OnlyClass", "f2", "LOW"),
    ]
    weights = {"HIGH": 10.0, "LOW": 1.0}
    result = class_score_max(problems, weights)
    assert abs(result - 11.0) < 1e-9, (
        f"Single class total = 11.0; max = 11.0; got {result} (0.0 = wrong guard)"
    )


def test_uses_class_total_not_individual_severity() -> None:
    """Class aggregation before max: max of TOTALS, not max of severities.

    Class A: 2x HIGH(5.0) -> total 10.0; B total = 1.0.
    Max of class totals = 10.0 (not 5.0 = max individual severity).
    Kills impl computing max over raw severity weights.
    """
    problems = [
        _p("A", "f1", "HIGH"),  # +5.0
        _p("A", "f2", "HIGH"),  # A total = 10.0
        _p("B", "f3", "LOW"),  # B total = 1.0
    ]
    weights = {"HIGH": 5.0, "LOW": 1.0}
    result = class_score_max(problems, weights)
    assert abs(result - 10.0) < 1e-9, (
        f"Max class total = 10.0; got {result} (5.0 = max individual severity is wrong)"
    )


def test_monotonically_increases_with_heaviest_class() -> None:
    """Adding more weight to the heaviest class increases the max.

    Kills impl returning sum, mean, or other non-max statistic.
    """
    problems_base = [_p("A", "f1", "HIGH"), _p("B", "f2", "LOW")]
    problems_extra = [_p("A", "f1", "HIGH"), _p("A", "f3", "HIGH"), _p("B", "f2", "LOW")]
    weights = {"HIGH": 5.0, "LOW": 1.0}
    result_base = class_score_max(problems_base, weights)  # A=5.0, B=1.0; max=5.0
    result_extra = class_score_max(problems_extra, weights)  # A=10.0, B=1.0; max=10.0
    assert abs(result_base - 5.0) < 1e-9, f"Base max = 5.0; got {result_base}"
    assert abs(result_extra - 10.0) < 1e-9, f"Extra max = 10.0; got {result_extra}"
    assert result_extra > result_base, "Adding to heaviest class must increase max"


def test_empty_returns_zero() -> None:
    """Empty problems -> 0.0 (not raise)."""
    result = class_score_max([], {"HIGH": 5.0})
    assert result == 0.0, f"Empty -> 0.0; got {result}"
