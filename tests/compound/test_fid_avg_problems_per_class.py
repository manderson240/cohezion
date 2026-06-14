"""Item 676: fid_avg_problems_per_class() -- avg problem count per (fid, class) cell, per fid.

Fid-axis complement of class_avg_problems_per_fid (item 675).
For each fid: mean(cell_count) over all classes that contain that fid.
float.  Returns {fid: avg}.  Empty -> {}.  Pure; no I/O.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import Problem, fid_avg_problems_per_class


def _p(cls: str, fid: str) -> Problem:
    return Problem(problem_class=cls, finding_id=fid, severity="HIGH")


def test_avg_per_class_not_total_primary_discriminator() -> None:
    """PRIMARY DISC.: avg = mean(class-cell counts) NOT total count NOT distinct-class count.

    fid 'f1': classA×3 classB×7 -> avg=(3+7)/2=5.0.
    total=10 wrong; distinct-class-count=2 wrong.
    Kills total-count impl and distinct-count impl.
    """
    problems = [_p("A", "f1")] * 3 + [_p("B", "f1")] * 7
    result = fid_avg_problems_per_class(problems)
    assert isinstance(result, dict), "Must return dict"
    assert "f1" in result, f"fid 'f1' must be present; got {list(result)}"
    expected = (3 + 7) / 2
    assert abs(result["f1"] - expected) < 1e-9, (
        f"(3+7)/2=5.0; got {result['f1']} (total=10 wrong, count=2 wrong)"
    )
    assert isinstance(result["f1"], float), "Must be float"


def test_single_class_avg_equals_count() -> None:
    """Single class -> avg = total problems for that fid (only one class cell)."""
    problems = [_p("A", "f2")] * 9
    result = fid_avg_problems_per_class(problems)
    assert abs(result["f2"] - 9.0) < 1e-9, f"9 problems, 1 class -> avg=9.0; got {result['f2']}"


def test_empty_returns_empty_dict() -> None:
    """Empty -> {}."""
    assert fid_avg_problems_per_class([]) == {}


def test_multiple_fids_independent() -> None:
    """Different fids get independent averages."""
    problems = (
        [_p("A", "fa")] * 4
        + [_p("B", "fa")] * 4
        + [_p("X", "fb")] * 10
        + [_p("Y", "fb")] * 2
        + [_p("Z", "fb")] * 3
    )
    result = fid_avg_problems_per_class(problems)
    assert abs(result["fa"] - 4.0) < 1e-9, f"fa avg=4.0; got {result.get('fa')}"
    assert abs(result["fb"] - 5.0) < 1e-9, f"fb avg=(10+2+3)/3=5.0; got {result.get('fb')}"


def test_return_type_is_float() -> None:
    """Result values must be float not int."""
    result = fid_avg_problems_per_class([_p("A", "fx")] * 6 + [_p("B", "fx")] * 6)
    assert isinstance(result["fx"], float), f"Must be float; got {type(result['fx'])}"
    assert abs(result["fx"] - 6.0) < 1e-9, f"(6+6)/2=6.0; got {result['fx']}"
