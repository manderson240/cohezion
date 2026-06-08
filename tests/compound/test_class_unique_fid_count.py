"""Item 644: class_unique_fid_count() -- distinct fid count per class.

For each class, count of distinct finding_ids.
int >= 1.  Empty -> {}.  Pure; no I/O.

Discriminating tests:
  1. PRIMARY DISC.: counts DISTINCT fids not total problems.
     class A: f1, f1, f2 -> 2 (not 3); kills impl counting total problems.
  2. Single problem per class -> 1.
  3. Empty -> {}.
  4. Multiple classes independent.
  5. Returns int (not float).
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import (
    Problem,
    class_unique_fid_count,
)


def _p(cls: str, fid: str, sev: str) -> Problem:
    return Problem(problem_class=cls, finding_id=fid, severity=sev)


def test_distinct_not_total_primary_discriminator() -> None:
    """PRIMARY DISC.: counts distinct fids, NOT total problems.

    class A: f1 appears twice, f2 once -> 2 distinct (not 3 total).
    Kills impl returning total problem count.
    """
    problems = [_p("A", "f1", "H"), _p("A", "f1", "H"), _p("A", "f2", "L")]
    result = class_unique_fid_count(problems)
    assert isinstance(result, dict), "Must return dict; got " + repr(type(result))
    assert "A" in result, f"Class 'A' must be in result; got {list(result)}"
    assert result["A"] == 2, f"f1×2 + f2×1 -> 2 distinct fids (not 3 total); got {result['A']}"
    assert isinstance(result["A"], int), f"Must return int; got {type(result['A']).__name__}"


def test_single_problem_returns_one() -> None:
    """Single problem -> 1 distinct fid."""
    problems = [_p("B", "f3", "H")]
    result = class_unique_fid_count(problems)
    assert result["B"] == 1, f"Single problem -> 1 fid; got {result['B']}"


def test_empty_returns_empty_dict() -> None:
    """Empty -> {}."""
    assert class_unique_fid_count([]) == {}


def test_multiple_classes_independent() -> None:
    """Multiple classes each counted independently.

    class A: f1, f2, f3 -> 3.
    class B: f1, f1 -> 1 (f1 repeated).
    """
    problems = [_p("A", "f1", "H"), _p("A", "f2", "M"), _p("A", "f3", "L")] + [
        _p("B", "f1", "H"),
        _p("B", "f1", "L"),
    ]
    result = class_unique_fid_count(problems)
    assert result["A"] == 3, f"A: f1+f2+f3 -> 3; got {result['A']}"
    assert result["B"] == 1, f"B: f1+f1 -> 1 (distinct); got {result['B']}"


def test_returns_int() -> None:
    """Return type must be int, not float."""
    problems = [_p("C", "f4", "H")] * 5 + [_p("C", "f5", "L")] * 3
    result = class_unique_fid_count(problems)
    assert isinstance(result["C"], int), f"Must be int; got {type(result['C']).__name__}"
    assert result["C"] == 2, f"f4+f5 -> 2 distinct; got {result['C']}"
