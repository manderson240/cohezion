"""Item 635: class_fid_count_cv() -- CV of per-fid problem counts per class.

CV = population_std_dev / mean of per-fid INTEGER problem counts per class.
0.0 = all fids contribute equally or single-fid.  float >= 0.0.  Empty -> {}.
Pure; no I/O.

Discriminating tests:
  1. PRIMARY DISC.: CV = std/mean of per-fid counts (NOT range, NOT gini, NOT variance).
     class A: f1=4, f2=1 -> counts=[4,1], mean=2.5, std=1.5, cv=0.6.
     range=3 wrong; variance=2.25 wrong; gini≈0.32 wrong.
     Kills impl returning range or variance.
  2. Uniform fids -> CV=0.0 (std=0).
  3. Single fid -> CV=0.0.
  4. Empty -> {}.
  5. Three-fid: f1=3, f2=2, f3=1 -> mean=2, std=sqrt(2/3), cv=sqrt(2/3)/2.
"""

from __future__ import annotations

import math

from cohezion.compound.problem_discovery import (
    Problem,
    class_fid_count_cv,
)


def _p(cls: str, fid: str, sev: str) -> Problem:
    return Problem(problem_class=cls, finding_id=fid, severity=sev)


def test_cv_not_range_not_variance_primary_discriminator() -> None:
    """PRIMARY DISC.: CV = std/mean of per-fid counts, not range, not variance.

    class A: f1=4, f2=1 -> counts=[4,1], mean=2.5, std=1.5, cv=0.6.
    range=3 wrong; variance=2.25 wrong; cv is 0.6.
    """
    problems = [_p("A", "f1", "H")] * 4 + [_p("A", "f2", "L")]
    result = class_fid_count_cv(problems)
    assert isinstance(result, dict), "Must return dict; got " + repr(type(result))
    assert "A" in result, f"Class 'A' must be in result; got {list(result)}"
    expected = 1.5 / 2.5  # 0.6
    assert abs(result["A"] - expected) < 1e-9, (
        f"f1=4,f2=1 -> cv=1.5/2.5=0.6; got {result['A']} (3.0=range wrong, 2.25=variance wrong)"
    )


def test_uniform_fids_zero_cv() -> None:
    """Uniform distribution of fid counts -> CV=0.0 (std=0)."""
    problems = [_p("B", "f1", "H")] * 3 + [_p("B", "f2", "L")] * 3
    result = class_fid_count_cv(problems)
    assert "B" in result, f"Class 'B' must be present; got {list(result)}"
    assert abs(result["B"]) < 1e-9, f"Uniform [3,3] -> cv=0.0; got {result['B']}"


def test_single_fid_zero_cv() -> None:
    """Single fid per class -> CV=0.0 (only one value, std=0)."""
    problems = [_p("C", "f3", "H")] * 7
    result = class_fid_count_cv(problems)
    assert "C" in result, f"Class 'C' must be present; got {list(result)}"
    assert abs(result["C"]) < 1e-9, f"Single-fid -> cv=0.0; got {result['C']}"


def test_empty_returns_empty_dict() -> None:
    """Empty -> {}."""
    assert class_fid_count_cv([]) == {}


def test_three_fid_cv() -> None:
    """Three fids: f1=3, f2=2, f3=1 -> mean=2, std=sqrt(2/3), cv=sqrt(2/3)/2."""
    problems = [_p("D", "f4", "H")] * 3 + [_p("D", "f5", "M")] * 2 + [_p("D", "f6", "L")]
    result = class_fid_count_cv(problems)
    expected = math.sqrt(2.0 / 3.0) / 2.0
    assert abs(result["D"] - expected) < 1e-9, (
        f"counts=[3,2,1], cv=sqrt(2/3)/2={expected:.6f}; got {result['D']}"
    )
