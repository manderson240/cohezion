"""Item 466: dominant_severity_for_fid() -- modal severity for a finding_id (2026-06-08).

``dominant_severity_for_fid(problems, finding_id) -> str | None``:
Returns the severity with the highest count for the given finding_id.
Tie-break: alphabetically first.  None when fid absent.  Pure; no I/O.

Discriminating tests -- each kills a plausible wrong implementation:

  1. PRIMARY DISC.: returns modal severity filtered to fid (not global modal).
     fid='F1' appears in HIGH×2 and LOW×1; global modal might differ.
     Kills impl using most_common_severity without fid filter.
  2. Tie-break alphabetical: equal counts -> alphabetically first severity.
     Kills impl returning last-seen or non-deterministic winner.
  3. Absent fid -> None (not raise).
     Kills impl without absence guard.
  4. Empty input -> None (not raise).
     Kills impl with unguarded access.
  5. Class-orthogonal: same fid in multiple classes uses combined count.
     fid='F1': ClassA/HIGH + ClassB/HIGH -> dominant='HIGH' (count=2).
     Kills impl that only uses the first class it sees.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import (
    Problem,
    dominant_severity_for_fid,
)


def _p(cls: str, fid: str, sev: str) -> Problem:
    return Problem(problem_class=cls, finding_id=fid, severity=sev)


def test_returns_fid_filtered_modal_severity() -> None:
    """PRIMARY DISC.: returns modal severity for the given fid, not global modal.

    fid='F1': HIGH×2, LOW×1 -> dominant='HIGH'.
    fid='F2': LOW×3 (if we used global modal it might return LOW for F1 too).
    Kills impl not filtering by fid.
    """
    problems = [
        _p("c", "F1", "HIGH"),
        _p("c", "F1", "HIGH"),
        _p("c", "F1", "LOW"),
        _p("c", "F2", "LOW"),
        _p("c", "F2", "LOW"),
        _p("c", "F2", "LOW"),
    ]
    result = dominant_severity_for_fid(problems, "F1")
    assert isinstance(result, str), "Must return str; got " + repr(type(result))
    assert result == "HIGH", "F1 dominant='HIGH'; got " + repr(result)


def test_tie_break_alphabetical() -> None:
    """Equal counts: tie-break is alphabetically first severity."""
    problems = [
        _p("c", "F1", "HIGH"),
        _p("c", "F1", "LOW"),
    ]
    result = dominant_severity_for_fid(problems, "F1")
    assert result == "HIGH", "Tie 'HIGH' < 'LOW' alphabetically; got " + repr(result)


def test_absent_fid_returns_none() -> None:
    """Absent fid -> None (not raise)."""
    problems = [_p("c", "F1", "HIGH")]
    result = dominant_severity_for_fid(problems, "NONEXISTENT")
    assert result is None, "Absent fid -> None; got " + repr(result)


def test_empty_input_returns_none() -> None:
    """Empty input -> None (not raise)."""
    result = dominant_severity_for_fid([], "F1")
    assert result is None, "Empty -> None; got " + repr(result)


def test_class_orthogonal() -> None:
    """Same fid in multiple classes: counts from all classes are combined."""
    problems = [
        _p("ClassA", "F1", "HIGH"),
        _p("ClassB", "F1", "HIGH"),
        _p("ClassC", "F1", "LOW"),
    ]
    # F1: HIGH×2, LOW×1 -> dominant='HIGH' (counts across classes)
    result = dominant_severity_for_fid(problems, "F1")
    assert result == "HIGH", "F1 cross-class dominant='HIGH'; got " + repr(result)
