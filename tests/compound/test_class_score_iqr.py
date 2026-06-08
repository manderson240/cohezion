"""Item 527: class_score_iqr() -- IQR of class total scores (2026-06-08).

``class_score_iqr(problems, weights) -> float``:
Returns Q3 - Q1 of class total weighted scores (interquartile range), using
statistics.quantiles with the default 'exclusive' method.
0.0 for fewer than 4 distinct classes.  Empty -> 0.0.  Pure; no I/O.

Discriminating tests -- each kills a plausible wrong implementation:

  1. PRIMARY DISC.: returns IQR (Q3 - Q1), not range (max - min).
     Kills impl returning score_spread (max - min).
  2. 0.0 for fewer than 4 distinct classes (not raise).
     Kills impl without the n < 4 guard (by design convention).
  3. Operates on class TOTAL scores, not raw per-problem severity values.
     Kills impl computing quantiles over individual problem severities.
  4. Distinct CLASS count drives the n < 4 guard (not problem count).
     Kills impl using len(problems) < 4 instead of len(class_totals) < 4.
  5. Empty -> 0.0 (not raise).
     Kills impl without empty guard.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import Problem, class_score_iqr


def _p(cls: str, fid: str, sev: str) -> Problem:
    return Problem(problem_class=cls, finding_id=fid, severity=sev)


def test_returns_iqr_not_range() -> None:
    """PRIMARY DISC.: returns IQR (Q3 - Q1), not range (max - min).

    Four classes with scores 1.0, 2.0, 3.0, 4.0:
      range = 4.0 - 1.0 = 3.0
      Q1 = 1.25, Q3 = 3.75 (exclusive), IQR = 2.5
    Kills impl returning score_spread (3.0).
    """
    problems = [
        _p("A", "f1", "S1"),  # 1.0
        _p("B", "f2", "S2"),  # 2.0
        _p("C", "f3", "S3"),  # 3.0
        _p("D", "f4", "S4"),  # 4.0
    ]
    weights = {"S1": 1.0, "S2": 2.0, "S3": 3.0, "S4": 4.0}
    result = class_score_iqr(problems, weights)
    assert isinstance(result, float), "Must return float; got " + repr(type(result))
    # IQR = 2.5, range = 3.0 -- must not be 3.0 (score_spread)
    assert abs(result - 2.5) < 1e-9, (
        f"IQR of [1,2,3,4] = 2.5; got {result} (range=3.0 is wrong)"
    )


def test_fewer_than_four_classes_returns_zero() -> None:
    """< 4 distinct classes -> 0.0 (convention: quartiles need ≥ 4 points).

    Kills impl without the n < 4 guard.
    """
    problems = [
        _p("A", "f1", "HIGH"),
        _p("B", "f2", "LOW"),
        _p("C", "f3", "MED"),
    ]
    result = class_score_iqr(problems, {"HIGH": 5.0, "LOW": 1.0, "MED": 3.0})
    assert result == 0.0, f"3 classes -> 0.0; got {result}"


def test_uses_class_total_scores_not_individual_severities() -> None:
    """Computes IQR over per-class TOTAL scores, not raw severity values.

    Class A has 2x HIGH(5.0) -> total 10.0; others: B=3.0, C=1.0, D=0.5.
    Class totals [0.5, 1.0, 3.0, 10.0] -> IQR = 7.625 (exclusive).
    Individual severity approach [0.5, 1.0, 3.0, 5.0, 5.0] -> IQR = 4.25.
    Kills impl computing quantiles over individual problem severity weights.
    """
    problems = [
        _p("A", "f1", "HIGH"),   # +5.0
        _p("A", "f2", "HIGH"),   # A total = 10.0
        _p("B", "f3", "LOW"),    # B total = 3.0
        _p("C", "f4", "V_LOW"),  # C total = 1.0
        _p("D", "f5", "X_LOW"),  # D total = 0.5
    ]
    weights = {"HIGH": 5.0, "LOW": 3.0, "V_LOW": 1.0, "X_LOW": 0.5}
    result = class_score_iqr(problems, weights)
    # Class totals IQR = 7.625; individual IQR = 4.25 — the right answer is 7.625
    assert isinstance(result, float), "Must return float"
    assert abs(result - 7.625) < 1e-9, (
        f"IQR of class totals [0.5,1.0,3.0,10.0] = 7.625; got {result}"
    )


def test_class_count_not_problem_count_drives_guard() -> None:
    """n < 4 guard checks distinct CLASS count, not problem count.

    10 problems all in 2 classes -> 0.0 (2 < 4 classes).
    Kills impl using len(problems) < 4 instead of len(class_totals) < 4.
    """
    problems = [
        _p("A", f"f{i}", "HIGH") for i in range(5)
    ] + [
        _p("B", f"g{i}", "LOW") for i in range(5)
    ]
    result = class_score_iqr(problems, {"HIGH": 5.0, "LOW": 1.0})
    assert result == 0.0, (
        f"2 classes (10 problems) -> 0.0 (< 4 classes); got {result}"
    )


def test_empty_returns_zero() -> None:
    """Empty problems -> 0.0 (not raise)."""
    result = class_score_iqr([], {"HIGH": 5.0})
    assert result == 0.0, f"Empty -> 0.0; got {result}"
