"""Item 472: class_fid_matrix() -- 2-D count matrix: class x finding_id (2026-06-08).

``class_fid_matrix(problems) -> dict[str, dict[str, int]]``:
Returns matrix[cls][fid] = count for each (class, fid) pair.
Sparse: missing pairs are absent, not zero-filled.  Empty -> {}.  Pure; no I/O.

Discriminating tests -- each kills a plausible wrong implementation:

  1. PRIMARY DISC.: outer key is problem_class, inner key is finding_id.
     ClassA+fid1=2, ClassA+fid2=1 -> matrix['ClassA']['fid1']=2, ['fid2']=1.
     Kills impl reusing class_severity_matrix (wrong inner key).
  2. Count > 1: multiple records with same (class, fid) pair accumulate.
     Kills impl that stores True or 1 instead of actual count.
  3. Empty input -> {}.
     Kills impl with unguarded access.
  4. Cross-class isolation: fid in two classes -> two separate inner dicts.
     Kills impl that merges fids across classes.
  5. Sparse representation: (ClassA, fid2) absent -> not in matrix['ClassA'].
     Kills impl that zero-fills all combinations.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import (
    Problem,
    class_fid_matrix,
)


def _p(cls: str, fid: str, sev: str) -> Problem:
    return Problem(problem_class=cls, finding_id=fid, severity=sev)


def test_outer_class_inner_fid_not_severity() -> None:
    """PRIMARY DISC.: outer key = problem_class, inner key = finding_id.

    ClassA: fid1x2, fid2x1.  ClassB: fid1x1.
    Correct: matrix['ClassA']['fid1']=2, matrix['ClassA']['fid2']=1.
    Kills impl reusing class_severity_matrix (wrong inner dimension).
    """
    problems = [
        _p("ClassA", "fid1", "HIGH"),
        _p("ClassA", "fid1", "LOW"),
        _p("ClassA", "fid2", "HIGH"),
        _p("ClassB", "fid1", "MED"),
    ]
    result = class_fid_matrix(problems)
    assert isinstance(result, dict), "Must return dict; got " + repr(type(result))
    assert result["ClassA"]["fid1"] == 2, "ClassA/fid1=2; got " + repr(result)
    assert result["ClassA"]["fid2"] == 1, "ClassA/fid2=1; got " + repr(result)
    assert result["ClassB"]["fid1"] == 1, "ClassB/fid1=1; got " + repr(result)


def test_count_accumulates_for_duplicates() -> None:
    """Count > 1 when same (class, fid) pair appears multiple times."""
    problems = [_p("C", "f", "HIGH") for _ in range(5)]
    result = class_fid_matrix(problems)
    assert result["C"]["f"] == 5, "5 records for (C, f); got " + repr(result)


def test_empty_returns_empty_dict() -> None:
    """Empty input -> {} (not raise)."""
    result = class_fid_matrix([])
    assert result == {}, "Empty -> {}; got " + repr(result)


def test_cross_class_isolation() -> None:
    """Same fid in two classes -> two separate inner dict entries."""
    problems = [
        _p("ClassA", "shared_fid", "HIGH"),
        _p("ClassA", "shared_fid", "HIGH"),
        _p("ClassB", "shared_fid", "LOW"),
    ]
    result = class_fid_matrix(problems)
    assert result["ClassA"]["shared_fid"] == 2
    assert result["ClassB"]["shared_fid"] == 1


def test_sparse_missing_pair_absent() -> None:
    """Pairs with zero count are absent (sparse, not zero-filled)."""
    problems = [_p("ClassA", "fid1", "HIGH"), _p("ClassA", "fid2", "HIGH")]
    result = class_fid_matrix(problems)
    assert "ClassB" not in result, "ClassB absent from sparse matrix"
    assert "fid3" not in result.get("ClassA", {}), "fid3 not in ClassA"
