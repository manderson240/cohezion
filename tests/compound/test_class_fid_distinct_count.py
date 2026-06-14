"""Item 617: class_fid_distinct_count() -- distinct finding_ids per class.

``class_fid_distinct_count(problems) -> dict[str, int]``:
Returns {class: distinct_fid_count} — cardinality of the fid set per class.
Counts how many unique finding_ids appear per class.
Empty -> {}.  Pure; no I/O.

Discriminating tests:
  1. PRIMARY DISC.: counts DISTINCT fids per class (not total problems).
     Class A with 3 problems across 2 fids -> result['A']==2 (not 3=total).
     Kills impl returning total problem count.
  2. Same fid repeated many times -> counts as 1.
     Class A with fid='f1' repeated 5 times -> distinct_fid_count=1.
     Kills impl counting fid occurrences instead of distinct fids.
  3. Returns int (not float).
     Kills impl returning float division.
  4. Empty -> {}.
     Kills impl without empty guard.
  5. Multiple classes are independent (each class has own distinct fid set).
     Class A shares fid 'f1' with class B -> each class still counts its own distinct fids.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import Problem, class_fid_distinct_count


def _p(cls: str, fid: str) -> Problem:
    return Problem(problem_class=cls, finding_id=fid, severity="HIGH")


def test_distinct_fids_not_total_count_primary_discriminator() -> None:
    """PRIMARY DISC.: counts DISTINCT fids, not total problems.

    Class A: 3 problems but only 2 distinct fids (f1, f2) -> result['A']==2.
    Kills impl returning 3 (total problem count).
    """
    problems = [_p("A", "f1"), _p("A", "f1"), _p("A", "f2")]
    result = class_fid_distinct_count(problems)
    assert isinstance(result, dict), "Must return dict; got " + repr(type(result))
    assert "A" in result, f"Class 'A' must be key; got {list(result)}"
    assert result["A"] == 2, (
        f"3 problems across 2 fids -> distinct_fid_count=2; got {result['A']} (3=total count wrong)"
    )


def test_repeated_fid_counts_once() -> None:
    """Same fid repeated 5 times counts as 1 distinct fid.

    Kills impl counting fid occurrences (would return 5).
    """
    problems = [_p("A", "f1")] * 5
    result = class_fid_distinct_count(problems)
    assert result["A"] == 1, f"f1 x5 -> distinct=1; got {result['A']}"


def test_returns_int_not_float() -> None:
    """Return type is int (not float).

    Kills impl returning float.
    """
    problems = [_p("A", "f1"), _p("A", "f2"), _p("A", "f3")]
    result = class_fid_distinct_count(problems)
    assert isinstance(result["A"], int), "Value must be int; got " + type(result["A"]).__name__
    assert result["A"] == 3, f"3 distinct fids -> 3; got {result['A']}"


def test_empty_returns_empty_dict() -> None:
    """Empty -> {}."""
    assert class_fid_distinct_count([]) == {}


def test_classes_have_independent_fid_sets() -> None:
    """Each class counts its own distinct fids independently.

    Class A and B both have fid 'f1' but their fid sets are independent.
    Class A: f1 only -> distinct=1.
    Class B: f1, f2 -> distinct=2.
    """
    problems = [_p("A", "f1"), _p("B", "f1"), _p("B", "f2")]
    result = class_fid_distinct_count(problems)
    assert result["A"] == 1, f"A has f1 only -> distinct=1; got {result['A']}"
    assert result["B"] == 2, f"B has f1,f2 -> distinct=2; got {result['B']}"
