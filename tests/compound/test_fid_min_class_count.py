"""Item 630: fid_min_class_count() -- minimum per-class problem count per fid.

FID-axis complement of class_min_fid_count (item 629).
Returns {fid: min_class_count}.  int.  Empty -> {}.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import Problem, fid_min_class_count


def _p(cls: str, fid: str) -> Problem:
    return Problem(problem_class=cls, finding_id=fid, severity="HIGH")


def test_fid_axis_min_not_max_primary_discriminator() -> None:
    """PRIMARY DISC.: keyed by fid NOT class; returns min per-class count (NOT max).

    fid 'f1' appears in class A 5 times, class B 2 times.
    result['f1']==2 (min), keyed by 'f1'.
    max=5 wrong; class-key 'A' wrong.
    Kills impl using class axis or returning max.
    """
    problems = [_p("A", "f1")] * 5 + [_p("B", "f1")] * 2
    result = fid_min_class_count(problems)
    assert isinstance(result, dict), "Must return dict"
    assert "f1" in result, f"fid 'f1' must be key; got {list(result)}"
    assert "A" not in result, f"class 'A' must NOT be key; got {list(result)}"
    assert result["f1"] == 2, f"class A=5, class B=2 -> min=2; got {result['f1']} (max=5 wrong)"
    assert isinstance(result["f1"], int), "Must be int; got " + type(result["f1"]).__name__


def test_single_class_returns_that_count() -> None:
    """Single class -> min equals that class's count (only bucket)."""
    problems = [_p("A", "f2")] * 6
    result = fid_min_class_count(problems)
    assert result["f2"] == 6, f"Single class -> min=6; got {result['f2']}"


def test_empty_returns_empty_dict() -> None:
    """Empty -> {}."""
    assert fid_min_class_count([]) == {}


def test_multiple_fids_independent() -> None:
    """Multiple fids each get independent min.

    fid 'f1': class A=4, class B=1 -> min=1.
    fid 'f2': class A=2, class B=3 -> min=2.
    """
    problems = [_p("A", "f1")] * 4 + [_p("B", "f1")] + [_p("A", "f2")] * 2 + [_p("B", "f2")] * 3
    result = fid_min_class_count(problems)
    assert result["f1"] == 1, f"f1: B=1 min; got {result['f1']}"
    assert result["f2"] == 2, f"f2: A=2 min; got {result['f2']}"


def test_uniform_classes_returns_common_count() -> None:
    """All classes equal count for a fid -> min = that count.

    fid 'f1': class A=3, class B=3 -> min=3.
    """
    problems = [_p("A", "f1")] * 3 + [_p("B", "f1")] * 3
    result = fid_min_class_count(problems)
    assert result["f1"] == 3, f"Uniform A=B=3 -> min=3; got {result['f1']}"
