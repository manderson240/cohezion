"""Item 645: fid_unique_class_count() -- distinct class count per fid.

FID-axis complement of class_unique_fid_count (item 644).
For each fid, count of distinct problem_classes.
int >= 1.  Empty -> {}.  Pure; no I/O.

Discriminating tests:
  1. PRIMARY DISC.: keyed by fid NOT class; counts DISTINCT classes not total problems.
     fid 'f1': class A twice, class B once -> 2 distinct (not 3 total).
     class-axis would key on 'A'; kills class-axis or total-count impl.
  2. Single problem -> 1 distinct class.
  3. Empty -> {}.
  4. Multiple fids independent.
  5. Returns int (not float).
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import (
    Problem,
    fid_unique_class_count,
)


def _p(cls: str, fid: str, sev: str) -> Problem:
    return Problem(problem_class=cls, finding_id=fid, severity=sev)


def test_fid_axis_distinct_not_total_primary_discriminator() -> None:
    """PRIMARY DISC.: keyed by fid; counts distinct classes not total.

    fid 'f1': A×2, B×1 -> 2 distinct (not 3 total).
    class-axis would key on 'A'; kills either wrong impl.
    """
    problems = [_p("A", "f1", "H"), _p("A", "f1", "H"), _p("B", "f1", "L")]
    result = fid_unique_class_count(problems)
    assert isinstance(result, dict), "Must return dict; got " + repr(type(result))
    assert "f1" in result, f"fid 'f1' must be key; got {list(result)}"
    assert "A" not in result, f"class 'A' must NOT be key; got {list(result)}"
    assert result["f1"] == 2, f"A×2 + B×1 -> 2 distinct classes (not 3 total); got {result['f1']}"
    assert isinstance(result["f1"], int), f"Must be int; got {type(result['f1']).__name__}"


def test_single_problem_returns_one() -> None:
    """Single problem -> 1 distinct class."""
    problems = [_p("A", "f2", "H")]
    result = fid_unique_class_count(problems)
    assert result["f2"] == 1, f"Single problem -> 1 class; got {result['f2']}"


def test_empty_returns_empty_dict() -> None:
    """Empty -> {}."""
    assert fid_unique_class_count([]) == {}


def test_multiple_fids_independent() -> None:
    """Multiple fids each counted independently.

    fid 'f3': A, B, C -> 3 distinct.
    fid 'f4': A, A -> 1 distinct (A repeated).
    """
    problems = [_p("A", "f3", "H"), _p("B", "f3", "M"), _p("C", "f3", "L")] + [
        _p("A", "f4", "H"),
        _p("A", "f4", "L"),
    ]
    result = fid_unique_class_count(problems)
    assert result["f3"] == 3, f"f3: A+B+C -> 3; got {result['f3']}"
    assert result["f4"] == 1, f"f4: A+A -> 1; got {result['f4']}"


def test_returns_int() -> None:
    """Return type must be int."""
    problems = [_p("A", "f5", "H")] * 3 + [_p("B", "f5", "L")] * 2
    result = fid_unique_class_count(problems)
    assert isinstance(result["f5"], int), f"Must be int; got {type(result['f5']).__name__}"
    assert result["f5"] == 2, f"A+B -> 2 distinct; got {result['f5']}"
