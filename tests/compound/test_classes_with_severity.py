"""Item 368: classes_with_severity() — class names that have ≥1 problem at a severity (2026-06-08).

``classes_with_severity(problems, severity) -> frozenset[str]``:
Returns the frozenset of problem_class strings where at least one Problem record
has the given severity.  Empty → frozenset().  Unknown severity → frozenset().
Pure; no I/O.

Discriminating tests — each kills a plausible wrong implementation:

  1. PRIMARY DISC.: returns class NAMES not Problem objects.
     Kills impl returning the Problem list.
  2. ONE matching record is enough to include the class (not ALL records must match).
     Kills impl requiring all records in a class to have that severity.
  3. Unknown severity returns frozenset() without raising.
     Kills impl crashing on unknown severity.
  4. Empty input returns frozenset().
     Kills impl raising on empty.
  5. Classes without any matching record are excluded.
     Kills impl returning all classes.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import (
    Problem,
    classes_with_severity,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _p(cls: str, fid: str, sev: str = "") -> Problem:
    return Problem(problem_class=cls, finding_id=fid, severity=sev)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_returns_class_names_not_problem_objects() -> None:
    """Returns frozenset of class name strings, not Problem objects.

    PRIMARY DISCRIMINATOR: kills impl returning list[Problem].
    """
    problems = [_p("alpha", "f:0", "HIGH"), _p("beta", "f:1", "LOW")]
    result = classes_with_severity(problems, "HIGH")
    assert isinstance(result, frozenset), "Must return frozenset"
    assert all(isinstance(v, str) for v in result), "Elements must be str"
    assert result == frozenset({"alpha"}), "Only alpha has HIGH; got " + repr(result)


def test_one_matching_record_qualifies_class() -> None:
    """A class qualifies if at least ONE record has the target severity.

    Kills impl requiring ALL records in a class to match.
    'alpha' has CRITICAL + LOW → qualifies for CRITICAL even though not all match.
    """
    problems = [
        _p("alpha", "f:0", "CRITICAL"),
        _p("alpha", "f:1", "LOW"),
        _p("beta", "f:2", "LOW"),
    ]
    result = classes_with_severity(problems, "CRITICAL")
    assert "alpha" in result, "alpha has one CRITICAL; got " + repr(result)
    assert "beta" not in result, "beta has no CRITICAL; got " + repr(result)


def test_unknown_severity_returns_empty() -> None:
    """Unknown severity returns frozenset() without raising.

    Kills impl crashing on unknown severity.
    """
    problems = [_p("alpha", "f:0", "HIGH")]
    result = classes_with_severity(problems, "NONEXISTENT_SEV")
    assert result == frozenset(), "Unknown severity → empty; got " + repr(result)


def test_empty_input_returns_empty() -> None:
    """Empty input returns frozenset() without raising."""
    assert classes_with_severity([], "HIGH") == frozenset()


def test_classes_without_match_excluded() -> None:
    """Classes with no records at target severity are excluded.

    Kills impl returning all classes regardless.
    """
    problems = [
        _p("has-it", "f:0", "MEDIUM"),
        _p("lacks-it", "f:1", "LOW"),
        _p("lacks-it", "f:2", "HIGH"),
    ]
    result = classes_with_severity(problems, "MEDIUM")
    assert result == frozenset({"has-it"}), "Only has-it has MEDIUM; got " + repr(result)
