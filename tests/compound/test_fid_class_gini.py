"""Item 638: fid_class_gini() -- Gini impurity of per-class counts per fid.

FID-axis complement of class_fid_gini (item 637).
Gini = 1 - sum(p_i^2) where p_i = class_count_i / total_fid_count.
0.0 = single class dominates; approaches 1.0 = perfectly uniform.
float in [0, 1).  Empty -> {}.  Pure; no I/O.

Discriminating tests:
  1. PRIMARY DISC.: keyed by fid NOT class.
     fid 'f1': class A=3, class B=1 -> p=[0.75,0.25], gini=0.375.
     class-axis would key on 'A'; kills impl using class axis.
  2. Single class -> Gini=0.0.
  3. Two equal classes -> Gini=0.5.
  4. Empty -> {}.
  5. Result float in [0, 1).
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import (
    Problem,
    fid_class_gini,
)


def _p(cls: str, fid: str, sev: str) -> Problem:
    return Problem(problem_class=cls, finding_id=fid, severity=sev)


def test_fid_axis_not_class_axis_primary_discriminator() -> None:
    """PRIMARY DISC.: keyed by fid, NOT class.

    fid 'f1': class A=3, class B=1 -> gini=0.375.
    Key must be 'f1', not 'A'.
    """
    problems = [_p("A", "f1", "H")] * 3 + [_p("B", "f1", "L")]
    result = fid_class_gini(problems)
    assert isinstance(result, dict), "Must return dict; got " + repr(type(result))
    assert "f1" in result, f"fid 'f1' must be key; got {list(result)}"
    assert "A" not in result, f"class 'A' must NOT be key; got {list(result)}"
    expected = 1.0 - (0.75**2 + 0.25**2)  # = 0.375
    assert abs(result["f1"] - expected) < 1e-9, (
        f"A=3,B=1 -> gini=0.375; got {result['f1']} (class-axis would key on 'A')"
    )


def test_single_class_zero_gini() -> None:
    """Single class per fid -> Gini=0.0."""
    problems = [_p("A", "f2", "H")] * 5
    result = fid_class_gini(problems)
    assert "f2" in result, f"fid 'f2' must be present; got {list(result)}"
    assert abs(result["f2"]) < 1e-9, f"Single-class -> gini=0.0; got {result['f2']}"


def test_two_equal_classes_half_gini() -> None:
    """Two equally-sized classes -> Gini=0.5."""
    problems = [_p("A", "f3", "H")] * 3 + [_p("B", "f3", "L")] * 3
    result = fid_class_gini(problems)
    assert "f3" in result, f"fid 'f3' must be present; got {list(result)}"
    assert abs(result["f3"] - 0.5) < 1e-9, f"Equal classes [3,3] -> gini=0.5; got {result['f3']}"


def test_empty_returns_empty_dict() -> None:
    """Empty -> {}."""
    assert fid_class_gini([]) == {}


def test_result_float_in_zero_one() -> None:
    """Result is float in [0, 1)."""
    problems = [_p("A", "f4", "H")] * 4 + [_p("B", "f4", "L")] * 2
    result = fid_class_gini(problems)
    assert "f4" in result, "fid 'f4' must be present"
    v = result["f4"]
    assert isinstance(v, float), f"Must return float; got {type(v).__name__}"
    assert 0.0 <= v < 1.0, f"Gini must be in [0, 1); got {v}"
