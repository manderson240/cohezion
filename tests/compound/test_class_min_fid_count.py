"""Item 629: class_min_fid_count() -- min problems from any single fid per class.

For each class, returns the lowest per-fid problem count.
Complement of class_max_fid_count (item 627): together they bound the per-fid range.
int.  Empty -> {}.  Pure; no I/O.

Discriminating tests:
  1. PRIMARY DISC.: returns MIN not MAX.
     class A with f1=5, f2=2 -> result['A']==2 (min), not 5 (max), not 7 (total).
     Kills impl reusing class_max_fid_count or returning total.
  2. Single fid per class -> that fid's count.
  3. Empty -> {}.
  4. Multiple classes computed independently.
  5. Returns int (not float, not fid label).
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import (
    Problem,
    class_min_fid_count,
)


def _p(cls: str, fid: str, sev: str) -> Problem:
    return Problem(problem_class=cls, finding_id=fid, severity=sev)


def test_returns_min_not_max_primary_discriminator() -> None:
    """PRIMARY DISC.: returns min count (not max, not total).

    class A: f1=5, f2=2 -> min=2.
    max would give 5; total would give 7.
    Kills impl reusing class_max_fid_count or summing.
    """
    problems = [_p("A", "f1", "H")] * 5 + [_p("A", "f2", "L")] * 2
    result = class_min_fid_count(problems)
    assert isinstance(result, dict), "Must return dict; got " + repr(type(result))
    assert "A" in result, f"Class 'A' must be in result; got {list(result)}"
    assert result["A"] == 2, f"f1=5, f2=2 -> min=2; got {result['A']} (5=max wrong, 7=total wrong)"
    assert isinstance(result["A"], int), "Must return int; got " + type(result["A"]).__name__


def test_single_fid_per_class_returns_its_count() -> None:
    """Single fid per class -> that fid's count is both min and max."""
    problems = [_p("B", "f3", "H")] * 4
    result = class_min_fid_count(problems)
    assert result["B"] == 4, f"single fid, 4 problems -> min=4; got {result['B']}"


def test_empty_returns_empty_dict() -> None:
    """Empty -> {}."""
    assert class_min_fid_count([]) == {}


def test_multiple_classes_computed_independently() -> None:
    """Multiple classes each get their own min.

    class A: f1=3, f2=1 -> min=1.
    class B: f3=2, f4=2 -> min=2 (uniform).
    """
    problems = (
        [_p("A", "f1", "H")] * 3
        + [_p("A", "f2", "L")]
        + [_p("B", "f3", "H")] * 2
        + [_p("B", "f4", "L")] * 2
    )
    result = class_min_fid_count(problems)
    assert result["A"] == 1, f"A: f1=3, f2=1 -> min=1; got {result['A']}"
    assert result["B"] == 2, f"B: f3=2, f4=2 -> min=2; got {result['B']}"


def test_returns_int_not_float() -> None:
    """Return type must be int."""
    problems = [_p("C", "f5", "H")] * 3 + [_p("C", "f6", "L")] * 5
    result = class_min_fid_count(problems)
    assert isinstance(result["C"], int), (
        f"Must return int; got {type(result['C']).__name__} = {result['C']}"
    )
    assert result["C"] == 3, f"f5=3, f6=5 -> min=3; got {result['C']}"
