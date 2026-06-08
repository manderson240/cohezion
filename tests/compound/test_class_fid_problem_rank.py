"""Item 671: class_fid_problem_rank() -- rank of class x fid cells by count (descending).

Returns {class: {fid: rank}}.  rank 1 = most problems in class.
Ties share the lower rank (dense rank).  Sparse.  Empty -> {}.  Pure; no I/O.

Discriminating tests:
  1. PRIMARY DISC.: rank NOT count; ties share rank.
     class A: f1=5, f2=3, f3=3 -> f1:1, f2:2, f3:2 (count=5 wrong, raw-count wrong).
  2. Rank is within class, NOT global.
     class A: f1=10, class B: f2=3, f3=7 -> B.f2:rank=2, B.f3:rank=1 (not global rank=3).
  3. Single fid -> rank=1.
  4. All tied -> all rank=1.
  5. Empty -> {}.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import Problem, class_fid_problem_rank


def _p(cls: str, fid: str) -> Problem:
    return Problem(problem_class=cls, finding_id=fid, severity="HIGH")


def test_rank_not_count_ties_share_primary_discriminator() -> None:
    """PRIMARY DISC.: returns RANK not count; ties share rank.

    class A: f1=5, f2=3, f3=3 -> f1:rank=1, f2:rank=2, f3:rank=2.
    count=5 wrong; raw desc-sort position wrong for ties.
    """
    problems = [_p("A", "f1")] * 5 + [_p("A", "f2")] * 3 + [_p("A", "f3")] * 3
    result = class_fid_problem_rank(problems)
    assert isinstance(result, dict), "Must return dict"
    assert "A" in result
    assert isinstance(result["A"]["f1"], int), "Rank must be int"
    assert result["A"]["f1"] == 1, f"f1 highest -> rank=1; got {result['A']['f1']}"
    assert result["A"]["f2"] == 2, f"f2 tied -> rank=2; got {result['A']['f2']}"
    assert result["A"]["f3"] == 2, f"f3 tied -> rank=2; got {result['A']['f3']}"


def test_rank_is_within_class_not_global() -> None:
    """Rank is per-class, not global.

    class A: f1=10 -> rank=1. class B: f2=3, f3=7 -> f3:rank=1, f2:rank=2.
    Global rank would put f2 at rank=3, but per-class f2 is rank=2 in B.
    """
    problems = [_p("A", "f1")] * 10 + [_p("B", "f2")] * 3 + [_p("B", "f3")] * 7
    result = class_fid_problem_rank(problems)
    assert result["A"]["f1"] == 1, f"A.f1 alone -> rank=1; got {result.get('A', {}).get('f1')}"
    assert result["B"]["f3"] == 1, f"B.f3 highest in B -> rank=1; got {result.get('B', {}).get('f3')}"
    assert result["B"]["f2"] == 2, f"B.f2 lower in B -> rank=2; got {result.get('B', {}).get('f2')}"


def test_single_fid_rank_one() -> None:
    """Single fid -> rank=1."""
    problems = [_p("A", "f4")] * 5
    result = class_fid_problem_rank(problems)
    assert result["A"]["f4"] == 1, f"Single fid -> rank=1; got {result.get('A', {}).get('f4')}"


def test_all_tied_all_rank_one() -> None:
    """All fids equal count -> all rank=1."""
    problems = [_p("A", "f5")] * 3 + [_p("A", "f6")] * 3 + [_p("A", "f7")] * 3
    result = class_fid_problem_rank(problems)
    for fid in ("f5", "f6", "f7"):
        assert result["A"][fid] == 1, f"{fid} tied top -> rank=1; got {result['A'].get(fid)}"


def test_empty_returns_empty_dict() -> None:
    """Empty -> {}."""
    assert class_fid_problem_rank([]) == {}
