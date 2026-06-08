"""Item 628: fid_max_class_count() -- max problems from any single class per fid.

FID-axis complement of class_max_fid_count (item 627).
For each fid, returns the highest number of problems contributed by any single class.
int.  Empty -> {}.  Pure; no I/O.

Discriminating tests:
  1. PRIMARY DISC.: keyed by fid (NOT class).
     fid 'f1' in class A 5 times, class B 2 times -> result['f1']==5.
     class-axis impl would key on class name; kills impl swapping axes.
  2. Single class per fid -> count equals total for that fid.
  3. Empty -> {}.
  4. Multiple fids computed independently.
  5. Returns int (not float, not label).
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import (
    Problem,
    fid_max_class_count,
)


def _p(cls: str, fid: str, sev: str) -> Problem:
    return Problem(problem_class=cls, finding_id=fid, severity=sev)


def test_fid_axis_not_class_axis_primary_discriminator() -> None:
    """PRIMARY DISC.: keyed by fid, NOT class.

    fid 'f1': class A=5, class B=2 -> max=5.
    Result key must be 'f1', not 'A'.
    Kills impl using class axis or returning class-keyed dict.
    """
    problems = [_p("A", "f1", "H")] * 5 + [_p("B", "f1", "L")] * 2
    result = fid_max_class_count(problems)
    assert isinstance(result, dict), "Must return dict; got " + repr(type(result))
    assert "f1" in result, f"fid 'f1' must be key; got {list(result)}"
    assert "A" not in result, f"class 'A' must NOT be key; got {list(result)}"
    assert result["f1"] == 5, (
        f"fid f1: A=5, B=2 -> max=5; got {result['f1']} "
        f"(7=total wrong, 'A'=label wrong, 3.5=avg wrong)"
    )
    assert isinstance(result["f1"], int), "Must return int; got " + type(result["f1"]).__name__


def test_single_class_per_fid_returns_total() -> None:
    """Single class per fid -> max = total count for that fid."""
    problems = [_p("A", "f2", "H")] * 4
    result = fid_max_class_count(problems)
    assert result["f2"] == 4, f"single class, 4 problems -> max=4; got {result['f2']}"


def test_empty_returns_empty_dict() -> None:
    """Empty -> {}."""
    assert fid_max_class_count([]) == {}


def test_multiple_fids_independent() -> None:
    """Multiple fids each get their own max independently.

    fid 'f3': A=3, B=1 -> max=3.
    fid 'f4': A=2, B=2 -> max=2.
    """
    problems = (
        [_p("A", "f3", "H")] * 3
        + [_p("B", "f3", "L")]
        + [_p("A", "f4", "H")] * 2
        + [_p("B", "f4", "L")] * 2
    )
    result = fid_max_class_count(problems)
    assert result["f3"] == 3, f"f3: A=3, B=1 -> max=3; got {result['f3']}"
    assert result["f4"] == 2, f"f4: A=2, B=2 -> max=2; got {result['f4']}"


def test_returns_int_not_float() -> None:
    """Return type must be int, not float."""
    problems = [_p("A", "f5", "H")] * 3 + [_p("B", "f5", "L")] * 2
    result = fid_max_class_count(problems)
    assert isinstance(result["f5"], int), (
        f"Must return int; got {type(result['f5']).__name__} = {result['f5']}"
    )
    assert result["f5"] == 3, f"A=3, B=2 -> max=3; got {result['f5']}"
