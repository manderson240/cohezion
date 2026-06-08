"""Item 465: dominant_severity_for_class() -- modal severity within a class (2026-06-08).

``dominant_severity_for_class(problems, problem_class) -> str | None``:
Returns the severity with the highest count among problems of the given class.
Tie-break: alphabetically first.  None when class absent or empty.

Discriminating tests -- each kills a plausible wrong implementation:

  1. PRIMARY DISC.: returns modal severity STR, not count, not bool.
     ClassA has HIGH×3, LOW×1 -> dominant='HIGH' (str).
     most_common_severity ignores class filter -- kills impl reusing it.
     Kills impl returning severity_rank (int) or has_problems_for_severity (bool).
  2. Tie-break: alphabetically first severity when counts are equal.
     ClassB has HIGH×1, LOW×1 -> dominant='HIGH' (alphabetically < 'LOW').
     Kills impl returning last-seen or random winner.
  3. Absent class -> None (not raise, not '').
     Kills impl without absence guard.
  4. Empty input -> None (not raise).
     Kills impl with unguarded access.
  5. Class filter is respected (other classes' severities don't affect result).
     ClassA: HIGH×1; ClassB: LOW×5 -> dominant_for_class(ClassA) = 'HIGH', not 'LOW'.
     Kills impl that ignores the class filter.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import (
    Problem,
    dominant_severity_for_class,
)


def _p(cls: str, fid: str, sev: str) -> Problem:
    return Problem(problem_class=cls, finding_id=fid, severity=sev)


def test_returns_modal_severity_string() -> None:
    """PRIMARY DISC.: returns modal severity str, not count or bool.

    ClassA: HIGH×3, LOW×1.  Dominant = 'HIGH' (str, the most common).
    most_common_severity across ALL classes would also be HIGH, but
    dominant_severity_for_class is class-filtered.
    Kills impl returning count (3) or True.
    """
    problems = [
        _p("ClassA", "f1", "HIGH"),
        _p("ClassA", "f2", "HIGH"),
        _p("ClassA", "f3", "HIGH"),
        _p("ClassA", "f4", "LOW"),
        _p("ClassB", "f5", "LOW"),
        _p("ClassB", "f6", "LOW"),
    ]
    result = dominant_severity_for_class(problems, "ClassA")
    assert isinstance(result, str), "Must return str; got " + repr(type(result))
    assert result == "HIGH", "ClassA dominant='HIGH'; got " + repr(result)


def test_tie_break_alphabetical() -> None:
    """Equal counts: tie-break is alphabetically first severity."""
    problems = [
        _p("C", "f1", "HIGH"),
        _p("C", "f2", "LOW"),
    ]
    # HIGH=1, LOW=1 tie -> alphabetically 'HIGH' < 'LOW'
    result = dominant_severity_for_class(problems, "C")
    assert result == "HIGH", "Tie -> alphabetically first 'HIGH'; got " + repr(result)


def test_absent_class_returns_none() -> None:
    """Absent class -> None (not raise)."""
    problems = [_p("ClassA", "f1", "HIGH")]
    result = dominant_severity_for_class(problems, "NONEXISTENT")
    assert result is None, "Absent class -> None; got " + repr(result)


def test_empty_input_returns_none() -> None:
    """Empty input -> None (not raise)."""
    result = dominant_severity_for_class([], "ClassA")
    assert result is None, "Empty -> None; got " + repr(result)


def test_class_filter_respected() -> None:
    """Only problems of the given class contribute to the dominant severity.

    ClassA: HIGH×1.  ClassB: LOW×5.
    dominant_for_class(ClassA) = 'HIGH' (not 'LOW' which dominates globally).
    Kills impl that ignores the class filter.
    """
    problems = [
        _p("ClassA", "f1", "HIGH"),
        _p("ClassB", "f2", "LOW"),
        _p("ClassB", "f3", "LOW"),
        _p("ClassB", "f4", "LOW"),
        _p("ClassB", "f5", "LOW"),
        _p("ClassB", "f6", "LOW"),
    ]
    result = dominant_severity_for_class(problems, "ClassA")
    assert result == "HIGH", "ClassA-only dominant='HIGH'; got " + repr(result)
