"""Item 549: class_score_min() -- minimum of class total scores (2026-06-08).

``class_score_min(problems, weights) -> float``:
Returns the minimum of per-class total weighted scores.
Identifies the least-burdened class.  0.0 for empty.
Single class -> that class total (not 0.0).  Pure; no I/O.

Discriminating tests -- each kills a plausible wrong implementation:

  1. PRIMARY DISC.: returns MIN (not max).
     Three classes [1.0, 2.0, 3.0]: min=1.0, max=3.0.
     Kills impl reusing class_score_max (returns 3.0, not 1.0).
  2. Single class -> that class total (not 0.0).
     Kills impl with an incorrect n<2 guard returning 0.0.
  3. Operates on class TOTAL scores (not individual severities).
     Class A: 3x LOW(1.0) -> total 3.0; B total = 8.0 -> min = 3.0, not 1.0.
     Kills impl computing min over raw per-problem severity weights.
  4. 0.0 for empty (not raise).
     Kills impl without empty guard.
  5. Min decreases when lightest class loses weight.
     Kills impl returning mean, max, or other non-min stat.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import Problem, class_score_min


def _p(cls: str, fid: str, sev: str) -> Problem:
    return Problem(problem_class=cls, finding_id=fid, severity=sev)


def test_returns_min_not_max() -> None:
    """PRIMARY DISC.: returns MIN of class totals, not max.

    Three classes with totals [1.0, 2.0, 3.0]:
      min = 1.0
      max = 3.0  (class_score_max returns 3.0 -- wrong here)
      mean = 2.0
    Kills impl reusing class_score_max (returns 3.0, not 1.0).
    """
    problems = [
        _p("A", "f1", "S1"),  # A total = 1.0
        _p("B", "f2", "S2"),  # B total = 2.0
        _p("C", "f3", "S3"),  # C total = 3.0
    ]
    weights = {"S1": 1.0, "S2": 2.0, "S3": 3.0}
    result = class_score_min(problems, weights)
    assert isinstance(result, float), "Must return float; got " + repr(type(result))
    # min=1.0; max=3.0; mean=2.0 -- must not be 3.0 or 2.0
    assert abs(result - 1.0) < 1e-9, (
        f"Min of class totals [1,2,3] = 1.0; got {result} (3.0 = max is wrong; 2.0 = mean is wrong)"
    )


def test_single_class_returns_its_total() -> None:
    """Single class -> min = that class's total (not 0.0).

    Kills impl with an incorrect n<2 guard returning 0.0.
    """
    problems = [
        _p("OnlyClass", "f1", "HIGH"),
        _p("OnlyClass", "f2", "LOW"),
    ]
    weights = {"HIGH": 10.0, "LOW": 1.0}
    result = class_score_min(problems, weights)
    # 1 distinct class: total = 11.0; min([11.0]) = 11.0
    assert abs(result - 11.0) < 1e-9, (
        f"Single class total 11.0 -> min = 11.0; got {result} (0.0 = wrong guard)"
    )


def test_uses_class_total_not_individual_severity() -> None:
    """Min of class TOTALS, not min of individual per-problem severity weights.

    Class A: 3x LOW(1.0) -> total 3.0; Class B: 1x HIGH(8.0) -> total 8.0.
    Min of class totals = 3.0 (not 1.0 = min individual severity).
    Kills impl computing min over raw per-problem severity weights.
    """
    problems = [
        _p("A", "f1", "LOW"),  # +1.0
        _p("A", "f2", "LOW"),  # +1.0
        _p("A", "f3", "LOW"),  # A total = 3.0
        _p("B", "f4", "HIGH"),  # B total = 8.0
    ]
    weights = {"LOW": 1.0, "HIGH": 8.0}
    result = class_score_min(problems, weights)
    # Class totals: A=3.0, B=8.0 -> min=3.0
    # Individual severity min=1.0 (LOW) -- wrong
    assert abs(result - 3.0) < 1e-9, (
        f"Min class total = 3.0; got {result} (1.0 = individual severity min is wrong)"
    )


def test_empty_returns_zero() -> None:
    """Empty problems -> 0.0 (not raise)."""
    result = class_score_min([], {"HIGH": 5.0})
    assert result == 0.0, f"Empty -> 0.0; got {result}"


def test_min_changes_correctly_between_distributions() -> None:
    """Min tracks the lightest class correctly across different distributions.

    Kills impl returning mean, max, or a fixed value.
    """
    # Case 1: two classes [5.0, 10.0] -> min=5.0
    p1 = [_p("A", "f1", "MED"), _p("B", "f2", "HIGH")]
    w = {"MED": 5.0, "HIGH": 10.0}
    assert abs(class_score_min(p1, w) - 5.0) < 1e-9, (
        f"Min of [5,10] = 5.0; got {class_score_min(p1, w)}"
    )
    # Case 2: two classes [2.0, 10.0] -> min=2.0 (lighter class is now 2.0, not 5.0)
    p2 = [_p("A", "f1", "TINY"), _p("B", "f2", "HIGH")]
    w2 = {"TINY": 2.0, "HIGH": 10.0}
    assert abs(class_score_min(p2, w2) - 2.0) < 1e-9, (
        f"Min of [2,10] = 2.0; got {class_score_min(p2, w2)}"
    )
    # min decreases as lightest class loses weight
    assert class_score_min(p2, w2) < class_score_min(p1, w), (
        "Lighter class (2.0) should yield smaller min than (5.0)"
    )
