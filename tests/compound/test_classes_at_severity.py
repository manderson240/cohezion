"""Item 253: classes_at_severity() — class names with ≥1 problem at severity (2026-06-08).

``classes_at_severity(problems: list[Problem], severity: str) -> frozenset[str]``:
Returns the frozenset of class names that have at least one Problem whose
``problem.severity`` exactly equals *severity*.  Bridges the severity analytics
family with the class-level analytics family.

Passing ``severity=""`` returns classes that have unlabelled problems.
Empty input or no matching problems → ``frozenset()``.  Pure; no I/O.

Discriminating tests — each kills a plausible wrong implementation:

  1. PRIMARY DISC.: only classes that have at least one problem at *severity*
     are included — kills impl that returns all classes with any labelled problem.
  2. A class contributes at most once (it's a set).
     Kills impl returning a list with duplicates.
  3. Match is case-sensitive: "HIGH" ≠ "high".
     Kills impl that normalises severity before matching.
  4. Empty input → frozenset().
     Kills impl that raises on empty input.
  5. Return type is frozenset[str], not list or dict.
     Kills impl returning a sorted list or count dict.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import (
    Problem,
    classes_at_severity,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _ps(cls: str, idx: int, sev: str) -> Problem:
    return Problem(problem_class=cls, finding_id=f"{cls}:{idx}", severity=sev)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_only_classes_with_target_severity_returned() -> None:
    """Returns only classes with ≥1 problem at the target severity.

    PRIMARY DISCRIMINATOR: kills impl that returns all classes with any
    labelled problem (alpha has HIGH, beta has LOW — only alpha in result).
    """
    problems = [
        _ps("alpha", 0, "HIGH"),
        _ps("alpha", 1, "HIGH"),
        _ps("beta", 0, "LOW"),
    ]
    result = classes_at_severity(problems, "HIGH")
    assert result == frozenset({"alpha"}), (
        "Only alpha has HIGH; beta (LOW) must be excluded; got " + repr(result)
    )


def test_class_appears_once_even_with_multiple_problems() -> None:
    """A class with multiple HIGH problems appears only once in the frozenset.

    Kills impl returning a list with duplicates or counting occurrences.
    """
    problems = [_ps("alpha", i, "HIGH") for i in range(4)]
    result = classes_at_severity(problems, "HIGH")
    assert result == frozenset({"alpha"}), (
        "4 HIGH problems from alpha → alpha appears once; got " + repr(result)
    )


def test_match_is_case_sensitive() -> None:
    """'HIGH' and 'high' are distinct severity strings.

    Kills impl that normalises severity to lowercase before matching.
    """
    problems = [_ps("alpha", 0, "high")]
    result_upper = classes_at_severity(problems, "HIGH")
    result_lower = classes_at_severity(problems, "high")
    assert result_upper == frozenset(), "'HIGH' must not match 'high'; got " + repr(result_upper)
    assert result_lower == frozenset({"alpha"}), "'high' must match 'high'; got " + repr(
        result_lower
    )


def test_empty_input_returns_empty_frozenset() -> None:
    """Empty problems list → frozenset().

    Kills impl that raises on empty input.
    """
    result = classes_at_severity([], "HIGH")
    assert result == frozenset(), "Empty input → frozenset(); got " + repr(result)


def test_return_type_is_frozenset() -> None:
    """Return type is frozenset[str], not list or dict.

    Kills impl returning a sorted list or set instead of frozenset.
    """
    problems = [_ps("alpha", 0, "CRITICAL")]
    result = classes_at_severity(problems, "CRITICAL")
    assert isinstance(result, frozenset), "Must return frozenset; got " + repr(type(result))
    assert "alpha" in result
