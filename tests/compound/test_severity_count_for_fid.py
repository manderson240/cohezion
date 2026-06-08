"""Item 470: severity_count_for_fid() -- fid×severity intersection count (2026-06-08).

``severity_count_for_fid(problems, finding_id, severity) -> int``:
Returns count of records matching BOTH finding_id AND severity.
0 for absent pair.  Pure; no I/O.

Discriminating tests -- each kills a plausible wrong implementation:

  1. PRIMARY DISC.: counts only records matching BOTH fid AND severity.
     fid_a: HIGH x3, LOW x2.  fid_b: HIGH x5.
     severity_count_for_fid(fid_a, HIGH) = 3 (not 5 for fid_b HIGH).
     Kills impl reusing fid histogram (ignores severity filter).
  2. Absent fid -> 0 (not raise).
     Kills impl without fid guard.
  3. Absent severity -> 0 (not raise).
     Kills impl without severity guard.
  4. Result <= fid total count (subset semantics).
     fid_a: HIGH x2, LOW x1 -> count(fid_a, HIGH)=2 <= fid_total(fid_a)=3.
  5. Returns int not float (discriminates from severity_labelling_ratio).
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import (
    Problem,
    severity_count_for_fid,
)


def _p(cls: str, fid: str, sev: str) -> Problem:
    return Problem(problem_class=cls, finding_id=fid, severity=sev)


def test_counts_both_fid_and_severity() -> None:
    """PRIMARY DISC.: counts records matching BOTH fid AND severity.

    fid_a: HIGH x3, LOW x2.  fid_b: HIGH x5.
    severity_count_for_fid(fid_a, HIGH) = 3 (not 5 from fid_b).
    """
    problems = [
        _p("c", "fid_a", "HIGH"),
        _p("c", "fid_a", "HIGH"),
        _p("c", "fid_a", "HIGH"),
        _p("c", "fid_a", "LOW"),
        _p("c", "fid_a", "LOW"),
        _p("c", "fid_b", "HIGH"),
        _p("c", "fid_b", "HIGH"),
        _p("c", "fid_b", "HIGH"),
        _p("c", "fid_b", "HIGH"),
        _p("c", "fid_b", "HIGH"),
    ]
    result = severity_count_for_fid(problems, "fid_a", "HIGH")
    assert type(result) is int, "Must return int; got " + repr(type(result))
    assert result == 3, "fid_a HIGH count=3; got " + repr(result)


def test_absent_fid_returns_zero() -> None:
    """Absent fid -> 0 (not raise)."""
    problems = [_p("c", "fid_a", "HIGH")]
    result = severity_count_for_fid(problems, "NONEXISTENT", "HIGH")
    assert result == 0, "Absent fid -> 0; got " + repr(result)


def test_absent_severity_returns_zero() -> None:
    """Absent severity -> 0 (not raise)."""
    problems = [_p("c", "fid_a", "HIGH")]
    result = severity_count_for_fid(problems, "fid_a", "NONEXISTENT")
    assert result == 0, "Absent severity -> 0; got " + repr(result)


def test_count_leq_fid_total() -> None:
    """Intersection count <= total fid count (subset semantics)."""
    problems = [
        _p("c", "fid_a", "HIGH"),
        _p("c", "fid_a", "HIGH"),
        _p("c", "fid_a", "LOW"),
    ]
    result = severity_count_for_fid(problems, "fid_a", "HIGH")
    assert result == 2, "fid_a HIGH=2; got " + repr(result)
    assert result <= 3, "must be <= fid total 3; got " + repr(result)


def test_returns_int_not_float() -> None:
    """Returns int, not float."""
    problems = [_p("c", "fid_a", "HIGH")]
    result = severity_count_for_fid(problems, "fid_a", "HIGH")
    assert type(result) is int, "Must be int; got " + repr(type(result))
    assert result == 1, "Single match -> 1; got " + repr(result)
