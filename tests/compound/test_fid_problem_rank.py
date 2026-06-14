"""Item 589: fid_problem_rank() — ordinal rank of each fid by problem count (2026-06-08).

``fid_problem_rank(problems) -> dict[str, int]``:
Returns {fid: rank} where rank 1 = fid with the most problems.
Tied fids share the top rank of their group; the next rank skips
(competition / 1-2-2-4 style).
FID-axis complement of class_problem_rank.
Empty -> {}.  Pure; no I/O.

Discriminating tests -- each kills a plausible wrong implementation:

  1. PRIMARY DISC.: keyed on FID axis (not class axis).
     One class 'A', three fids f1/f2/f3 each with 1 problem:
     class_problem_rank gives {'A': 1} (one entry for one class);
     fid_problem_rank gives {'f1':1, 'f2':1, 'f3':1} (three entries for three fids).
     Kills impl reusing class_problem_rank on wrong axis.
  2. Rank 1 = MOST problems (not fewest).
     fid 'fa'=5 problems, fid 'fb'=1 problem -> fa=1, fb=2.
     Kills impl using ascending rank (would give fa=2, fb=1).
  3. Tied fids share rank with skip (competition ranking, NOT dense).
     [fa:3, fb:3, fc:1] -> fa=1, fb=1, fc=3 (NOT fc=2 which would be dense).
     Kills impl using dense ranking.
  4. Empty -> {} (not raise).
     Kills impl without empty guard.
  5. Returns int (not float).
     Kills impl returning float ranks.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import Problem, fid_problem_rank


def _p(cls: str, fid: str) -> Problem:
    return Problem(problem_class=cls, finding_id=fid, severity="HIGH")


def test_fid_axis_not_class_axis_primary_discriminator() -> None:
    """PRIMARY DISC.: keyed on FID axis (not class axis).

    One class 'A', three fids f1/f2/f3 each with 1 problem:
    class_problem_rank -> {'A': 1} (single class entry);
    fid_problem_rank   -> {'f1':1, 'f2':1, 'f3':1} (one entry per fid).
    Kills impl reusing class_problem_rank on wrong axis.
    """
    problems = [_p("A", "f1"), _p("A", "f2"), _p("A", "f3")]
    result = fid_problem_rank(problems)
    assert isinstance(result, dict), "Must return dict; got " + repr(type(result))
    assert "f1" in result and "f2" in result and "f3" in result, (
        f"All 3 fids must be keys; got {list(result)} (only 'A' = class axis wrong)"
    )
    assert "A" not in result, f"Class 'A' must NOT be a key; got {result} (class axis used)"
    assert result["f1"] == 1 and result["f2"] == 1 and result["f3"] == 1, (
        f"All tied at 1 problem -> rank 1; got {result}"
    )


def test_rank_one_is_most_problems_not_fewest() -> None:
    """Rank 1 = MOST problems (not fewest).

    fa=5 problems, fb=1 problem -> fa rank 1, fb rank 2.
    Kills impl using ascending rank (would give fa rank 2).
    """
    problems = [_p("A", "fa")] * 5 + [_p("B", "fb")]
    result = fid_problem_rank(problems)
    assert result["fa"] == 1, f"fa (5 problems) must be rank 1; got {result['fa']}"
    assert result["fb"] == 2, f"fb (1 problem) must be rank 2; got {result['fb']}"


def test_ties_competition_ranking_not_dense() -> None:
    """Tied fids share rank with skip (competition ranking, NOT dense).

    fa=3, fb=3, fc=1 -> fa=1, fb=1, fc=3.
    Dense ranking would give fc=2 (wrong).
    Kills impl using dense ranking.
    """
    problems = [_p("A", "fa")] * 3 + [_p("B", "fb")] * 3 + [_p("C", "fc")]
    result = fid_problem_rank(problems)
    assert result["fa"] == 1, f"fa (3, tied top) must be rank 1; got {result['fa']}"
    assert result["fb"] == 1, f"fb (3, tied top) must be rank 1; got {result['fb']}"
    assert result["fc"] == 3, (
        f"fc (1 problem, after 2-way tie) must be rank 3 (not 2); got {result['fc']} "
        f"(rank 2 = dense ranking, wrong)"
    )


def test_empty_returns_empty_dict() -> None:
    """Empty problems -> {} (not raise).

    Kills impl without empty guard.
    """
    result = fid_problem_rank([])
    assert result == {}, f"Empty -> {{}}; got {result}"


def test_rank_values_are_int() -> None:
    """Rank values are int (not float).

    Kills impl returning float ranks.
    """
    problems = [_p("A", "fx"), _p("B", "fy")]
    result = fid_problem_rank(problems)
    for fid, rank in result.items():
        assert isinstance(rank, int), f"Rank for {fid!r} must be int; got {type(rank).__name__}"
