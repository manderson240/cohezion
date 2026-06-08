"""Item 646: class_total_problems() -- total problem count per class.

For each class, count ALL problems including duplicates.
int >= 1.  Empty -> {}.  Pure; no I/O.

Discriminating tests:
  1. PRIMARY DISC.: counts ALL problems including duplicates (NOT distinct fids).
     class A: f1, f1, f2 -> 3 (not 2 distinct fids).
     Kills distinct-count impl (class_unique_fid_count).
  2. Single problem -> 1.
  3. Empty -> {}.
  4. Multiple classes independent.
  5. Returns int (not float).
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import (
    Problem,
    class_total_problems,
)


def _p(cls: str, fid: str, sev: str) -> Problem:
    return Problem(problem_class=cls, finding_id=fid, severity=sev)


def test_total_not_distinct_primary_discriminator() -> None:
    """PRIMARY DISC.: counts total problems NOT distinct fids.

    class A: f1, f1, f2 -> 3 total (not 2 distinct fids).
    Kills class_unique_fid_count impl which would return 2.
    """
    problems = [_p("A", "f1", "H"), _p("A", "f1", "H"), _p("A", "f2", "L")]
    result = class_total_problems(problems)
    assert isinstance(result, dict), "Must return dict; got " + repr(type(result))
    assert "A" in result, f"Class 'A' must be in result; got {list(result)}"
    assert result["A"] == 3, (
        f"f1×2 + f2×1 -> 3 total (not 2 distinct); got {result['A']}"
    )
    assert isinstance(result["A"], int), f"Must be int; got {type(result['A']).__name__}"


def test_single_problem_returns_one() -> None:
    """Single problem -> 1."""
    problems = [_p("B", "f3", "H")]
    result = class_total_problems(problems)
    assert result["B"] == 1, f"Single problem -> 1; got {result['B']}"


def test_empty_returns_empty_dict() -> None:
    """Empty -> {}."""
    assert class_total_problems([]) == {}


def test_multiple_classes_independent() -> None:
    """Multiple classes each counted independently."""
    problems = (
        [_p("A", "f1", "H")] * 4
        + [_p("B", "f2", "L")] * 2
        + [_p("B", "f3", "M")]
    )
    result = class_total_problems(problems)
    assert result["A"] == 4, f"A: 4 problems; got {result['A']}"
    assert result["B"] == 3, f"B: 3 problems; got {result['B']}"


def test_returns_int() -> None:
    """Return type must be int."""
    problems = [_p("C", "f4", "H")] * 7
    result = class_total_problems(problems)
    assert isinstance(result["C"], int), f"Must be int; got {type(result['C']).__name__}"
    assert result["C"] == 7, f"7 problems -> 7; got {result['C']}"
