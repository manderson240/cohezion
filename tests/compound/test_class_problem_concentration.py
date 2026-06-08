"""Item 621: class_global_density() -- globally-normalised problem density per class.

Renamed from 'class_problem_density' to avoid collision with item-580 which owns
that name for the local formula (problems / class_fids).

``class_global_density(problems) -> dict[str, float]``:
Returns {class: total_class_problems / (distinct_fids_in_class * total_distinct_fids)}.
Empty -> {}.  Pure; no I/O.

Discriminating tests:
  1. PRIMARY DISC.: denominator is class_fids * TOTAL_fids (not just class_fids).
     Class A: 3 problems, 2 class-fids; total 4 distinct fids.
     density = 3 / (2 * 4) = 0.375.
     Item-580 local density = 3 / 2 = 1.5 -- kills impl reusing local-density formula.
  2. Empty -> {}.
  3. Single-class, single-fid: 2 probs / (1 * 1) = 2.0.
  4. Multiple classes computed independently with shared total_fids.
     Class A: 4 probs, 2 fids, total 3 fids -> 4/(2*3)=0.667.
     Class B: 1 prob, 1 fid, total 3 fids -> 1/(1*3)=0.333.
  5. Kills impl ignoring total-fids: result < local-density when total_fids > 1.
"""

from __future__ import annotations

import math

from cohezion.compound.problem_discovery import (
    Problem,
    class_global_density,
)


def _p(cls: str, fid: str, sev: str) -> Problem:
    return Problem(problem_class=cls, finding_id=fid, severity=sev)


def test_global_normalisation_primary_discriminator() -> None:
    """PRIMARY DISC.: denominator uses class_fids * total_fids (not class_fids alone).

    Class A: 3 problems over fids {f1,f2}; total distinct fids = {f1,f2,f3,f4} = 4.
    density = 3 / (2 * 4) = 0.375.
    local density (item-580 formula) = 3 / 2 = 1.5 -- kills local-density impl.
    """
    problems = (
        [_p("A", "f1", "H")] * 2 + [_p("A", "f2", "H")] + [_p("B", "f3", "M"), _p("B", "f4", "L")]
    )
    result = class_global_density(problems)
    assert isinstance(result, dict), "Must return dict; got " + repr(type(result))
    assert "A" in result, f"Class 'A' missing; got {list(result)}"
    expected_a = 3.0 / (2 * 4)  # 0.375
    assert abs(result["A"] - expected_a) < 1e-9, (
        f"A: 3 probs, 2 class-fids, 4 total-fids -> 3/(2*4)=0.375; "
        f"got {result['A']} (1.5 = local density, wrong)"
    )


def test_empty_returns_empty_dict() -> None:
    """Empty -> {}."""
    assert class_global_density([]) == {}


def test_single_class_single_fid() -> None:
    """Single class, single fid: 2 problems / (1 class-fid * 1 total-fid) = 2.0."""
    problems = [_p("X", "f1", "H"), _p("X", "f1", "H")]
    result = class_global_density(problems)
    assert abs(result["X"] - 2.0) < 1e-9, f"2/(1*1)=2.0; got {result['X']}"


def test_multiple_classes_share_total_fids_denominator() -> None:
    """Multiple classes computed with shared total_fids denominator.

    fids across all: {f1, f2, f3} -> total_distinct_fids = 3.
    Class A: 4 problems, fids {f1, f2} -> 4/(2*3) = 2/3 ≈ 0.6667.
    Class B: 1 problem, fid {f3}      -> 1/(1*3) = 1/3 ≈ 0.3333.
    """
    problems = [_p("A", "f1", "H")] * 2 + [_p("A", "f2", "H")] * 2 + [_p("B", "f3", "L")]
    result = class_global_density(problems)
    assert abs(result["A"] - 4.0 / (2 * 3)) < 1e-9, f"A: 4/(2*3); got {result['A']}"
    assert abs(result["B"] - 1.0 / (1 * 3)) < 1e-9, f"B: 1/(1*3); got {result['B']}"


def test_density_less_than_local_when_multiple_total_fids() -> None:
    """Kills impl that ignores total-fids (off by a constant factor).

    When total_fids > 1, global density < local density (item-580 formula),
    because global density divides by an EXTRA factor of total_fids.
    """
    problems = [_p("A", "f1", "H")] * 3 + [_p("B", "f2", "L")]
    result = class_global_density(problems)
    # total_fids = 2, class A: 3 probs / (1 * 2) = 1.5
    expected_a = 3.0 / (1 * 2)  # 1.5
    assert abs(result["A"] - expected_a) < 1e-9, (
        f"A: 3/(1*2)=1.5; got {result['A']} (3.0=local density, missing global factor)"
    )
    local_only = 3.0 / 1  # 3.0
    assert result["A"] < local_only, "global density must be < local density when total_fids>1"
    assert not math.isnan(result["A"]) and not math.isinf(result["A"])
