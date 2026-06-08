"""Item 278: count_classes_with_severity() — number of distinct classes with a given severity (2026-06-08).

``count_classes_with_severity(problems: list[Problem], severity: str) -> int``:
Returns the number of distinct class names that have at least one problem at
*severity* (exact, case-sensitive).  0 when no class matches.  Pure; no I/O.

Discriminating tests — each kills a plausible wrong implementation:

  1. PRIMARY DISC.: counts distinct CLASSES, not total problems.
     A class with 3 HIGH problems counts as 1 (not 3).
     Kills impl returning total count of problems at that severity.
  2. Each class is counted at most once even with multiple matches.
     Kills impl that over-counts a class with multiple matching problems.
  3. Returns 0 when no problem has the given severity.
     Kills impl returning total class count regardless.
  4. Case-sensitive match: 'HIGH' and 'high' are distinct severities.
     Kills impl doing case-insensitive matching.
  5. Return type is int.
     Kills impl returning frozenset or list.
"""
from __future__ import annotations

from cohezion.compound.problem_discovery import (
    Problem,
    count_classes_with_severity,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _p(cls: str, idx: int, sev: str = "") -> Problem:
    return Problem(problem_class=cls, finding_id=f"{cls}:{idx}", severity=sev)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_counts_classes_not_problems() -> None:
    """Counts distinct classes, not total problems.

    PRIMARY DISCRIMINATOR: kills impl returning total problem count.
    alpha: 3 HIGH, beta: 1 HIGH. Classes with HIGH = 2, problems = 4.
    """
    problems = [
        _p("alpha", 0, "HIGH"), _p("alpha", 1, "HIGH"), _p("alpha", 2, "HIGH"),
        _p("beta", 0, "HIGH"),
    ]
    result = count_classes_with_severity(problems, "HIGH")
    assert result == 2, (
        "alpha and beta both have HIGH; expected 2 classes; got " + repr(result)
    )


def test_each_class_counted_once() -> None:
    """Each class is counted at most once even with multiple problems at severity.

    Kills impl incrementing a counter per matching problem.
    alpha has 5 HIGH problems but must count as 1.
    """
    problems = [_p("alpha", i, "HIGH") for i in range(5)]
    result = count_classes_with_severity(problems, "HIGH")
    assert result == 1, (
        "alpha has 5 HIGH but only 1 class; expected 1; got " + repr(result)
    )


def test_returns_zero_when_severity_absent() -> None:
    """Returns 0 when no problem has the given severity.

    Kills impl returning total class count regardless of severity.
    """
    problems = [_p("alpha", 0, "LOW"), _p("beta", 0, "MEDIUM")]
    result = count_classes_with_severity(problems, "HIGH")
    assert result == 0, "No HIGH problems → 0 classes; got " + repr(result)
    assert count_classes_with_severity([], "HIGH") == 0, "Empty → 0"


def test_case_sensitive_severity_match() -> None:
    """Match is case-sensitive: 'HIGH' and 'high' are distinct severities.

    Kills impl doing case-insensitive matching.
    """
    problems = [
        _p("alpha", 0, "HIGH"),
        _p("beta", 0, "high"),
    ]
    assert count_classes_with_severity(problems, "HIGH") == 1, (
        "Only alpha has 'HIGH' (uppercase); got " + repr(count_classes_with_severity(problems, "HIGH"))
    )
    assert count_classes_with_severity(problems, "high") == 1, (
        "Only beta has 'high' (lowercase); got " + repr(count_classes_with_severity(problems, "high"))
    )


def test_return_type_is_int() -> None:
    """Return type is int, not frozenset or list.

    Kills impl returning a collection.
    """
    problems = [_p("alpha", 0, "HIGH")]
    result = count_classes_with_severity(problems, "HIGH")
    assert isinstance(result, int), "Must return int; got " + repr(type(result))
