"""Item 467: dominant_class_for_severity() -- class most associated with a severity (2026-06-08).

``dominant_class_for_severity(problems, severity) -> str | None``:
Returns the problem_class with the most records at the given severity.
Tie-break: alphabetically first.  None when severity absent.  Pure; no I/O.

Discriminating tests -- each kills a plausible wrong implementation:

  1. PRIMARY DISC.: returns single class STR (not list, not frozenset).
     Kills impl reusing classes_with_severity which returns a collection.
     HIGH appears in ClassA×3, ClassB×1 -> dominant='ClassA' (str).
  2. Tie-break alphabetical: equal per-class counts -> alphabetically first.
     Kills impl returning arbitrary first-seen winner.
  3. Absent severity -> None (not raise, not '').
     Kills impl without absence guard.
  4. Empty input -> None (not raise).
     Kills impl with unguarded access.
  5. Severity-filtered (other severities in the same class don't count).
     ClassA: HIGH×1, LOW×5.  ClassB: HIGH×3.
     dominant_class_for_severity(HIGH) -> 'ClassB' (3 > 1), not 'ClassA'.
     Kills impl counting ALL problems for a class, not just the severity ones.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import (
    Problem,
    dominant_class_for_severity,
)


def _p(cls: str, fid: str, sev: str) -> Problem:
    return Problem(problem_class=cls, finding_id=fid, severity=sev)


def test_returns_single_class_string_not_collection() -> None:
    """PRIMARY DISC.: returns class str, not list/frozenset of classes.

    HIGH: ClassA×3, ClassB×1.  Dominant = 'ClassA' (str, not ['ClassA','ClassB']).
    classes_with_severity would return a collection -- wrong here.
    Kills impl reusing classes_with_severity.
    """
    problems = [
        _p("ClassA", "f1", "HIGH"),
        _p("ClassA", "f2", "HIGH"),
        _p("ClassA", "f3", "HIGH"),
        _p("ClassB", "f4", "HIGH"),
    ]
    result = dominant_class_for_severity(problems, "HIGH")
    assert isinstance(result, str), "Must return str; got " + repr(type(result))
    assert result == "ClassA", "ClassA dominant for HIGH; got " + repr(result)


def test_tie_break_alphabetical() -> None:
    """Equal per-class HIGH counts: tie-break alphabetically first class."""
    problems = [
        _p("ClassZ", "f1", "HIGH"),
        _p("ClassA", "f2", "HIGH"),
    ]
    result = dominant_class_for_severity(problems, "HIGH")
    assert result == "ClassA", "Tie 'ClassA' < 'ClassZ'; got " + repr(result)


def test_absent_severity_returns_none() -> None:
    """Absent severity -> None (not raise)."""
    problems = [_p("ClassA", "f1", "HIGH")]
    result = dominant_class_for_severity(problems, "NONEXISTENT")
    assert result is None, "Absent severity -> None; got " + repr(result)


def test_empty_input_returns_none() -> None:
    """Empty input -> None (not raise)."""
    result = dominant_class_for_severity([], "HIGH")
    assert result is None, "Empty -> None; got " + repr(result)


def test_only_severity_filtered_counts() -> None:
    """Only problems matching the severity contribute to the count.

    ClassA: HIGH×1, LOW×5.  ClassB: HIGH×3.
    dominant_for_HIGH -> 'ClassB' (3 HIGH) not 'ClassA' (6 total).
    Kills impl counting all problems for a class, not just the target severity.
    """
    problems = [
        _p("ClassA", "f1", "HIGH"),
        _p("ClassA", "f2", "LOW"),
        _p("ClassA", "f3", "LOW"),
        _p("ClassA", "f4", "LOW"),
        _p("ClassA", "f5", "LOW"),
        _p("ClassA", "f6", "LOW"),
        _p("ClassB", "f7", "HIGH"),
        _p("ClassB", "f8", "HIGH"),
        _p("ClassB", "f9", "HIGH"),
    ]
    result = dominant_class_for_severity(problems, "HIGH")
    assert result == "ClassB", "ClassB has 3 HIGH vs ClassA 1 HIGH; got " + repr(result)
