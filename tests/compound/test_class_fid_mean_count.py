"""Item 633: class_fid_mean_count() -- mean per-fid problem count per class.

mean = total_class_count / distinct_fids_in_class.
Returns {class: mean_fid_count}.  float.  Empty -> {}.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import Problem, class_fid_mean_count


def _p(cls: str, fid: str) -> Problem:
    return Problem(problem_class=cls, finding_id=fid, severity="HIGH")


def test_mean_not_max_not_min_not_range_primary_discriminator() -> None:
    """PRIMARY DISC.: returns mean = total/fids (NOT max=5, NOT min=2, NOT range=3).

    Class A: f1=5, f2=2 -> total=7, distinct_fids=2 -> mean=7/2=3.5.
    Kills impl returning max=5, min=2, or range=3.
    """
    problems = [_p("A", "f1")] * 5 + [_p("A", "f2")] * 2
    result = class_fid_mean_count(problems)
    assert isinstance(result, dict), "Must return dict"
    assert "A" in result, f"Class 'A' must be key; got {list(result)}"
    assert abs(result["A"] - 3.5) < 1e-9, (
        f"f1=5, f2=2 -> mean=7/2=3.5; got {result['A']} "
        f"(max=5 wrong, min=2 wrong, range=3 wrong)"
    )
    assert isinstance(result["A"], float), "Must be float; got " + type(result["A"]).__name__


def test_single_fid_returns_that_count_as_float() -> None:
    """Single fid -> mean equals that count as float."""
    problems = [_p("A", "f1")] * 6
    result = class_fid_mean_count(problems)
    assert abs(result["A"] - 6.0) < 1e-9, f"Single fid -> mean=6.0; got {result['A']}"


def test_empty_returns_empty_dict() -> None:
    """Empty -> {}."""
    assert class_fid_mean_count([]) == {}


def test_three_fids_correct_mean() -> None:
    """Three fids: total/fids = mean.

    Class A: f1=6, f2=3, f3=3 -> total=12, fids=3 -> mean=4.0.
    """
    problems = [_p("A", "f1")] * 6 + [_p("A", "f2")] * 3 + [_p("A", "f3")] * 3
    result = class_fid_mean_count(problems)
    assert abs(result["A"] - 4.0) < 1e-9, f"total=12, fids=3 -> mean=4.0; got {result['A']}"


def test_multiple_classes_independent() -> None:
    """Multiple classes each get independent mean.

    Class A: f1=4, f2=2 -> total=6, fids=2 -> mean=3.0.
    Class B: f3=1, f4=1, f5=1 -> total=3, fids=3 -> mean=1.0.
    """
    problems = (
        [_p("A", "f1")] * 4 + [_p("A", "f2")] * 2
        + [_p("B", "f3")] + [_p("B", "f4")] + [_p("B", "f5")]
    )
    result = class_fid_mean_count(problems)
    assert abs(result["A"] - 3.0) < 1e-9, f"A: total=6, fids=2 -> mean=3.0; got {result['A']}"
    assert abs(result["B"] - 1.0) < 1e-9, f"B: total=3, fids=3 -> mean=1.0; got {result['B']}"
