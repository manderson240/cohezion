"""Item 637: class_fid_gini() -- Gini impurity of per-fid counts per class.

For each class, 1 - sum(p_i^2) where p_i = fid_count_i / total_class_count.
0.0 = single fid dominates; approaches 1.0 = perfectly uniform.
float in [0, 1).  Empty -> {}.  Pure; no I/O.

Discriminating tests:
  1. PRIMARY DISC.: Gini != CV, != range, != variance.
     class A: f1=3, f2=1 -> p=[0.75, 0.25], gini=1-(0.5625+0.0625)=0.375.
     CV=0.8 wrong; range=2 wrong; kills impl returning CV or range.
  2. Single fid -> Gini=0.0 (p=1.0, gini=1-1=0).
  3. Two equal fids -> Gini=0.5 (p=[0.5,0.5], gini=1-0.5=0.5).
  4. Empty -> {}.
  5. Result is float in [0, 1).
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import (
    Problem,
    class_fid_gini,
)


def _p(cls: str, fid: str, sev: str) -> Problem:
    return Problem(problem_class=cls, finding_id=fid, severity=sev)


def test_gini_not_cv_not_range_primary_discriminator() -> None:
    """PRIMARY DISC.: Gini != CV, != range.

    class A: f1=3, f2=1 -> p=[0.75,0.25], gini=1-(0.5625+0.0625)=0.375.
    CV = (std/mean) would give ~0.8; range=2.  Kills CV or range impls.
    """
    problems = [_p("A", "f1", "H")] * 3 + [_p("A", "f2", "L")]
    result = class_fid_gini(problems)
    assert isinstance(result, dict), "Must return dict; got " + repr(type(result))
    assert "A" in result, f"Class 'A' must be in result; got {list(result)}"
    expected = 1.0 - (0.75**2 + 0.25**2)  # = 0.375
    assert abs(result["A"] - expected) < 1e-9, (
        f"f1=3,f2=1 -> gini=0.375; got {result['A']} (CV≈0.8 wrong, range=2 wrong)"
    )


def test_single_fid_zero_gini() -> None:
    """Single fid -> Gini=0.0 (p=1.0 -> 1-1=0)."""
    problems = [_p("B", "f3", "H")] * 5
    result = class_fid_gini(problems)
    assert "B" in result, f"Class 'B' must be present; got {list(result)}"
    assert abs(result["B"]) < 1e-9, f"Single-fid -> gini=0.0; got {result['B']}"


def test_two_equal_fids_half_gini() -> None:
    """Two equally-sized fids -> Gini=0.5."""
    problems = [_p("C", "f4", "H")] * 4 + [_p("C", "f5", "L")] * 4
    result = class_fid_gini(problems)
    assert "C" in result, f"Class 'C' must be present; got {list(result)}"
    assert abs(result["C"] - 0.5) < 1e-9, f"Equal fids [4,4] -> gini=0.5; got {result['C']}"


def test_empty_returns_empty_dict() -> None:
    """Empty -> {}."""
    assert class_fid_gini([]) == {}


def test_result_float_in_zero_one() -> None:
    """Result is float in [0, 1)."""
    problems = [_p("D", "f6", "H")] * 3 + [_p("D", "f7", "L")] * 2
    result = class_fid_gini(problems)
    assert "D" in result, "Class 'D' must be present"
    v = result["D"]
    assert isinstance(v, float), f"Must return float; got {type(v).__name__}"
    assert 0.0 <= v < 1.0, f"Gini must be in [0, 1); got {v}"
