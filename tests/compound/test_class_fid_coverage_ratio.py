"""Item 619: class_fid_coverage_ratio() -- fraction of total fids covered per class.

``class_fid_coverage_ratio(problems) -> dict[str, float]``:
Returns {class: distinct_fids_in_class / total_distinct_fids}.
Proportion of ALL distinct fids that appear in each class.
Range: (0.0, 1.0].  Floats.  Empty -> {}.  Pure; no I/O.

NOTE: renamed from item-619's `class_coverage_ratio` to avoid collision with
the existing `class_coverage_ratio` (item 419) which returns record fractions.

Discriminating tests:
  1. PRIMARY DISC.: ratio = class-fids / TOTAL-fids (not per-class fraction of records).
     4 total distinct fids; class A covers 2 of them -> result['A']==0.5.
     class_fid_distinct_count would return 2 (count not ratio).
     class_coverage_ratio (419) returns record fraction, not fid fraction.
  2. Single class covers all fids -> ratio=1.0.
     Kills impl capping at less than 1.
  3. Returns float (not int).
  4. Empty -> {}.
  5. Two classes with overlapping fids -- each gets ratio against global total.
     fid 'f1' in A and B; fid 'f2' in B only; total fids=2.
     A: 1/2=0.5; B: 2/2=1.0.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import Problem, class_fid_coverage_ratio


def _p(cls: str, fid: str) -> Problem:
    return Problem(problem_class=cls, finding_id=fid, severity="HIGH")


def test_ratio_of_class_fids_over_total_fids_primary_discriminator() -> None:
    """PRIMARY DISC.: ratio = class's distinct fids / ALL distinct fids.

    4 total distinct fids (f1,f2,f3,f4); class A covers f1,f2 -> ratio=0.5.
    class_fid_distinct_count would return 2 (count).
    class_coverage_ratio (item 419) returns record fraction, not fid coverage.
    Kills both wrong-formula impls.
    """
    problems = [
        _p("A", "f1"),
        _p("A", "f2"),
        _p("B", "f3"),
        _p("B", "f4"),
    ]
    result = class_fid_coverage_ratio(problems)
    assert isinstance(result, dict), "Must return dict; got " + repr(type(result))
    assert "A" in result, f"Class 'A' must be key; got {list(result)}"
    assert abs(result["A"] - 0.5) < 1e-9, (
        f"A covers 2 of 4 total fids -> ratio=0.5; got {result['A']} "
        f"(2=count wrong, \!=0.5 = wrong denominator)"
    )
    assert abs(result["B"] - 0.5) < 1e-9, (
        f"B covers 2 of 4 total fids -> ratio=0.5; got {result['B']}"
    )


def test_single_class_covers_all_fids_ratio_one() -> None:
    """Single class with all fids -> ratio=1.0.

    Kills impl capping ratio below 1.0.
    """
    problems = [_p("A", "f1"), _p("A", "f2"), _p("A", "f3")]
    result = class_fid_coverage_ratio(problems)
    assert abs(result["A"] - 1.0) < 1e-9, (
        f"A covers all 3 of 3 fids -> ratio=1.0; got {result['A']}"
    )


def test_returns_float_not_int() -> None:
    """Return type is float (not int).

    Kills impl returning int count.
    """
    problems = [_p("A", "f1"), _p("B", "f2")]
    result = class_fid_coverage_ratio(problems)
    assert isinstance(result["A"], float), "Value must be float; got " + type(result["A"]).__name__


def test_empty_returns_empty_dict() -> None:
    """Empty -> {}."""
    assert class_fid_coverage_ratio([]) == {}


def test_overlapping_fids_ratio_against_global_total() -> None:
    """Classes sharing fids: each ratio is against the global total fid count.

    fid 'f1' in A and B; fid 'f2' in B only. Total distinct fids=2.
    A: 1 fid out of 2 total -> 0.5.
    B: 2 fids out of 2 total -> 1.0.
    Kills impl computing each class independently.
    """
    problems = [_p("A", "f1"), _p("B", "f1"), _p("B", "f2")]
    result = class_fid_coverage_ratio(problems)
    assert abs(result["A"] - 0.5) < 1e-9, f"A covers 1/2 fids -> 0.5; got {result['A']}"
    assert abs(result["B"] - 1.0) < 1e-9, f"B covers 2/2 fids -> 1.0; got {result['B']}"
