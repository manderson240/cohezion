"""Item 632: fid_class_count_range() -- spread of per-class counts per fid (max - min).

FID-axis complement of class_fid_count_range (item 631).
Returns {fid: max_class_count - min_class_count}.  int >= 0.  Empty -> {}.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import Problem, fid_class_count_range


def _p(cls: str, fid: str) -> Problem:
    return Problem(problem_class=cls, finding_id=fid, severity="HIGH")


def test_fid_axis_range_not_class_axis_primary_discriminator() -> None:
    """PRIMARY DISC.: keyed by fid NOT class; returns max - min per-class count.

    fid 'f1': class A=5, class B=2 -> range = 5-2 = 3.
    Result key must be 'f1', not 'A'. Kills impl using class axis.
    """
    problems = [_p("A", "f1")] * 5 + [_p("B", "f1")] * 2
    result = fid_class_count_range(problems)
    assert isinstance(result, dict), "Must return dict"
    assert "f1" in result, f"fid 'f1' must be key; got {list(result)}"
    assert "A" not in result, f"class 'A' must NOT be key; got {list(result)}"
    assert result["f1"] == 3, (
        f"class A=5, class B=2 -> range=3; got {result['f1']} "
        f"(max=5 wrong, min=2 wrong, class key 'A' wrong)"
    )
    assert isinstance(result["f1"], int), "Must be int; got " + type(result["f1"]).__name__


def test_single_class_range_is_zero() -> None:
    """Single class for fid -> max=min -> range=0."""
    problems = [_p("A", "f2")] * 6
    result = fid_class_count_range(problems)
    assert result["f2"] == 0, f"Single class -> range=0; got {result['f2']}"


def test_empty_returns_empty_dict() -> None:
    """Empty -> {}."""
    assert fid_class_count_range([]) == {}


def test_uniform_classes_range_is_zero() -> None:
    """All classes equal count -> range=0.

    fid 'f1': class A=3, class B=3 -> range=0.
    """
    problems = [_p("A", "f1")] * 3 + [_p("B", "f1")] * 3
    result = fid_class_count_range(problems)
    assert result["f1"] == 0, f"Uniform A=B=3 -> range=0; got {result['f1']}"


def test_multiple_fids_independent() -> None:
    """Multiple fids each get independent range.

    fid 'f1': class A=6, class B=1 -> range=5.
    fid 'f2': class A=4, class B=4 -> range=0.
    """
    problems = (
        [_p("A", "f1")] * 6 + [_p("B", "f1")]
        + [_p("A", "f2")] * 4 + [_p("B", "f2")] * 4
    )
    result = fid_class_count_range(problems)
    assert result["f1"] == 5, f"f1: A=6, B=1 -> range=5; got {result['f1']}"
    assert result["f2"] == 0, f"f2: A=B=4 -> range=0; got {result['f2']}"
