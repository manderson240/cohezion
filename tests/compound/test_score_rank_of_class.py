"""Item 506: score_rank_of_class() -- 1-based dense rank by total score (2026-06-08).

``score_rank_of_class(problems, weights, problem_class) -> int | None``:
Returns the 1-based dense rank of problem_class by total weighted severity score.
Rank 1 = highest-scoring class.  Ties share the same rank.
Absent class -> None.  Empty problems -> None.  Pure; no I/O.

Discriminating tests -- each kills a plausible wrong implementation:

  1. PRIMARY DISC.: returns INT rank, not score.
     Kills impl returning class_total_severity_score (a float).
  2. 1-based (rank 1 = highest score).
     Kills impl returning 0-based index.
  3. DENSE rank on ties: both tied classes share the same rank number.
     Kills impl returning ordinal position-after-all-better (standard rank).
  4. Absent class -> None (not raise, not 0).
     Kills impl raising KeyError or returning a sentinel integer.
  5. Empty problems -> None (not raise).
     Kills impl without empty guard.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import (
    Problem,
    score_rank_of_class,
)


def _p(cls: str, fid: str, sev: str) -> Problem:
    return Problem(problem_class=cls, finding_id=fid, severity=sev)


def test_returns_int_rank_not_score() -> None:
    """PRIMARY DISC.: returns int rank, not float score.

    Highest-scoring class -> rank 1 (int).
    Kills impl returning class_total_severity_score (float).
    """
    problems = [
        _p("ClassA", "f1", "HIGH"),   # score 5.0 -> rank 1
        _p("ClassB", "f2", "LOW"),    # score 1.0 -> rank 2
    ]
    weights = {"HIGH": 5.0, "LOW": 1.0}
    result = score_rank_of_class(problems, weights, "ClassA")
    assert isinstance(result, int), "Must return int; got " + repr(type(result))
    assert result == 1, "ClassA highest -> rank 1; got " + repr(result)
    result_b = score_rank_of_class(problems, weights, "ClassB")
    assert result_b == 2, "ClassB second -> rank 2; got " + repr(result_b)


def test_rank_is_one_based() -> None:
    """Rank 1 = highest-scoring class (1-based, not 0-based).

    Kills impl returning 0-based index (would return 0 for the top class).
    """
    problems = [_p("Top", "f1", "HIGH"), _p("Bottom", "f2", "LOW")]
    result = score_rank_of_class(problems, {"HIGH": 5.0, "LOW": 1.0}, "Top")
    assert result == 1, "Top class is rank 1 (1-based); got " + repr(result)
    assert result != 0, "Must be 1-based, not 0-based"


def test_ties_share_dense_rank() -> None:
    """Tied classes share the same dense rank.

    ClassA and ClassB both score 3.0 -> both rank 1.
    ClassC scores 1.0 -> rank 2 (not rank 3 in non-dense scheme).
    Kills impl using non-dense/standard rank (1, 2, 3) instead of dense (1, 1, 2).
    """
    problems = [
        _p("ClassA", "f1", "HIGH"),  # 3.0
        _p("ClassB", "f2", "HIGH"),  # 3.0 (tied with ClassA)
        _p("ClassC", "f3", "LOW"),   # 1.0
    ]
    weights = {"HIGH": 3.0, "LOW": 1.0}
    assert score_rank_of_class(problems, weights, "ClassA") == 1, "ClassA tied at rank 1"
    assert score_rank_of_class(problems, weights, "ClassB") == 1, "ClassB tied at rank 1"
    assert score_rank_of_class(problems, weights, "ClassC") == 2, (
        "ClassC -> dense rank 2 (not 3); got "
        + repr(score_rank_of_class(problems, weights, "ClassC"))
    )


def test_absent_class_returns_none() -> None:
    """Absent class -> None (not raise, not 0).

    Kills impl raising KeyError or returning sentinel integer.
    """
    problems = [_p("ClassA", "f1", "HIGH")]
    result = score_rank_of_class(problems, {"HIGH": 3.0}, "ABSENT")
    assert result is None, "Absent -> None; got " + repr(result)


def test_empty_problems_returns_none() -> None:
    """Empty problems -> None (not raise)."""
    result = score_rank_of_class([], {"HIGH": 3.0}, "ClassA")
    assert result is None, "Empty -> None; got " + repr(result)
