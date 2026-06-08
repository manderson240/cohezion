"""Item 639: class_problem_entropy() -- Shannon entropy of per-fid counts per class.

For each class, -sum(p_i * log2(p_i)) where p_i = fid_count_i / total_class_count.
0.0 = single fid; log2(N) = N perfectly equal fids.  float >= 0.0.  Empty -> {}.
Pure; no I/O.

Discriminating tests:
  1. PRIMARY DISC.: entropy != Gini; distinct values for same input.
     class A: f1=3, f2=1 -> p=[0.75,0.25],
     H = -(0.75*log2(0.75) + 0.25*log2(0.25)) ≈ 0.8113.
     Gini=0.375 wrong; CV wrong; kills Gini or CV impl.
  2. Single fid -> entropy=0.0.
  3. Two equal fids -> entropy=1.0 (log2(2)=1).
  4. Empty -> {}.
  5. Four equal fids -> entropy=2.0 (log2(4)=2).
"""

from __future__ import annotations

import math

from cohezion.compound.problem_discovery import (
    Problem,
    class_problem_entropy,
)


def _p(cls: str, fid: str, sev: str) -> Problem:
    return Problem(problem_class=cls, finding_id=fid, severity=sev)


def test_entropy_not_gini_primary_discriminator() -> None:
    """PRIMARY DISC.: entropy != Gini.

    class A: f1=3, f2=1 -> H≈0.8113, Gini=0.375.
    Kills impl returning Gini (0.375) or CV (~0.8 for different input).
    """
    problems = [_p("A", "f1", "H")] * 3 + [_p("A", "f2", "L")]
    result = class_problem_entropy(problems)
    assert isinstance(result, dict), "Must return dict; got " + repr(type(result))
    assert "A" in result, f"Class 'A' must be in result; got {list(result)}"
    expected = -(0.75 * math.log2(0.75) + 0.25 * math.log2(0.25))  # ≈ 0.8113
    assert abs(result["A"] - expected) < 1e-9, (
        f"f1=3,f2=1 -> H≈{expected:.4f}; got {result['A']} "
        f"(0.375=Gini wrong)"
    )


def test_single_fid_zero_entropy() -> None:
    """Single fid -> entropy=0.0 (p=1.0, log2(1)=0)."""
    problems = [_p("B", "f3", "H")] * 6
    result = class_problem_entropy(problems)
    assert "B" in result, f"Class 'B' must be present; got {list(result)}"
    assert abs(result["B"]) < 1e-9, f"Single-fid -> entropy=0.0; got {result['B']}"


def test_two_equal_fids_entropy_one() -> None:
    """Two equal fids -> entropy=1.0 (log2(2)=1)."""
    problems = [_p("C", "f4", "H")] * 5 + [_p("C", "f5", "L")] * 5
    result = class_problem_entropy(problems)
    assert "C" in result, f"Class 'C' must be present; got {list(result)}"
    assert abs(result["C"] - 1.0) < 1e-9, (
        f"Equal fids [5,5] -> entropy=1.0; got {result['C']}"
    )


def test_empty_returns_empty_dict() -> None:
    """Empty -> {}."""
    assert class_problem_entropy([]) == {}


def test_four_equal_fids_entropy_two() -> None:
    """Four equal fids -> entropy=2.0 (log2(4)=2)."""
    problems = (
        [_p("D", "f6", "H")]
        + [_p("D", "f7", "M")]
        + [_p("D", "f8", "L")]
        + [_p("D", "f9", "C")]
    )
    result = class_problem_entropy(problems)
    assert "D" in result, f"Class 'D' must be present; got {list(result)}"
    assert abs(result["D"] - 2.0) < 1e-9, (
        f"Four equal fids [1,1,1,1] -> entropy=2.0; got {result['D']}"
    )
