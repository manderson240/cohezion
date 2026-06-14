"""Item 627: class_max_fid_count() -- max number of problems any single fid contributes per class.

Returns {class: max_fid_count}.  int.  Empty -> {}.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import Problem, class_max_fid_count


def _p(cls: str, fid: str) -> Problem:
    return Problem(problem_class=cls, finding_id=fid, severity="HIGH")


def test_max_not_total_not_label_primary_discriminator() -> None:
    """PRIMARY DISC.: returns max per-fid count (NOT total, NOT avg, NOT fid label).

    Class A: f1=5 problems, f2=2 problems.
    max_fid_count=5 (NOT total=7, NOT avg=3.5, NOT label='f1').
    Kills impl returning total class count or class_fid_distinct_count.
    """
    problems = [_p("A", "f1")] * 5 + [_p("A", "f2")] * 2
    result = class_max_fid_count(problems)
    assert isinstance(result, dict), "Must return dict"
    assert "A" in result, f"Class 'A' must be key; got {list(result)}"
    assert result["A"] == 5, (
        f"f1=5, f2=2 -> max=5; got {result['A']} (total=7 wrong, avg=3.5 wrong, label='f1' wrong)"
    )
    assert isinstance(result["A"], int), "Must be int; got " + type(result["A"]).__name__


def test_single_fid_returns_total_count() -> None:
    """Single fid -> max equals total (only one bucket)."""
    problems = [_p("A", "f1")] * 6
    result = class_max_fid_count(problems)
    assert result["A"] == 6, f"Single fid -> max=6=total; got {result['A']}"


def test_empty_returns_empty_dict() -> None:
    """Empty -> {}."""
    assert class_max_fid_count([]) == {}


def test_multiple_classes_independent() -> None:
    """Multiple classes each get independent max.

    Class A: f1=4, f2=1 -> max=4.
    Class B: f3=2, f4=3, f5=3 -> max=3 (tied at 3).
    """
    problems = (
        [_p("A", "f1")] * 4
        + [_p("A", "f2")]
        + [_p("B", "f3")] * 2
        + [_p("B", "f4")] * 3
        + [_p("B", "f5")] * 3
    )
    result = class_max_fid_count(problems)
    assert result["A"] == 4, f"A: f1=4 max; got {result['A']}"
    assert result["B"] == 3, f"B: f4=f5=3 max; got {result['B']}"


def test_all_fids_equal_count_returns_that_count() -> None:
    """All fids contribute equally -> max = that common count.

    Class A: f1=2, f2=2, f3=2 -> max=2 (not 6=total, not 3=fid-count).
    """
    problems = [_p("A", "f1")] * 2 + [_p("A", "f2")] * 2 + [_p("A", "f3")] * 2
    result = class_max_fid_count(problems)
    assert result["A"] == 2, f"Uniform [2,2,2] -> max=2; got {result['A']}"
