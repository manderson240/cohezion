"""Item 643: fid_class_dominance_ratio() -- max/min per-class count per fid.

FID-axis complement of class_fid_dominance_ratio (item 642).
dominance_ratio = max_class_count / min_class_count.
1.0 = all classes equal; > 1.0 = dominant class.
float >= 1.0.  Single-class -> 1.0.  Empty -> {}.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import Problem, fid_class_dominance_ratio


def _p(cls: str, fid: str) -> Problem:
    return Problem(problem_class=cls, finding_id=fid, severity="HIGH")


def test_fid_axis_not_class_axis_primary_discriminator() -> None:
    """PRIMARY DISC.: keyed by fid NOT class; ratio = max/min.

    fid 'f1': class A=6, class B=2 -> ratio=3.0.
    Key must be 'f1', NOT 'A'. class-axis wrong; range=4 wrong.
    """
    problems = [_p("A", "f1")] * 6 + [_p("B", "f1")] * 2
    result = fid_class_dominance_ratio(problems)
    assert isinstance(result, dict), "Must return dict"
    assert "f1" in result, f"fid 'f1' must be key; got {list(result)}"
    assert "A" not in result, f"class 'A' must NOT be key; got {list(result)}"
    assert abs(result["f1"] - 3.0) < 1e-9, (
        f"A=6, B=2 -> ratio=3.0; got {result['f1']} (class-axis wrong, range=4 wrong)"
    )
    assert isinstance(result["f1"], float), "Must be float"


def test_single_class_ratio_is_one() -> None:
    """Single class per fid -> ratio=1.0."""
    problems = [_p("A", "f2")] * 5
    result = fid_class_dominance_ratio(problems)
    assert "f2" in result
    assert abs(result["f2"] - 1.0) < 1e-9, f"Single-class -> ratio=1.0; got {result['f2']}"


def test_equal_classes_ratio_is_one() -> None:
    """Equal class counts -> ratio=1.0."""
    problems = [_p("A", "f3")] * 4 + [_p("B", "f3")] * 4
    result = fid_class_dominance_ratio(problems)
    assert "f3" in result
    assert abs(result["f3"] - 1.0) < 1e-9, f"Equal [4,4] -> ratio=1.0; got {result['f3']}"


def test_empty_returns_empty_dict() -> None:
    """Empty -> {}."""
    assert fid_class_dominance_ratio([]) == {}


def test_multiple_fids_independent() -> None:
    """Multiple fids each get independent ratio.

    fid 'f4': A=9, B=3 -> ratio=3.0.
    fid 'f5': A=5, B=5 -> ratio=1.0.
    """
    problems = [_p("A", "f4")] * 9 + [_p("B", "f4")] * 3 + [_p("A", "f5")] * 5 + [_p("B", "f5")] * 5
    result = fid_class_dominance_ratio(problems)
    assert abs(result["f4"] - 3.0) < 1e-9, f"f4: A=9,B=3 -> ratio=3.0; got {result['f4']}"
    assert abs(result["f5"] - 1.0) < 1e-9, f"f5: equal -> ratio=1.0; got {result['f5']}"
