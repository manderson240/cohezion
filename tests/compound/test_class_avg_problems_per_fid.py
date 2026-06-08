"""Item 675: class_avg_problems_per_fid() -- avg problem count per (class, fid) cell, per class.

For each class: mean(cell_count) over all fids in that class.
float.  Returns {class: avg}.  Empty -> {}.  Pure; no I/O.

Discriminating tests:
  1. PRIMARY DISC.: average is per-fid-cell NOT total count per class.
     class A: f1×5 f2×1 f3×4 -> avg=(5+1+4)/3=3.33... (total=10 wrong, distinct-fid-count=3 wrong).
  2. Single fid -> avg = total problems (same cell is the only cell).
  3. Empty -> {}.
  4. Multiple classes computed independently.
  5. Return type is float.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import Problem, class_avg_problems_per_fid


def _p(cls: str, fid: str) -> Problem:
    return Problem(problem_class=cls, finding_id=fid, severity="HIGH")


def test_avg_per_fid_not_total_count_primary_discriminator() -> None:
    """PRIMARY DISC.: avg = mean(cell_counts) NOT total count NOT distinct-fid count.

    class A: f1×5, f2×1, f3×4 -> avg=(5+1+4)/3=10/3≈3.333.
    total=10 wrong; distinct-fid-count=3 wrong.
    """
    problems = [_p("A", "f1")] * 5 + [_p("A", "f2")] * 1 + [_p("A", "f3")] * 4
    result = class_avg_problems_per_fid(problems)
    assert isinstance(result, dict), "Must return dict"
    assert "A" in result, f"Class 'A' must be present; got {list(result)}"
    expected = (5 + 1 + 4) / 3
    assert abs(result["A"] - expected) < 1e-9, (
        f"(5+1+4)/3={expected:.4f}; got {result['A']:.4f} (total=10 wrong, count=3 wrong)"
    )
    assert isinstance(result["A"], float), "Must be float"


def test_single_fid_avg_equals_count() -> None:
    """Single fid -> avg = number of problems for that fid (only one cell)."""
    problems = [_p("B", "f1")] * 7
    result = class_avg_problems_per_fid(problems)
    assert abs(result["B"] - 7.0) < 1e-9, f"7 problems, 1 fid -> avg=7.0; got {result['B']}"


def test_empty_returns_empty_dict() -> None:
    """Empty -> {}."""
    assert class_avg_problems_per_fid([]) == {}


def test_multiple_classes_independent() -> None:
    """Different classes get independent averages."""
    problems = (
        [_p("A", "fa")] * 3
        + [_p("A", "fb")] * 3  # A avg=3.0
        + [_p("B", "fc")] * 10
        + [_p("B", "fd")] * 2  # B avg=6.0
    )
    result = class_avg_problems_per_fid(problems)
    assert abs(result["A"] - 3.0) < 1e-9, f"A avg=3.0; got {result.get('A')}"
    assert abs(result["B"] - 6.0) < 1e-9, f"B avg=6.0; got {result.get('B')}"


def test_return_type_is_float() -> None:
    """Result values must be float not int."""
    result = class_avg_problems_per_fid([_p("Z", "f1")] * 4 + [_p("Z", "f2")] * 4)
    assert isinstance(result["Z"], float), f"Must be float; got {type(result['Z'])}"
