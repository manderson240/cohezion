"""Item 839: top_n_fids_with_counts() -- top N fids by count as (fid, count) tuples."""

from __future__ import annotations
from cohezion.compound.problem_discovery import Problem, top_n_fids_with_counts


def _p(fid: str) -> Problem:
    return Problem(problem_class="A", finding_id=fid, severity="HIGH")


def test_fid_tuple_not_class_primary_discriminator() -> None:
    # 3 fids: f1(3), f2(2), f3(1) -> n=2 -> [("f1",3),("f2",2)]; class-axis wrong
    problems = [_p("f1")] * 3 + [_p("f2")] * 2 + [_p("f3")] * 1
    result = top_n_fids_with_counts(problems, 2)
    assert len(result) == 2
    assert result[0] == ("f1", 3) and result[1] == ("f2", 2)
    assert isinstance(result[0], tuple)


def test_descending_sort_by_count() -> None:
    problems = [_p("f9")] * 1 + [_p("f1")] * 5
    result = top_n_fids_with_counts(problems, 2)
    assert result[0][0] == "f1" and result[0][1] == 5


def test_tie_broken_by_fid_name_ascending() -> None:
    problems = [_p("f2")] * 3 + [_p("f1")] * 3
    result = top_n_fids_with_counts(problems, 2)
    assert result[0][0] == "f1" and result[1][0] == "f2"


def test_empty_returns_empty_list() -> None:
    assert top_n_fids_with_counts([], 5) == []


def test_n_zero_returns_empty_list() -> None:
    assert top_n_fids_with_counts([_p("f1")], 0) == []
