"""Item 590: class_score_rank_competition() -- competition rank by weighted score (2026-06-08).

``class_score_rank_competition(problems, weights) -> dict[str, int]``:
Returns {class: rank} where rank 1 = highest weighted score.
Competition ranking: tied classes share the lower rank; next rank skips (1-1-3, not 1-1-2).
NOTE: Named class_score_rank_competition to avoid clash with class_score_rank (item 566,
which uses dense ranking).
Empty -> {}.  Pure; no I/O.

Discriminating tests -- each kills a plausible wrong implementation:

  1. PRIMARY DISC.: rank by WEIGHTED SCORE (not raw count).
     Class A has 2 HIGH (w=2.0 each, score=4.0); class B has 5 LOW (w=0.5 each, score=2.5).
     A gets rank 1, B gets rank 2 (score-based, not count-based: B has more problems).
     Kills impl reusing class_problem_rank without weighting.
  2. Competition ranking (not dense): tied classes leave a gap.
     [A=4.0, B=4.0, C=1.0] -> A=1, B=1, C=3 (not C=2 which would be dense).
     Kills impl using dense ranking (item 566 behavior).
  3. Rank 1 = HIGHEST score (not lowest).
     fa=5.0, fb=1.0 -> fa rank 1.
     Kills impl using ascending rank.
  4. Empty -> {} (not raise).
     Kills impl without empty guard.
  5. Returns int ranks (not float scores).
     Kills impl returning score values instead of ordinal ranks.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import Problem, class_score_rank_competition


def _p(cls: str, fid: str, sev: str) -> Problem:
    return Problem(problem_class=cls, finding_id=fid, severity=sev)


def test_weighted_score_not_raw_count_primary_discriminator() -> None:
    """PRIMARY DISC.: rank by WEIGHTED SCORE (not raw count).

    A: 2 HIGH at w=2.0 -> score=4.0.  B: 5 LOW at w=0.5 -> score=2.5.
    A has fewer problems but higher score -> A=rank1, B=rank2.
    class_problem_rank (raw count) would give A=rank2, B=rank1 (B has 5 > A has 2).
    Kills impl reusing class_problem_rank without weighting.
    """
    weights = {"HIGH": 2.0, "LOW": 0.5}
    problems = [_p("A", "f1", "HIGH"), _p("A", "f2", "HIGH")] + [_p("B", f"f{i}", "LOW") for i in range(5)]
    result = class_score_rank_competition(problems, weights)
    assert isinstance(result, dict), "Must return dict; got " + repr(type(result))
    assert result["A"] == 1, (
        f"A (score=4.0) must be rank 1; got {result['A']} "
        f"(raw-count ranking would put B=rank1 since B has 5 problems > A has 2)"
    )
    assert result["B"] == 2, f"B (score=2.5) must be rank 2; got {result['B']}"


def test_competition_ranking_not_dense() -> None:
    """Competition ranking: tied classes leave a gap after their group.

    [A=4.0, B=4.0, C=1.0] -> A=1, B=1, C=3 (NOT C=2 which would be dense).
    class_score_rank (item 566) uses DENSE ranking -> C=2.
    Kills impl using dense ranking.
    """
    weights = {"HIGH": 4.0, "LOW": 1.0}
    problems = [
        _p("A", "f1", "HIGH"),  # A score=4.0
        _p("B", "f2", "HIGH"),  # B score=4.0
        _p("C", "f3", "LOW"),   # C score=1.0
    ]
    result = class_score_rank_competition(problems, weights)
    assert result["A"] == 1, f"A (tied top) must be rank 1; got {result['A']}"
    assert result["B"] == 1, f"B (tied top) must be rank 1; got {result['B']}"
    assert result["C"] == 3, (
        f"C (after 2-way tie) must be rank 3 (not 2); got {result['C']} "
        f"(rank 2 = dense ranking, wrong for competition)"
    )


def test_rank_one_is_highest_score_not_lowest() -> None:
    """Rank 1 = highest score (not lowest).

    fa=5.0, fb=1.0 -> fa=rank1, fb=rank2.
    Kills impl using ascending rank (would give fa=rank2).
    """
    weights = {"HIGH": 5.0, "LOW": 1.0}
    problems = [_p("fa_cls", "f1", "HIGH"), _p("fb_cls", "f2", "LOW")]
    result = class_score_rank_competition(problems, weights)
    assert result["fa_cls"] == 1, f"fa_cls (score=5.0) must be rank 1; got {result['fa_cls']}"
    assert result["fb_cls"] == 2, f"fb_cls (score=1.0) must be rank 2; got {result['fb_cls']}"


def test_empty_returns_empty_dict() -> None:
    """Empty problems -> {} (not raise).

    Kills impl without empty guard.
    """
    result = class_score_rank_competition([], {"HIGH": 1.0})
    assert result == {}, f"Empty -> {{}}; got {result}"


def test_rank_values_are_int_not_score() -> None:
    """Rank values are int (not float score values).

    Kills impl returning score=5.0 instead of rank=1.
    """
    weights = {"HIGH": 5.0}
    problems = [_p("A", "f1", "HIGH"), _p("B", "f2", "HIGH")]
    result = class_score_rank_competition(problems, weights)
    for cls, rank in result.items():
        assert isinstance(rank, int), (
            "Rank for '" + cls + "' must be int (not float score); got " + type(rank).__name__ + "=" + repr(rank)
        )
