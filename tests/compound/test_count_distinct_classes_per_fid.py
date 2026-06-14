"""Item 831: count_distinct_classes_per_fid() -- count distinct problem_classes per fid."""

from __future__ import annotations
from cohezion.compound.problem_discovery import Problem, count_distinct_classes_per_fid


def _p(cls: str, fid: str) -> Problem:
    return Problem(problem_class=cls, finding_id=fid, severity="HIGH")


def test_distinct_classes_not_total_problems_primary_discriminator() -> None:
    # fid f1: 3 problems, classes A,A,B -> 2 distinct; count_problems=3 wrong
    problems = [_p("A", "f1"), _p("A", "f1"), _p("B", "f1")]
    result = count_distinct_classes_per_fid(problems)
    got = result["f1"]
    assert got == 2 and isinstance(got, int) and got != 3


def test_all_same_class_gives_one() -> None:
    problems = [_p("A", "f2"), _p("A", "f2"), _p("A", "f2")]
    result = count_distinct_classes_per_fid(problems)
    assert result["f2"] == 1


def test_multiple_fids_independent() -> None:
    problems = [_p("A", "f10"), _p("B", "f10"), _p("C", "f10"), _p("A", "f11"), _p("A", "f11")]
    result = count_distinct_classes_per_fid(problems)
    assert result.get("f10") == 3 and result.get("f11") == 1


def test_empty_returns_empty_dict() -> None:
    assert count_distinct_classes_per_fid([]) == {}


def test_return_type_is_int() -> None:
    problems = [_p("A", "f99"), _p("B", "f99")]
    result = count_distinct_classes_per_fid(problems)
    assert isinstance(result["f99"], int)
