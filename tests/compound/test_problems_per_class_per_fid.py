"""Item 832: problems_per_class_per_fid() -- count problems per (class, fid) cell."""

from __future__ import annotations
from cohezion.compound.problem_discovery import Problem, problems_per_class_per_fid


def _p(cls: str, fid: str) -> Problem:
    return Problem(problem_class=cls, finding_id=fid, severity="HIGH")


def test_tuple_key_not_flat_primary_discriminator() -> None:
    # (class A, fid f1) with 3 problems -> {("A","f1"): 3}; flat class-key wrong; flat fid-key wrong
    problems = [_p("A", "f1"), _p("A", "f1"), _p("A", "f1")]
    result = problems_per_class_per_fid(problems)
    assert ("A", "f1") in result and result[("A", "f1")] == 3
    assert "A" not in result and "f1" not in result


def test_different_cells_are_independent() -> None:
    problems = [_p("A", "f1"), _p("A", "f1"), _p("B", "f1"), _p("A", "f2")]
    result = problems_per_class_per_fid(problems)
    assert result.get(("A", "f1")) == 2
    assert result.get(("B", "f1")) == 1
    assert result.get(("A", "f2")) == 1


def test_empty_returns_empty_dict() -> None:
    assert problems_per_class_per_fid([]) == {}


def test_single_problem_gives_cell_count_one() -> None:
    problems = [_p("X", "f99")]
    result = problems_per_class_per_fid(problems)
    assert result[("X", "f99")] == 1


def test_return_type_is_int() -> None:
    problems = [_p("D", "f1"), _p("D", "f1")]
    result = problems_per_class_per_fid(problems)
    assert isinstance(result[("D", "f1")], int)
