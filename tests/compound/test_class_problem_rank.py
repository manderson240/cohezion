"""Item 588: class_problem_rank() -- ordinal rank of each class by problem count (2026-06-08).

``class_problem_rank(problems) -> dict[str, int]``:
Returns {class: rank} where rank 1 = highest problem count.
Dense ranking: ties share the lowest rank of their group.
[10, 10, 5] -> ranks [1, 1, 3] (the 5 is ranked 3rd, not 2nd).
Empty -> {}.  Pure; no I/O.

Discriminating tests -- each kills a plausible wrong implementation:

  1. PRIMARY DISC.: rank 1 = MOST problems (descending, not ascending).
     [A:3, B:1] -> A=rank1, B=rank2.
     Kills impl assigning rank 1 to the class with FEWEST problems.
  2. Dense ranking: ties share rank; next rank skips (standard competition).
     [A:5, B:5, C:2] -> A=1, B=1, C=3 (NOT C=2).
     Kills impl using "competition ranking" where C would be 2.
     Wait -- dense ranking means [1,1,2] for [5,5,2]. Let me clarify.
     Actually "dense" ranking = [1,1,2] for [5,5,2] (no gaps).
     "Competition" ranking = [1,1,3] for [5,5,2] (skips 2).
     The backlog says "dense ranking: [10,10,5] -> [1,1,3]" which is COMPETITION ranking.
     Using competition ranking: tied items share lowest rank, next skips.
  3. Returns int (not float).
     Kills impl returning float ranks.
  4. Empty -> {} (not raise).
     Kills impl without empty guard.
  5. Single class -> rank 1.
     Kills impl with off-by-one (returning rank 0).
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import Problem, class_problem_rank


def _p(cls: str, fid: str, sev: str = "HIGH") -> Problem:
    return Problem(problem_class=cls, finding_id=fid, severity=sev)


def test_rank_1_is_most_problems_primary_discriminator() -> None:
    """PRIMARY DISC.: rank 1 = class with MOST problems.

    A has 3 problems, B has 1 problem -> A=rank1, B=rank2.
    Kills impl that assigns rank 1 to the class with FEWEST problems.
    """
    problems = [
        _p("A", "f1"),
        _p("A", "f2"),
        _p("A", "f3"),  # A: 3 problems
        _p("B", "f4"),  # B: 1 problem
    ]
    result = class_problem_rank(problems)
    assert isinstance(result, dict), "Must return dict; got " + repr(type(result))
    assert "A" in result, f"Class 'A' must be in result; got {result}"
    assert result["A"] == 1, (
        f"A (3 problems, most) must have rank=1; got {result['A']} "
        f"(rank=2 = ascending rank, wrong direction)"
    )
    assert result["B"] == 2, f"B (1 problem) must have rank=2; got {result['B']}"


def test_ties_share_rank_with_gap_after() -> None:
    """Ties use competition ranking: tied classes share rank; next rank skips.

    A:5, B:5, C:2 -> A=1, B=1, C=3 (C is 3rd-highest, skips rank 2).
    Kills impl using dense ranking (would give C=2) or sequential (A=1, B=2, C=3).
    """
    problems = (
        [_p("A", f"a{i}") for i in range(5)]  # A: 5
        + [_p("B", f"b{i}") for i in range(5)]  # B: 5
        + [_p("C", f"c{i}") for i in range(2)]  # C: 2
    )
    result = class_problem_rank(problems)
    assert result["A"] == 1, f"A (tied 5) -> rank=1; got {result['A']}"
    assert result["B"] == 1, f"B (tied 5) -> rank=1; got {result['B']}"
    assert result["C"] == 3, (
        f"C (2 problems, 2 above it) -> rank=3; got {result['C']} "
        f"(rank=2 = dense ranking, not competition)"
    )


def test_returns_int_not_float() -> None:
    """Rank values are int (not float).

    Kills impl returning float ranks.
    """
    result = class_problem_rank([_p("A", "f1"), _p("B", "f2")])
    for cls, rank in result.items():
        assert isinstance(rank, int), f"Rank for '{cls}' must be int; got {type(rank).__name__}"


def test_empty_returns_empty_dict() -> None:
    """Empty problems -> {} (not raise).

    Kills impl without empty guard.
    """
    result = class_problem_rank([])
    assert result == {}, f"Empty -> {{}}; got {result}"


def test_single_class_is_rank_one() -> None:
    """Single class -> rank=1 (not 0).

    Kills impl with off-by-one (0-indexed rank).
    """
    result = class_problem_rank([_p("A", "f1"), _p("A", "f2")])
    assert result.get("A") == 1, f"Single class -> rank=1; got {result}"
