"""Item 830: count_distinct_fids_per_class() -- count distinct finding_ids per class."""
from __future__ import annotations
from cohezion.compound.problem_discovery import Problem, count_distinct_fids_per_class


def _p(cls: str, fid: str) -> Problem:
    return Problem(problem_class=cls, finding_id=fid, severity="HIGH")


def test_distinct_fids_not_total_problems_primary_discriminator() -> None:
    # class A: 3 problems, fids f1,f1,f2 -> 2 distinct; count_problems=3 wrong
    problems = [_p("A", "f1"), _p("A", "f1"), _p("A", "f2")]
    result = count_distinct_fids_per_class(problems)
    got = result["A"]
    assert got == 2 and isinstance(got, int) and got != 3


def test_all_same_fid_gives_one() -> None:
    problems = [_p("B", "f1"), _p("B", "f1"), _p("B", "f1")]
    result = count_distinct_fids_per_class(problems)
    assert result["B"] == 1


def test_multi_class_independent() -> None:
    problems = [_p("X", "f1"), _p("X", "f2"), _p("X", "f3"), _p("Y", "f1"), _p("Y", "f1")]
    result = count_distinct_fids_per_class(problems)
    assert result.get("X") == 3 and result.get("Y") == 1


def test_empty_returns_empty_dict() -> None:
    assert count_distinct_fids_per_class([]) == {}


def test_return_type_is_int() -> None:
    problems = [_p("D", "f1"), _p("D", "f2")]
    result = count_distinct_fids_per_class(problems)
    assert isinstance(result["D"], int)
