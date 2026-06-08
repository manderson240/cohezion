"""Item 634: fid_class_mean_count() -- mean per-class problem count per fid.

FID-axis complement of class_fid_mean_count (item 633).
mean = total_fid_count / distinct_classes_in_fid.
Returns {fid: mean_class_count}.  float.  Empty -> {}.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import Problem, fid_class_mean_count


def _p(cls: str, fid: str) -> Problem:
    return Problem(problem_class=cls, finding_id=fid, severity="HIGH")


def test_fid_axis_mean_not_class_axis_primary_discriminator() -> None:
    """PRIMARY DISC.: keyed by fid NOT class; mean = total_fid/distinct_classes.

    fid 'f1': class A=5, class B=2 -> total=7, classes=2 -> mean=7/2=3.5.
    Result key must be 'f1', not 'A'. Kills impl using class axis.
    """
    problems = [_p("A", "f1")] * 5 + [_p("B", "f1")] * 2
    result = fid_class_mean_count(problems)
    assert isinstance(result, dict), "Must return dict"
    assert "f1" in result, f"fid 'f1' must be key; got {list(result)}"
    assert "A" not in result, f"class 'A' must NOT be key; got {list(result)}"
    assert abs(result["f1"] - 3.5) < 1e-9, (
        f"class A=5, B=2 -> mean=3.5; got {result['f1']} (class-axis wrong)"
    )
    assert isinstance(result["f1"], float), "Must be float; got " + type(result["f1"]).__name__


def test_single_class_returns_that_count_as_float() -> None:
    """Single class for fid -> mean equals that count as float."""
    problems = [_p("A", "f2")] * 6
    result = fid_class_mean_count(problems)
    assert abs(result["f2"] - 6.0) < 1e-9, f"Single class -> mean=6.0; got {result['f2']}"


def test_empty_returns_empty_dict() -> None:
    """Empty -> {}."""
    assert fid_class_mean_count([]) == {}


def test_uniform_classes_mean_equals_common_count() -> None:
    """Uniform classes -> mean = each class's count.

    fid 'f1': class A=3, class B=3 -> total=6, classes=2 -> mean=3.0.
    """
    problems = [_p("A", "f1")] * 3 + [_p("B", "f1")] * 3
    result = fid_class_mean_count(problems)
    assert abs(result["f1"] - 3.0) < 1e-9, f"Uniform A=B=3 -> mean=3.0; got {result['f1']}"


def test_multiple_fids_independent() -> None:
    """Multiple fids each get independent mean.

    fid 'f1': class A=4, class B=2 -> mean=3.0.
    fid 'f2': class A=1, class B=1, class C=1 -> mean=1.0.
    """
    problems = (
        [_p("A", "f1")] * 4 + [_p("B", "f1")] * 2
        + [_p("A", "f2")] + [_p("B", "f2")] + [_p("C", "f2")]
    )
    result = fid_class_mean_count(problems)
    assert abs(result["f1"] - 3.0) < 1e-9, f"f1: A=4, B=2 -> mean=3.0; got {result['f1']}"
    assert abs(result["f2"] - 1.0) < 1e-9, f"f2: A=B=C=1 -> mean=1.0; got {result['f2']}"
