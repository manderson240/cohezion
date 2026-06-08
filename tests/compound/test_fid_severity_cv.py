"""Item 626: fid_severity_cv() -- coefficient of variation of severity counts per fid.

FID-axis complement of class_severity_cv (item 625).
CV = population_std_dev / mean of the per-severity INTEGER counts for each fid.
float >= 0.0.  Empty -> {}.  Pure; no I/O.

Discriminating tests:
  1. PRIMARY DISC.: keyed by fid NOT class.
     fid 'f1': HIGH=4, LOW=1 -> counts=[4,1], mean=2.5, std=1.5, cv=0.6.
     Result key must be 'f1' (fid), not 'A' (class).
     Kills impl using class axis or calling class_severity_cv.
  2. Uniform distribution -> CV=0.0 (std=0).
  3. Single-severity -> CV=0.0 (std=0).
  4. Empty -> {}.
  5. Multiple fids computed independently.
"""

from __future__ import annotations

import math

from cohezion.compound.problem_discovery import Problem, fid_severity_cv


def _p(cls: str, fid: str, sev: str) -> Problem:
    return Problem(problem_class=cls, finding_id=fid, severity=sev)


def test_fid_axis_cv_primary_discriminator() -> None:
    """PRIMARY DISC.: keyed by fid NOT class; uses per-fid severity counts.

    fid 'f1': HIGH=4, LOW=1 -> counts=[4,1], mean=2.5, std=sqrt(2.25)=1.5, cv=0.6.
    Result key must be 'f1', not 'A'. Kills impl using class axis.
    """
    problems = [_p("A", "f1", "HIGH")] * 4 + [_p("A", "f1", "LOW")]
    result = fid_severity_cv(problems)
    assert isinstance(result, dict), "Must return dict"
    assert "f1" in result, f"fid 'f1' must be key; got {list(result)}"
    assert "A" not in result, f"class 'A' must NOT be key; got {list(result)}"
    expected = 1.5 / 2.5  # 0.6
    assert abs(result["f1"] - expected) < 1e-9, (
        f"HIGH=4,LOW=1 -> cv=0.6; got {result['f1']} (kills class-axis impl)"
    )
    assert isinstance(result["f1"], float), "Must be float; got " + type(result["f1"]).__name__


def test_uniform_distribution_zero_cv() -> None:
    """Uniform severity distribution -> CV=0.0 (std=0)."""
    problems = [_p("A", "f1", "HIGH")] * 3 + [_p("A", "f1", "LOW")] * 3
    result = fid_severity_cv(problems)
    assert abs(result["f1"]) < 1e-9, f"Uniform [3,3] -> cv=0.0; got {result['f1']}"


def test_single_severity_zero_cv() -> None:
    """Single severity bucket -> CV=0.0 (std=0, mean=count)."""
    problems = [_p("B", "f2", "CRITICAL")] * 7
    result = fid_severity_cv(problems)
    assert abs(result["f2"]) < 1e-9, f"Single-severity -> cv=0.0; got {result['f2']}"


def test_empty_returns_empty_dict() -> None:
    """Empty -> {}."""
    assert fid_severity_cv([]) == {}


def test_multiple_fids_independent_cvs() -> None:
    """Multiple fids each computed independently.

    fid 'f1': HIGH=3, MED=2, LOW=1 -> mean=2, std=sqrt(2/3), cv=sqrt(2/3)/2.
    fid 'f2': HIGH=5, LOW=5 -> uniform -> cv=0.0.
    """
    problems = (
        [_p("A", "f1", "HIGH")] * 3 + [_p("A", "f1", "MED")] * 2 + [_p("A", "f1", "LOW")]
        + [_p("B", "f2", "HIGH")] * 5 + [_p("B", "f2", "LOW")] * 5
    )
    result = fid_severity_cv(problems)
    expected_f1 = math.sqrt(2.0 / 3.0) / 2.0
    assert abs(result["f1"] - expected_f1) < 1e-9, (
        f"f1: counts=[3,2,1], cv=sqrt(2/3)/2={expected_f1:.6f}; got {result['f1']}"
    )
    assert abs(result["f2"]) < 1e-9, f"f2: uniform [5,5] -> cv=0.0; got {result['f2']}"
