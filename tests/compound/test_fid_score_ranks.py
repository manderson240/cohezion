"""Item 567: fid_score_ranks() -- rank dict for ALL fids by weighted score (2026-06-08).

``fid_score_ranks(problems, weights) -> dict[str, int]``:
Returns {fid: rank} for ALL fids. Rank 1 = highest total score.
Dense ranking: ties get same rank, next rank is consecutive.
Empty -> {}.  Pure; no I/O.

Discriminating tests -- each kills a plausible wrong implementation:

  1. PRIMARY DISC.: returns DICT for ALL fids (not int for one fid).
     Kills impl calling single-fid fid_score_rank in a loop improperly.
  2. FID axis (not class axis).
     1 class, 3 fids: class_score_rank has 1 key; fid_score_ranks has 3.
     Kills impl reusing class_score_rank (wrong axis).
  3. Dense ranking: ties get same rank, next rank is consecutive.
     Scores [HIGH, MED, MED, LOW] -> ranks [1, 2, 2, 3] not [1, 2, 2, 4].
     Kills impl using standard rank (where tie causes gap).
  4. Single fid -> {fid: 1} (only rank = 1).
     Kills impl with incorrect n<2 guard returning empty.
  5. Empty -> {} (not raise).
     Kills impl without empty guard.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import Problem, fid_score_ranks


def _p(cls: str, fid: str, sev: str) -> Problem:
    return Problem(problem_class=cls, finding_id=fid, severity=sev)


def test_returns_dict_for_all_fids_not_single_int() -> None:
    """PRIMARY DISC.: returns {fid: rank} for ALL fids (not a single int).

    3 fids -> dict with 3 keys, all ranked.
    Kills impl returning a scalar or only one fid.
    """
    problems = [
        _p("A", "f1", "HIGH"),
        _p("B", "f2", "MED"),
        _p("C", "f3", "LOW"),
    ]
    weights = {"HIGH": 5.0, "MED": 3.0, "LOW": 1.0}
    result = fid_score_ranks(problems, weights)
    assert isinstance(result, dict), "Must return dict; got " + repr(type(result))
    assert set(result.keys()) == {"f1", "f2", "f3"}, (
        f"Expected keys f1,f2,f3; got {set(result.keys())}"
    )
    assert result["f1"] == 1, f"f1 (HIGH=5) -> rank 1; got {result['f1']}"
    assert result["f2"] == 2, f"f2 (MED=3) -> rank 2; got {result['f2']}"
    assert result["f3"] == 3, f"f3 (LOW=1) -> rank 3; got {result['f3']}"


def test_fid_axis_not_class_axis() -> None:
    """FID axis (not class axis).

    1 class, 3 fids: class_score_rank has 1 key; fid_score_ranks has 3.
    Kills impl reusing class_score_rank.
    """
    problems = [
        _p("SameClass", "fa", "HIGH"),  # fa total = 5.0
        _p("SameClass", "fb", "MED"),  # fb total = 3.0
        _p("SameClass", "fc", "LOW"),  # fc total = 1.0
    ]
    weights = {"HIGH": 5.0, "MED": 3.0, "LOW": 1.0}
    result = fid_score_ranks(problems, weights)
    # class_score_rank would return {"SameClass": 1} (one key, wrong axis)
    assert len(result) == 3, f"3 fids -> 3 keys; got {len(result)} (1 key = class axis is wrong)"


def test_dense_ranking_for_ties() -> None:
    """Dense ranking: tied scores get same rank, next rank consecutive.

    Scores [HIGH=5, MED=3, MED=3, LOW=1] -> ranks [1, 2, 2, 3] (not [1,2,2,4]).
    Kills impl using standard/competition ranking (gap after tie).
    """
    problems = [
        _p("A", "f1", "HIGH"),  # total 5.0
        _p("B", "f2", "MED"),  # total 3.0
        _p("C", "f3", "MED"),  # total 3.0 -- tie with f2
        _p("D", "f4", "LOW"),  # total 1.0
    ]
    weights = {"HIGH": 5.0, "MED": 3.0, "LOW": 1.0}
    result = fid_score_ranks(problems, weights)
    assert result["f1"] == 1, f"f1 rank=1; got {result['f1']}"
    assert result["f2"] == 2, f"f2 rank=2 (tied); got {result['f2']}"
    assert result["f3"] == 2, f"f3 rank=2 (tied with f2); got {result['f3']}"
    assert result["f4"] == 3, (
        f"f4 rank=3 (dense -- not 4); got {result['f4']} (4 = competition ranking, not dense)"
    )


def test_single_fid_returns_rank_one() -> None:
    """Single fid -> {fid: 1} (only rank is 1).

    Kills impl with incorrect guard returning empty or 0.
    """
    problems = [_p("A", "only", "HIGH")]
    weights = {"HIGH": 5.0}
    result = fid_score_ranks(problems, weights)
    assert result == {"only": 1}, f"Single fid -> {{only: 1}}; got {result}"


def test_empty_returns_empty_dict() -> None:
    """Empty problems -> {} (not raise)."""
    result = fid_score_ranks([], {"HIGH": 5.0})
    assert result == {}, f"Empty -> {{}}; got {result}"
