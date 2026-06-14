"""Item 631: class_fid_count_range() -- spread of per-fid counts per class (max - min).

Returns {class: max_fid_count - min_fid_count}.  int >= 0.  Empty -> {}.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import Problem, class_fid_count_range


def _p(cls: str, fid: str) -> Problem:
    return Problem(problem_class=cls, finding_id=fid, severity="HIGH")


def test_range_not_max_not_min_not_total_primary_discriminator() -> None:
    """PRIMARY DISC.: returns max - min (NOT max=5, NOT min=2, NOT total=7).

    Class A: f1=5, f2=2 -> range = 5-2 = 3.
    Kills impl returning max=5, min=2, or total=7.
    """
    problems = [_p("A", "f1")] * 5 + [_p("A", "f2")] * 2
    result = class_fid_count_range(problems)
    assert isinstance(result, dict), "Must return dict"
    assert "A" in result, f"Class 'A' must be key; got {list(result)}"
    assert result["A"] == 3, (
        f"f1=5, f2=2 -> range=3; got {result['A']} (max=5 wrong, min=2 wrong, total=7 wrong)"
    )
    assert isinstance(result["A"], int), "Must be int; got " + type(result["A"]).__name__


def test_single_fid_range_is_zero() -> None:
    """Single fid -> max=min -> range=0."""
    problems = [_p("A", "f1")] * 6
    result = class_fid_count_range(problems)
    assert result["A"] == 0, f"Single fid -> range=0; got {result['A']}"


def test_empty_returns_empty_dict() -> None:
    """Empty -> {}."""
    assert class_fid_count_range([]) == {}


def test_uniform_fids_range_is_zero() -> None:
    """All fids equal count -> range=0.

    Class A: f1=3, f2=3, f3=3 -> max=3, min=3, range=0.
    """
    problems = [_p("A", "f1")] * 3 + [_p("A", "f2")] * 3 + [_p("A", "f3")] * 3
    result = class_fid_count_range(problems)
    assert result["A"] == 0, f"Uniform [3,3,3] -> range=0; got {result['A']}"


def test_multiple_classes_independent() -> None:
    """Multiple classes each get independent range.

    Class A: f1=6, f2=1 -> range=5.
    Class B: f3=3, f4=3 -> range=0 (uniform).
    """
    problems = [_p("A", "f1")] * 6 + [_p("A", "f2")] + [_p("B", "f3")] * 3 + [_p("B", "f4")] * 3
    result = class_fid_count_range(problems)
    assert result["A"] == 5, f"A: f1=6, f2=1 -> range=5; got {result['A']}"
    assert result["B"] == 0, f"B: f3=f4=3 -> range=0; got {result['B']}"
