"""Item 520: fid_score_rank() -- 1-based dense rank of a finding ID by score (2026-06-08).

``fid_score_rank(problems, weights, finding_id) -> int | None``:
Returns the 1-based dense rank of finding_id in the full fid score ranking
(rank 1 = highest-scoring fid).  Tied fids share the same rank (dense rank).
Absent fid -> None.  Empty -> None.  Pure; no I/O.

Discriminating tests -- each kills a plausible wrong implementation:

  1. PRIMARY DISC.: returns INT rank (not score).
     fid with score 5.0 has rank 1 (not 5.0).
     Kills impl returning the total score instead of ordinal position.
  2. 1-based indexing (rank 1 = highest, not 0-based).
     Kills impl returning 0-based array index.
  3. DENSE rank: tied fids share the same rank.
     A:5.0, B:5.0, C:1.0 -> rank(A)=rank(B)=1, rank(C)=2 (not 3).
     Kills impl using standard/Olympic rank (position-after-all-higher-including-ties).
  4. Absent fid -> None (not raise).
     Kills impl without membership guard.
  5. Empty problems -> None (not raise).
     Kills impl without empty guard.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import (
    Problem,
    fid_score_rank,
)


def _p(cls: str, fid: str, sev: str) -> Problem:
    return Problem(problem_class=cls, finding_id=fid, severity=sev)


def test_returns_rank_not_score() -> None:
    """PRIMARY DISC.: returns INT rank, not the score value.

    fid_a has score 5.0; rank should be 1 (not 5.0).
    Kills impl returning total score instead of ordinal position.
    """
    problems = [
        _p("ClassA", "fid_a", "HIGH"),   # score 5.0
        _p("ClassA", "fid_b", "LOW"),    # score 1.0
    ]
    result = fid_score_rank(problems, {"HIGH": 5.0, "LOW": 1.0}, "fid_a")
    assert isinstance(result, int), "Must return int; got " + repr(type(result))
    assert result == 1, "fid_a is rank 1 (highest); got " + repr(result)
    assert result != 5, "Must return rank (1), not score (5.0); got " + repr(result)


def test_one_based_indexing() -> None:
    """Rank is 1-based (highest-scoring fid = rank 1, not rank 0).

    Kills impl returning 0-based index.
    """
    problems = [_p("ClassA", "fid_only", "HIGH")]
    result = fid_score_rank(problems, {"HIGH": 3.0}, "fid_only")
    assert result == 1, "Single fid is rank 1 (not 0); got " + repr(result)


def test_dense_rank_ties_share_same_rank() -> None:
    """Dense rank: tied fids share rank; next rank skips (dense, not Olympic).

    fid_a=5.0, fid_b=5.0, fid_c=1.0:
      rank(fid_a) = rank(fid_b) = 1
      rank(fid_c) = 2  (not 3)
    Kills impl using Olympic rank (3 for fid_c) or non-deterministic ties.
    """
    problems = [
        _p("ClassA", "fid_b", "HIGH"),   # 5.0 tied
        _p("ClassA", "fid_a", "HIGH"),   # 5.0 tied
        _p("ClassA", "fid_c", "LOW"),    # 1.0
    ]
    weights = {"HIGH": 5.0, "LOW": 1.0}
    rank_a = fid_score_rank(problems, weights, "fid_a")
    rank_b = fid_score_rank(problems, weights, "fid_b")
    rank_c = fid_score_rank(problems, weights, "fid_c")
    assert rank_a == 1, "fid_a tied at top -> rank 1; got " + repr(rank_a)
    assert rank_b == 1, "fid_b tied at top -> rank 1; got " + repr(rank_b)
    assert rank_c == 2, "fid_c below tie -> dense rank 2 (not 3); got " + repr(rank_c)


def test_absent_fid_returns_none() -> None:
    """Absent finding_id -> None (not raise).

    Kills impl without membership guard.
    """
    problems = [_p("ClassA", "fid_a", "HIGH")]
    result = fid_score_rank(problems, {"HIGH": 3.0}, "fid_missing")
    assert result is None, "Absent fid -> None; got " + repr(result)


def test_empty_problems_returns_none() -> None:
    """Empty problems -> None (not raise).

    Kills impl without empty guard.
    """
    result = fid_score_rank([], {"HIGH": 3.0}, "fid_a")
    assert result is None, "Empty problems -> None; got " + repr(result)
