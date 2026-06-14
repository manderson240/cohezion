"""Item 636: fid_class_count_cv() -- CV of per-class problem counts per fid.

FID-axis complement of class_fid_count_cv (item 635).
CV = population_std_dev / mean of per-class INTEGER problem counts per fid.
0.0 = all classes equal or single-class.  float >= 0.0.  Empty -> {}.
Pure; no I/O.

Discriminating tests:
  1. PRIMARY DISC.: keyed by fid NOT class.
     fid 'f1': class A=4, class B=1 -> counts=[4,1], mean=2.5, std=1.5, cv=0.6.
     class-axis impl would key on class name; kills impl using class axis.
  2. Uniform classes -> CV=0.0.
  3. Single class per fid -> CV=0.0.
  4. Empty -> {}.
  5. Three-class: A=3, B=2, C=1 -> mean=2, std=sqrt(2/3), cv=sqrt(2/3)/2.
"""

from __future__ import annotations

import math

from cohezion.compound.problem_discovery import (
    Problem,
    fid_class_count_cv,
)


def _p(cls: str, fid: str, sev: str) -> Problem:
    return Problem(problem_class=cls, finding_id=fid, severity=sev)


def test_fid_axis_not_class_axis_primary_discriminator() -> None:
    """PRIMARY DISC.: keyed by fid, NOT class.

    fid 'f1': class A=4, class B=1 -> cv=0.6.
    Key must be 'f1', not 'A'.  class-axis wrong.
    """
    problems = [_p("A", "f1", "H")] * 4 + [_p("B", "f1", "L")]
    result = fid_class_count_cv(problems)
    assert isinstance(result, dict), "Must return dict; got " + repr(type(result))
    assert "f1" in result, f"fid 'f1' must be key; got {list(result)}"
    assert "A" not in result, f"class 'A' must NOT be key; got {list(result)}"
    expected = 1.5 / 2.5  # 0.6
    assert abs(result["f1"] - expected) < 1e-9, (
        f"A=4,B=1 -> cv=0.6; got {result['f1']} (class-axis wrong)"
    )


def test_uniform_classes_zero_cv() -> None:
    """Uniform class counts -> CV=0.0."""
    problems = [_p("A", "f2", "H")] * 3 + [_p("B", "f2", "L")] * 3
    result = fid_class_count_cv(problems)
    assert "f2" in result, f"fid 'f2' must be present; got {list(result)}"
    assert abs(result["f2"]) < 1e-9, f"Uniform [3,3] -> cv=0.0; got {result['f2']}"


def test_single_class_zero_cv() -> None:
    """Single class per fid -> CV=0.0."""
    problems = [_p("A", "f3", "H")] * 5
    result = fid_class_count_cv(problems)
    assert "f3" in result, f"fid 'f3' must be present; got {list(result)}"
    assert abs(result["f3"]) < 1e-9, f"Single-class -> cv=0.0; got {result['f3']}"


def test_empty_returns_empty_dict() -> None:
    """Empty -> {}."""
    assert fid_class_count_cv([]) == {}


def test_three_class_cv() -> None:
    """Three classes: A=3, B=2, C=1 -> mean=2, std=sqrt(2/3), cv=sqrt(2/3)/2."""
    problems = [_p("A", "f4", "H")] * 3 + [_p("B", "f4", "M")] * 2 + [_p("C", "f4", "L")]
    result = fid_class_count_cv(problems)
    expected = math.sqrt(2.0 / 3.0) / 2.0
    assert abs(result["f4"] - expected) < 1e-9, (
        f"counts=[3,2,1], cv=sqrt(2/3)/2={expected:.6f}; got {result['f4']}"
    )
