"""Item 563: fid_problem_fractions() -- fraction of total problems per fid (2026-06-08).

``fid_problem_fractions(problems) -> dict[str, float]``:
Returns {fid: count/total_problems} for every fid.
FID-axis complement of class_problem_fractions.
Values sum to 1.0.  Empty -> {}.  Pure; no I/O.

Discriminating tests -- each kills a plausible wrong implementation:

  1. PRIMARY DISC.: returns FID fractions (not class fractions).
     1 class, 3 distinct fids: class_problem_fractions={"SameClass":1.0},
     fid_problem_fractions={"fid_a":0.333..., "fid_b":0.333..., "fid_c":0.333...}.
     Kills impl reusing class_problem_fractions.
  2. Returns FRACTION (not count).
     fid_a: 3 of 5 problems -> fraction=0.6, count=3.
     Kills impl reusing fid_problem_count.
  3. Values sum to 1.0 (normalized distribution).
     Kills impl normalizing by number of fids instead of total problems.
  4. Returns dict[str, float] (not float).
     Kills impl returning a single float.
  5. Empty -> {} (not raise).
     Kills impl without empty guard.
"""

from __future__ import annotations
import math

from cohezion.compound.problem_discovery import Problem, fid_problem_fractions


def _p(cls: str, fid: str) -> Problem:
    return Problem(problem_class=cls, finding_id=fid)


def test_returns_fid_axis_fractions_not_class_axis() -> None:
    """PRIMARY DISC.: keyed on FID axis (not class axis).

    1 class, 3 distinct fids each with 1 problem -> fractions = [1/3, 1/3, 1/3].
    class_problem_fractions would return {"SameClass": 1.0}.
    Kills impl reusing class_problem_fractions.
    """
    problems = [
        _p("SameClass", "fid_a"),
        _p("SameClass", "fid_b"),
        _p("SameClass", "fid_c"),
    ]
    result = fid_problem_fractions(problems)
    assert isinstance(result, dict), "Must return dict; got " + repr(type(result))
    assert set(result.keys()) == {"fid_a", "fid_b", "fid_c"}, (
        f"Expected keys {{fid_a,fid_b,fid_c}}; got {set(result.keys())} "
        f"(class_problem_fractions gives {{SameClass:1.0}} = wrong axis)"
    )
    for fid, frac in result.items():
        assert abs(frac - 1/3) < 1e-9, f"{fid} fraction=1/3; got {frac}"


def test_returns_fraction_not_count() -> None:
    """Returns FRACTION (float), not int count.

    fid_a: 3 of 5 total problems -> fraction=0.6, not count=3.
    Kills impl reusing fid_problem_count (returns int counts).
    """
    problems = [
        _p("A", "fid_a"),
        _p("B", "fid_a"),
        _p("C", "fid_a"),  # fid_a = 3 of 5
        _p("A", "fid_b"),
        _p("B", "fid_b"),  # fid_b = 2 of 5
    ]
    result = fid_problem_fractions(problems)
    assert abs(result["fid_a"] - 0.6) < 1e-9, (
        f"fid_a: 3/5=0.6; got {result['fid_a']} (3=count is wrong)"
    )
    assert abs(result["fid_b"] - 0.4) < 1e-9, (
        f"fid_b: 2/5=0.4; got {result['fid_b']}"
    )


def test_values_sum_to_one() -> None:
    """All fractions sum to 1.0 (normalized partition).

    Kills impl normalizing by number of fids (not total problems).
    """
    problems = [
        _p("A", "fid_x"),
        _p("B", "fid_x"),
        _p("C", "fid_y"),
        _p("D", "fid_y"),
        _p("E", "fid_z"),
    ]
    result = fid_problem_fractions(problems)
    total = sum(result.values())
    assert abs(total - 1.0) < 1e-9, (
        f"Fractions must sum to 1.0; got {total}"
    )


def test_returns_dict_not_float() -> None:
    """Returns dict[str, float] (not a single float scalar).

    Kills impl returning a single float like fid_problem_fraction(problems, fid).
    """
    problems = [_p("A", "f1"), _p("B", "f2"), _p("C", "f3")]
    result = fid_problem_fractions(problems)
    assert isinstance(result, dict), "Must return dict; got " + repr(type(result))
    assert len(result) == 3, f"3 distinct fids -> 3 keys; got {len(result)}"


def test_empty_returns_empty_dict() -> None:
    """Empty problems -> {} (not raise, not ZeroDivisionError)."""
    result = fid_problem_fractions([])
    assert result == {}, f"Empty -> {{}}; got {result}"
