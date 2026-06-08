"""Item 673: class_distinct_fid_count() -- count of unique finding_ids per class.

Returns {class: distinct_fid_count}.  int >= 1.  Empty -> {}.  Pure; no I/O.

Discriminating tests:
  1. PRIMARY DISC.: counts DISTINCT fids NOT total problems.
     class A: f1,f1,f1,f2 -> distinct_count=2 (total_problem_count=4 wrong).
  2. Single fid repeated many times -> distinct_count=1.
  3. Empty -> {}.
  4. Multiple classes counted independently.
  5. Return type is int.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import Problem, class_distinct_fid_count


def _p(cls: str, fid: str) -> Problem:
    return Problem(problem_class=cls, finding_id=fid, severity="HIGH")


def test_distinct_not_total_primary_discriminator() -> None:
    """PRIMARY DISC.: counts DISTINCT fids NOT total problems in class.

    class A: f1 appears 3 times, f2 appears once -> distinct_fid_count=2 (not 4).
    Kills total-problem-count impl (4 wrong).
    """
    problems = [_p("A", "f1")] * 3 + [_p("A", "f2")]
    result = class_distinct_fid_count(problems)
    assert isinstance(result, dict), "Must return dict"
    assert "A" in result, f"Class 'A' must be present; got {list(result)}"
    assert result["A"] == 2, f"f1×3 + f2×1 -> 2 distinct fids; got {result['A']} (total=4 wrong)"
    assert isinstance(result["A"], int), "Must be int"


def test_single_fid_repeated_is_one() -> None:
    """Single fid repeated many times -> distinct_count=1."""
    problems = [_p("X", "f99")] * 7
    result = class_distinct_fid_count(problems)
    assert result["X"] == 1, f"Same fid 7 times -> distinct=1; got {result.get('X')}"


def test_empty_returns_empty_dict() -> None:
    """Empty -> {}."""
    assert class_distinct_fid_count([]) == {}


def test_multiple_classes_independent_counts() -> None:
    """Different classes get independent distinct fid counts."""
    problems = [_p("A", "f1")] * 2 + [_p("A", "f2")] * 2 + [_p("A", "f3")] + [_p("B", "f1")] * 5
    result = class_distinct_fid_count(problems)
    assert result["A"] == 3, f"A has 3 distinct fids; got {result.get('A')}"
    assert result["B"] == 1, f"B has 1 distinct fid; got {result.get('B')}"


def test_return_type_is_int() -> None:
    """Distinct count must be int."""
    result = class_distinct_fid_count([_p("Z", "fx"), _p("Z", "fy")])
    assert isinstance(result["Z"], int), f"Must be int; got {type(result['Z'])}"
