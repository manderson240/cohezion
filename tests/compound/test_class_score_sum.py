"""Item 541: class_score_sum() -- total weighted score across all classes (2026-06-08).

``class_score_sum(problems, weights) -> float``:
Returns the sum of all per-class total weighted scores.
Equivalent to summing all individual problem weights (grouping by class does not
change the grand total).  0.0 for empty.  Pure; no I/O.

Discriminating tests -- each kills a plausible wrong implementation:

  1. PRIMARY DISC.: returns weighted SUM (not problem count).
     Kills impl returning len(problems) for different-weight severities.
  2. Sum equals direct sum of individual weights (class grouping is transparent).
     Kills impl that double-counts or under-counts due to aggregation error.
  3. Scales with severity weights (higher weight -> higher sum).
     Kills impl using unweighted count.
  4. 0.0 for empty (not raise).
     Kills impl without empty guard.
  5. Unknown severity contributes 0.0 (weight defaults to 0).
     Kills impl that raises on missing severity key.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import Problem, class_score_sum


def _p(cls: str, fid: str, sev: str) -> Problem:
    return Problem(problem_class=cls, finding_id=fid, severity=sev)


def test_returns_weighted_sum_not_count() -> None:
    """PRIMARY DISC.: returns weighted sum, not problem count.

    3 problems: 2x HIGH(5.0) + 1x LOW(1.0) = sum 11.0; count = 3.
    Kills impl returning len(problems) (would return 3, not 11.0).
    """
    problems = [
        _p("A", "f1", "HIGH"),  # +5.0
        _p("A", "f2", "HIGH"),  # +5.0  A total = 10.0
        _p("B", "f3", "LOW"),  # +1.0  B total = 1.0
    ]
    weights = {"HIGH": 5.0, "LOW": 1.0}
    result = class_score_sum(problems, weights)
    assert isinstance(result, float), "Must return float; got " + repr(type(result))
    # weighted sum = 5+5+1 = 11.0; problem count = 3 -- must not be 3.0
    assert abs(result - 11.0) < 1e-9, (
        f"Weighted sum of [HIGH,HIGH,LOW]=[5,5,1] = 11.0; got {result} (3.0 = count is wrong)"
    )


def test_sum_equals_individual_weights_sum() -> None:
    """Class grouping is transparent: sum(class_totals) == sum(all weights).

    A: 2x HIGH(10.0) -> total 20.0; B: 1x MED(3.0) -> total 3.0; C: 2x LOW(1.0) -> total 2.0.
    class_score_sum = 20 + 3 + 2 = 25.0.
    Direct sum of individual weights = 10+10+3+1+1 = 25.0.
    Kills impl that double-counts or under-counts through aggregation.
    """
    problems = [
        _p("A", "f1", "HIGH"),  # +10.0
        _p("A", "f2", "HIGH"),  # +10.0
        _p("B", "f3", "MED"),  # +3.0
        _p("C", "f4", "LOW"),  # +1.0
        _p("C", "f5", "LOW"),  # +1.0
    ]
    weights = {"HIGH": 10.0, "MED": 3.0, "LOW": 1.0}
    result = class_score_sum(problems, weights)
    assert abs(result - 25.0) < 1e-9, f"Sum of class totals [20,3,2] = 25.0; got {result}"


def test_scales_with_severity_weights() -> None:
    """Same structure, higher weights -> higher sum.

    Kills impl using unweighted count (which would return 2.0 for both).
    """
    problems_low = [_p("A", "f1", "LOW"), _p("B", "f2", "LOW")]
    problems_high = [_p("A", "f1", "HIGH"), _p("B", "f2", "HIGH")]
    weights = {"LOW": 1.0, "HIGH": 100.0}
    result_low = class_score_sum(problems_low, weights)
    result_high = class_score_sum(problems_high, weights)
    assert abs(result_low - 2.0) < 1e-9, f"2x LOW(1.0) = 2.0; got {result_low}"
    assert abs(result_high - 200.0) < 1e-9, f"2x HIGH(100.0) = 200.0; got {result_high}"
    assert result_high > result_low, "Higher weights must produce higher sum"


def test_empty_returns_zero() -> None:
    """Empty problems -> 0.0 (not raise)."""
    result = class_score_sum([], {"HIGH": 5.0})
    assert result == 0.0, f"Empty -> 0.0; got {result}"


def test_unknown_severity_contributes_zero() -> None:
    """Problem with unknown severity contributes 0.0 to the sum.

    Kills impl that raises KeyError for missing severity key.
    """
    problems = [
        _p("A", "f1", "KNOWN"),  # +5.0
        _p("B", "f2", "UNKNOWN"),  # +0.0 (not in weights)
    ]
    weights = {"KNOWN": 5.0}
    result = class_score_sum(problems, weights)
    assert abs(result - 5.0) < 1e-9, f"KNOWN(5.0) + UNKNOWN(0.0) = 5.0; got {result}"
