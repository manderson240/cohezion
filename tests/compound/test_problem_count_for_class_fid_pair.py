"""Item 471: problem_count_for_class_fid_pair() -- class×fid intersection count (2026-06-08).

``problem_count_for_class_fid_pair(problems, problem_class, finding_id) -> int``:
Returns count of records matching BOTH problem_class AND finding_id.
0 for absent pair.  Pure; no I/O.

Discriminating tests -- each kills a plausible wrong implementation:

  1. PRIMARY DISC.: counts BOTH filters together (not class alone, not fid alone).
     ClassA+fid1=2, ClassA+fid2=3 -> (ClassA, fid1) = 2, not 5 (class total).
     Kills impl reusing class_histogram()[cls] which returns 5.
  2. Cross-class isolation: ClassA+fid1=2, ClassB+fid1=3 -> (ClassA, fid1) = 2.
     Kills impl reusing fid histogram which returns 5 (counts ClassB too).
  3. Absent class -> 0 (not raise).
  4. Absent fid -> 0 (not raise).
  5. Returns int not float.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import (
    Problem,
    problem_count_for_class_fid_pair,
)


def _p(cls: str, fid: str, sev: str) -> Problem:
    return Problem(problem_class=cls, finding_id=fid, severity=sev)


def test_counts_class_and_fid_together_not_class_alone() -> None:
    """PRIMARY DISC.: counts records matching BOTH class AND fid.

    ClassA: fid1×2, fid2×3 (total 5).  Query (ClassA, fid1) -> 2, not 5.
    Kills impl reusing class_histogram()[cls] = 5.
    """
    problems = [
        _p("ClassA", "fid1", "HIGH"),
        _p("ClassA", "fid1", "LOW"),
        _p("ClassA", "fid2", "HIGH"),
        _p("ClassA", "fid2", "HIGH"),
        _p("ClassA", "fid2", "HIGH"),
    ]
    result = problem_count_for_class_fid_pair(problems, "ClassA", "fid1")
    assert type(result) is int, "Must return int; got " + repr(type(result))
    assert result == 2, "(ClassA, fid1) = 2; got " + repr(result)


def test_cross_class_isolation() -> None:
    """Other classes with same fid do not contribute.

    ClassA+fid1=2, ClassB+fid1=3.  Query (ClassA, fid1) -> 2, not 5.
    Kills impl reusing fid histogram which ignores class.
    """
    problems = [
        _p("ClassA", "fid1", "HIGH"),
        _p("ClassA", "fid1", "HIGH"),
        _p("ClassB", "fid1", "HIGH"),
        _p("ClassB", "fid1", "HIGH"),
        _p("ClassB", "fid1", "LOW"),
    ]
    result = problem_count_for_class_fid_pair(problems, "ClassA", "fid1")
    assert result == 2, "(ClassA, fid1) = 2 not 5; got " + repr(result)


def test_absent_class_returns_zero() -> None:
    """Absent class -> 0 (not raise)."""
    problems = [_p("ClassA", "fid1", "HIGH")]
    result = problem_count_for_class_fid_pair(problems, "NONEXISTENT", "fid1")
    assert result == 0, "Absent class -> 0; got " + repr(result)


def test_absent_fid_returns_zero() -> None:
    """Absent fid -> 0 (not raise)."""
    problems = [_p("ClassA", "fid1", "HIGH")]
    result = problem_count_for_class_fid_pair(problems, "ClassA", "NONEXISTENT")
    assert result == 0, "Absent fid -> 0; got " + repr(result)


def test_returns_int_not_float() -> None:
    """Result is int, not float."""
    problems = [_p("ClassA", "fid1", "HIGH"), _p("ClassA", "fid1", "LOW")]
    result = problem_count_for_class_fid_pair(problems, "ClassA", "fid1")
    assert type(result) is int, "Must be int; got " + repr(type(result))
    assert result == 2
