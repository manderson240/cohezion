"""Item 838: top_n_classes_with_counts() -- top N classes by count as (class, count) tuples."""
from __future__ import annotations
from cohezion.compound.problem_discovery import Problem, top_n_classes_with_counts


def _p(cls: str) -> Problem:
    return Problem(problem_class=cls, finding_id="f1", severity="HIGH")


def test_tuple_result_not_string_list_primary_discriminator() -> None:
    # 3 classes: A(3), B(2), C(1) -> n=2 -> [("A",3),("B",2)]; string-list wrong; all-3 wrong
    problems = [_p("A")] * 3 + [_p("B")] * 2 + [_p("C")] * 1
    result = top_n_classes_with_counts(problems, 2)
    assert len(result) == 2
    assert result[0] == ("A", 3) and result[1] == ("B", 2)
    assert isinstance(result[0], tuple)


def test_descending_sort_by_count() -> None:
    problems = [_p("Z")] * 1 + [_p("A")] * 5
    result = top_n_classes_with_counts(problems, 2)
    assert result[0][0] == "A" and result[0][1] == 5


def test_tie_broken_by_class_name_ascending() -> None:
    problems = [_p("B")] * 3 + [_p("A")] * 3
    result = top_n_classes_with_counts(problems, 2)
    assert result[0][0] == "A" and result[1][0] == "B"


def test_empty_returns_empty_list() -> None:
    assert top_n_classes_with_counts([], 5) == []


def test_n_zero_returns_empty_list() -> None:
    problems = [_p("A")]
    assert top_n_classes_with_counts(problems, 0) == []
