"""Item 642: class_fid_dominance_ratio() -- max/min per-fid count per class.

dominance_ratio = max_fid_count / min_fid_count.
1.0 = all fids equal; > 1.0 = dominant fid exists.
float >= 1.0.  Single-fid -> 1.0.  Empty -> {}.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import Problem, class_fid_dominance_ratio


def _p(cls: str, fid: str) -> Problem:
    return Problem(problem_class=cls, finding_id=fid, severity="HIGH")


def test_ratio_not_range_not_cv_primary_discriminator() -> None:
    """PRIMARY DISC.: ratio = max/min (NOT max-min range, NOT cv).

    class A: f1=6, f2=2 -> ratio=6/2=3.0.
    range=4 wrong; cv≈0.8 wrong. Kills range or cv impls.
    """
    problems = [_p("A", "f1")] * 6 + [_p("A", "f2")] * 2
    result = class_fid_dominance_ratio(problems)
    assert isinstance(result, dict), "Must return dict"
    assert "A" in result, f"Class 'A' must be key; got {list(result)}"
    assert abs(result["A"] - 3.0) < 1e-9, (
        f"f1=6, f2=2 -> ratio=3.0; got {result['A']} "
        f"(range=4 wrong, cv≈0.8 wrong)"
    )
    assert isinstance(result["A"], float), "Must be float"


def test_single_fid_ratio_is_one() -> None:
    """Single fid -> ratio=1.0 (max/min = count/count)."""
    problems = [_p("B", "f3")] * 5
    result = class_fid_dominance_ratio(problems)
    assert "B" in result, f"Class 'B' must be present"
    assert abs(result["B"] - 1.0) < 1e-9, (
        f"Single-fid -> ratio=1.0; got {result['B']}"
    )


def test_equal_fids_ratio_is_one() -> None:
    """Equal fid counts -> ratio=1.0."""
    problems = [_p("C", "f4")] * 4 + [_p("C", "f5")] * 4
    result = class_fid_dominance_ratio(problems)
    assert "C" in result
    assert abs(result["C"] - 1.0) < 1e-9, (
        f"Equal fids [4,4] -> ratio=1.0; got {result['C']}"
    )


def test_empty_returns_empty_dict() -> None:
    """Empty -> {}."""
    assert class_fid_dominance_ratio([]) == {}


def test_multiple_classes_independent() -> None:
    """Multiple classes each get independent ratio.

    Class X: f6=9, f7=3 -> ratio=3.0.
    Class Y: f8=5, f9=5 -> ratio=1.0.
    """
    problems = (
        [_p("X", "f6")] * 9 + [_p("X", "f7")] * 3
        + [_p("Y", "f8")] * 5 + [_p("Y", "f9")] * 5
    )
    result = class_fid_dominance_ratio(problems)
    assert abs(result["X"] - 3.0) < 1e-9, (
        f"X: f6=9,f7=3 -> ratio=3.0; got {result['X']}"
    )
    assert abs(result["Y"] - 1.0) < 1e-9, (
        f"Y: equal -> ratio=1.0; got {result['Y']}"
    )
