"""Item 507: score_percentile_of_class() -- [0,1] normalized score position (2026-06-08).

``score_percentile_of_class(problems, weights, problem_class) -> float | None``:
Returns the fraction of OTHER classes with a strictly lower score.
percentile = (# classes with strictly lower score) / (total_classes - 1).
Single class -> 0.0 (not None).  Absent class -> None.  Empty -> None.
Pure; no I/O.

Discriminating tests -- each kills a plausible wrong implementation:

  1. PRIMARY DISC.: returns FLOAT in [0.0, 1.0] (not int rank).
     Kills impl returning score_rank_of_class (int).
  2. Single class -> 0.0 (not None, not raise).
     Kills impl requiring N >= 2 to compute.
  3. Absent class -> None (not raise, not 0.0).
     Kills impl silently returning 0.0 for absent class.
  4. Strictly-lower count (not <=).
     Kills impl using >= for the comparison (would count equals).
  5. Correct fraction: (strictly_lower_count) / (total_classes - 1).
     Kills impl dividing by total_classes (off-by-one).
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import (
    Problem,
    score_percentile_of_class,
)


def _p(cls: str, fid: str, sev: str) -> Problem:
    return Problem(problem_class=cls, finding_id=fid, severity=sev)


def test_returns_float_not_rank() -> None:
    """PRIMARY DISC.: returns float [0,1], not int rank.

    Top class out of 4 -> percentile 1.0 (3 lower / 3 others).
    Kills impl returning score_rank_of_class which returns int=1 for the top class.
    """
    problems = [
        _p("A", "f1", "HIGH"),   # score 4.0 -> top
        _p("B", "f2", "MED"),    # score 3.0
        _p("C", "f3", "LOW"),    # score 2.0
        _p("D", "f4", "TINY"),   # score 1.0
    ]
    weights = {"HIGH": 4.0, "MED": 3.0, "LOW": 2.0, "TINY": 1.0}
    result = score_percentile_of_class(problems, weights, "A")
    assert isinstance(result, float), "Must return float; got " + repr(type(result))
    # A has 3 classes strictly below it out of 3 others -> 1.0
    assert result == 1.0, "Top class percentile = 1.0; got " + repr(result)
    result_d = score_percentile_of_class(problems, weights, "D")
    assert result_d == 0.0, "Bottom class percentile = 0.0; got " + repr(result_d)


def test_single_class_returns_zero() -> None:
    """Single class -> 0.0 (not None, not raise).

    Kills impl returning None when N < 2.
    """
    problems = [_p("Only", "f1", "HIGH")]
    result = score_percentile_of_class(problems, {"HIGH": 3.0}, "Only")
    assert result == 0.0, "Single class -> 0.0; got " + repr(result)
    assert isinstance(result, float), "Must be float 0.0; got " + repr(type(result))


def test_absent_class_returns_none() -> None:
    """Absent class -> None (not 0.0, not raise).

    Kills impl silently returning 0.0 for absent class.
    """
    problems = [_p("Present", "f1", "HIGH")]
    result = score_percentile_of_class(problems, {"HIGH": 3.0}, "ABSENT")
    assert result is None, "Absent class -> None; got " + repr(result)


def test_strictly_lower_not_lower_or_equal() -> None:
    """Counts STRICTLY lower, not lower-or-equal.

    A=3.0, B=3.0 (tie), C=1.0 -> A has 1 class strictly below (C);
    percentile = 1/2 = 0.5 (not 2/2 = 1.0 which would include the tie).
    Kills impl using <= comparison.
    """
    problems = [
        _p("A", "f1", "HIGH"),   # 3.0
        _p("B", "f2", "HIGH"),   # 3.0 (tied)
        _p("C", "f3", "LOW"),    # 1.0
    ]
    result = score_percentile_of_class(problems, {"HIGH": 3.0, "LOW": 1.0}, "A")
    assert result == 0.5, "1 strictly lower out of 2 others = 0.5; got " + repr(result)


def test_correct_fraction_denominator() -> None:
    """Denominator is (total_classes - 1), not total_classes.

    Middle class out of 3: 1 strictly lower, 1 strictly higher.
    percentile = 1 / (3-1) = 0.5.
    Kills impl dividing by total_classes (would give 1/3 ≈ 0.333).
    """
    problems = [
        _p("High", "f1", "HIGH"),  # 3.0 -> 2 others, 1 lower
        _p("Mid", "f2", "MED"),    # 2.0 -> 2 others, 1 lower
        _p("Low", "f3", "LOW"),    # 1.0 -> 2 others, 0 lower
    ]
    result = score_percentile_of_class(problems, {"HIGH": 3.0, "MED": 2.0, "LOW": 1.0}, "Mid")
    assert result == 0.5, "Mid: 1 lower / 2 others = 0.5; got " + repr(result)
