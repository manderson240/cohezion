"""Item 626: fid_severity_cv() -- FID-axis coefficient of variation of severity counts.

FID-axis complement of class_severity_cv (item 625).
CV = population_std_dev / mean of the per-severity INTEGER counts per fid.
0.0 = uniform or single-severity.  float >= 0.0.  Empty -> {}.  Pure; no I/O.

Discriminating tests:
  1. PRIMARY DISC.: keyed by fid (NOT class).
     fid 'f1' HIGH=4, LOW=1 -> counts=[4,1], mean=2.5, std=1.5, cv=0.6.
     class-axis impl would key on class name; kills impl reusing class_severity_cv.
  2. Uniform distribution -> CV=0.0 (std=0).
  3. Single-severity -> CV=0.0.
  4. Empty -> {}.
  5. Three-severity: fid counts=[3,2,1], mean=2, std=sqrt(2/3), cv=sqrt(2/3)/2.
"""

from __future__ import annotations

import math

from cohezion.compound.problem_discovery import (
    Problem,
    fid_severity_cv,
)


def _p(cls: str, fid: str, sev: str) -> Problem:
    return Problem(problem_class=cls, finding_id=fid, severity=sev)


def test_fid_axis_not_class_axis_primary_discriminator() -> None:
    """PRIMARY DISC.: keyed by fid, NOT class.

    fid 'f1': HIGH=4, LOW=1 -> counts=[4,1], mean=2.5, std=1.5, cv=0.6.
    Result key must be 'f1', not the class name.
    Kills impl using class axis or calling class_severity_cv.
    """
    problems = [_p("A", "f1", "HIGH")] * 4 + [_p("A", "f1", "LOW")]
    result = fid_severity_cv(problems)
    assert isinstance(result, dict), "Must return dict; got " + repr(type(result))
    assert "f1" in result, f"fid 'f1' must be key; got {list(result)}"
    assert "A" not in result, f"class 'A' must NOT be key; got {list(result)}"
    expected = 1.5 / 2.5  # 0.6
    assert abs(result["f1"] - expected) < 1e-9, (
        f"HIGH=4,LOW=1 -> cv=1.5/2.5=0.6; got {result['f1']} "
        f"(class-axis would key on 'A', not 'f1')"
    )


def test_uniform_distribution_zero_cv() -> None:
    """Uniform distribution -> CV=0.0 (std=0 -> cv=0)."""
    problems = [_p("A", "f2", "HIGH")] * 3 + [_p("A", "f2", "LOW")] * 3
    result = fid_severity_cv(problems)
    assert abs(result["f2"]) < 1e-9, f"Uniform [3,3] -> cv=0.0; got {result['f2']}"


def test_single_severity_zero_cv() -> None:
    """Single severity -> CV=0.0."""
    problems = [_p("A", "f3", "CRITICAL")] * 7
    result = fid_severity_cv(problems)
    assert abs(result["f3"]) < 1e-9, f"Single-severity -> cv=0.0; got {result['f3']}"


def test_empty_returns_empty_dict() -> None:
    """Empty -> {}."""
    assert fid_severity_cv([]) == {}


def test_three_severity_cv() -> None:
    """fid counts=[3,2,1], mean=2, std=sqrt(2/3), cv=sqrt(2/3)/2."""
    problems = [_p("A", "f4", "HIGH")] * 3 + [_p("A", "f4", "MED")] * 2 + [_p("A", "f4", "LOW")]
    result = fid_severity_cv(problems)
    expected = math.sqrt(2.0 / 3.0) / 2.0
    assert abs(result["f4"] - expected) < 1e-9, (
        f"counts=[3,2,1], cv=sqrt(2/3)/2={expected:.6f}; got {result['f4']}"
    )
