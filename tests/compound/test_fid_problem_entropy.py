"""Item 641: fid_problem_entropy() -- Shannon entropy of per-class counts per fid.

FID-axis complement of class_problem_entropy (item 639).
H = -sum(p_i * log2(p_i)) where p_i = class_count_i / total_fid_count.
0.0 = single class; log2(N) = N equal classes.  float >= 0.0.  Empty -> {}.
"""

from __future__ import annotations

import math

from cohezion.compound.problem_discovery import Problem, fid_problem_entropy


def _p(cls: str, fid: str) -> Problem:
    return Problem(problem_class=cls, finding_id=fid, severity="HIGH")


def test_fid_axis_not_class_axis_primary_discriminator() -> None:
    """PRIMARY DISC.: keyed by fid NOT class; entropy != Gini != CV.

    fid 'f1': class A=3, B=1 -> p=[0.75, 0.25], H≈0.8113.
    Key must be 'f1', NOT 'A'. class-axis kills; Gini=0.375 kills.
    """
    problems = [_p("A", "f1")] * 3 + [_p("B", "f1")]
    result = fid_problem_entropy(problems)
    assert isinstance(result, dict), "Must return dict"
    assert "f1" in result, f"fid 'f1' must be key; got {list(result)}"
    assert "A" not in result, f"class 'A' must NOT be key; got {list(result)}"
    expected = -(0.75 * math.log2(0.75) + 0.25 * math.log2(0.25))
    assert abs(result["f1"] - expected) < 1e-9, (
        f"A=3,B=1 -> H≈0.8113; got {result['f1']} (class-axis wrong, Gini=0.375 wrong)"
    )
    assert isinstance(result["f1"], float), "Must be float"


def test_single_class_zero_entropy() -> None:
    """Single class per fid -> H=0.0."""
    problems = [_p("A", "f2")] * 5
    result = fid_problem_entropy(problems)
    assert "f2" in result, f"fid 'f2' must be present"
    assert abs(result["f2"]) < 1e-9, f"Single-class -> H=0.0; got {result['f2']}"


def test_two_equal_classes_one_bit_entropy() -> None:
    """Two equal classes -> H=1.0 bit (p=[0.5,0.5])."""
    problems = [_p("A", "f3")] * 4 + [_p("B", "f3")] * 4
    result = fid_problem_entropy(problems)
    assert "f3" in result
    assert abs(result["f3"] - 1.0) < 1e-9, f"Equal classes [4,4] -> H=1.0; got {result['f3']}"


def test_empty_returns_empty_dict() -> None:
    """Empty -> {}."""
    assert fid_problem_entropy([]) == {}


def test_multiple_fids_independent() -> None:
    """Multiple fids each get independent entropy.

    fid 'f4': A=1 -> H=0.0.
    fid 'f5': A=3, B=3 -> H=1.0 bit.
    """
    problems = [_p("A", "f4")] + [_p("A", "f5")] * 3 + [_p("B", "f5")] * 3
    result = fid_problem_entropy(problems)
    assert abs(result["f4"]) < 1e-9, f"f4 single-class -> H=0.0; got {result['f4']}"
    assert abs(result["f5"] - 1.0) < 1e-9, f"f5 equal classes -> H=1.0; got {result['f5']}"
