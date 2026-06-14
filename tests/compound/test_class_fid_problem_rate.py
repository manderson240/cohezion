"""Item 670: class_fid_problem_rate() -- fraction of all problems each class x fid cell contributes.

Returns {class: {fid: fraction}} where fraction = cell_count / total_problems.
float in (0, 1].  Sparse (absent cells not included).  Empty -> {}.  Pure; no I/O.

Discriminating tests:
  1. PRIMARY DISC.: fraction uses TOTAL problems across ALL classes and fids.
     class A fid f1: 3 of 10 total -> rate=0.3 (NOT 3/6 class-total=0.5, NOT 3/5 fid-total=0.6).
     Kills class-normalized and fid-normalized impl.
  2. All rates sum to 1.0 (float precision).
  3. Empty -> {}.
  4. Single problem -> rate=1.0.
  5. Return type is float not int.
"""

from __future__ import annotations

import math

from cohezion.compound.problem_discovery import Problem, class_fid_problem_rate


def _p(cls: str, fid: str) -> Problem:
    return Problem(problem_class=cls, finding_id=fid, severity="HIGH")


def test_rate_uses_total_not_class_or_fid_total_primary_discriminator() -> None:
    """PRIMARY DISC.: rate = cell_count / TOTAL problems (not class total, not fid total).

    Setup: class A fid f1: 3 problems; class A fid f2: 3 problems; class B fid f1: 4 problems.
    Total = 10.
    rate(A,f1) = 3/10 = 0.3.
    class-normalized wrong: 3/6 = 0.5.
    fid-normalized wrong: 3/7 = 0.4286.
    """
    problems = [_p("A", "f1")] * 3 + [_p("A", "f2")] * 3 + [_p("B", "f1")] * 4
    result = class_fid_problem_rate(problems)
    assert "A" in result and "f1" in result["A"], "A/f1 must be present"
    assert abs(result["A"]["f1"] - 0.3) < 1e-9, (
        f"3 of 10 total -> rate=0.3; got {result['A']['f1']} "
        f"(class-total 3/6=0.5 wrong; fid-total 3/7≈0.4286 wrong)"
    )
    assert isinstance(result["A"]["f1"], float), "Must be float"


def test_all_rates_sum_to_one() -> None:
    """All cell rates must sum to 1.0 (float precision)."""
    problems = [_p("A", "f1")] * 2 + [_p("A", "f2")] * 3 + [_p("B", "f3")] * 5
    result = class_fid_problem_rate(problems)
    total = sum(v for inner in result.values() for v in inner.values())
    assert math.isclose(total, 1.0, rel_tol=1e-9), f"Rates must sum to 1.0; got {total}"


def test_empty_returns_empty_dict() -> None:
    """Empty -> {}."""
    assert class_fid_problem_rate([]) == {}


def test_single_problem_rate_is_one() -> None:
    """Single problem -> only cell has rate=1.0."""
    result = class_fid_problem_rate([_p("A", "f1")])
    assert result["A"]["f1"] == 1.0, f"1/1 total -> rate=1.0; got {result['A']['f1']}"


def test_return_type_is_float() -> None:
    """Cell values must be float, not int."""
    result = class_fid_problem_rate([_p("X", "f9")] * 5)
    assert isinstance(result["X"]["f9"], float), f"Must be float; got {type(result['X']['f9'])}"
