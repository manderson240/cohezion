"""Item 242: classes_with_max_severity() — classes containing a severity level (2026-06-08).

``classes_with_max_severity(problems: list[Problem], severity: str)``
-> ``frozenset[str]``:
Returns the frozenset of class names where at least one Problem has
``problem.severity == severity`` (exact, case-sensitive match).
Classes with no matching severity are excluded.
Empty input → frozenset().  Pure; no I/O.

Note: this function requires ``Problem`` to carry a ``severity`` field
(added as optional with default ``""`` — backward-compatible).

Discriminating tests — each kills a plausible wrong implementation:

  1. PRIMARY DISC.: only classes WITH a problem at the target severity are
     returned — not all non-empty classes.
     Kills an impl that returns ``classes_with_problems()`` or all classes.
  2. A class with a different severity is excluded.
     Kills an impl that ignores the severity argument.
  3. Severity match is case-sensitive: "HIGH" ≠ "high".
     Kills an impl that lowercases before comparing.
  4. Empty input → frozenset().
     Kills an impl that raises or returns None.
  5. Return type is frozenset, not list or dict.
     Kills an impl returning a list of Problem objects or a dict.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import (
    Problem,
    classes_with_max_severity,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _p(cls: str, severity: str = "", idx: int = 0) -> Problem:
    return Problem(problem_class=cls, finding_id=f"{cls}:{idx}", severity=severity)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_only_classes_with_target_severity_returned() -> None:
    """Only classes that have at least one problem at the target severity.

    PRIMARY DISCRIMINATOR: kills an impl that returns all non-empty classes.
    alpha has severity="HIGH"; beta has severity="LOW".
    classes_with_max_severity(..., "HIGH") must return only {"alpha"}.
    """
    problems = [_p("alpha", "HIGH"), _p("beta", "LOW")]

    result = classes_with_max_severity(problems, "HIGH")

    assert result == frozenset({"alpha"}), "Only alpha has HIGH; got " + repr(result)


def test_class_with_different_severity_excluded() -> None:
    """A class whose problem has a different severity is not returned.

    Kills an impl that ignores the severity argument.
    """
    problems = [_p("alpha", "LOW"), _p("alpha", "LOW", idx=1)]

    result = classes_with_max_severity(problems, "HIGH")

    assert result == frozenset(), "No HIGH problems → empty result; got " + repr(result)


def test_severity_match_is_case_sensitive() -> None:
    """Severity match is case-sensitive: 'HIGH' ≠ 'high'.

    Kills an impl that lowercases before comparing.
    """
    problems = [_p("alpha", "HIGH")]

    result_lower = classes_with_max_severity(problems, "high")

    assert "alpha" not in result_lower, "'high' (lowercase) must not match 'HIGH'; got " + repr(
        result_lower
    )


def test_empty_input_returns_empty_frozenset() -> None:
    """Empty problems → frozenset().

    Kills an impl that raises or returns None.
    """
    result = classes_with_max_severity([], "HIGH")
    assert result == frozenset(), "Empty input → frozenset(); got " + repr(result)


def test_return_type_is_frozenset() -> None:
    """Return type is frozenset, not list or dict.

    Kills an impl returning a list of Problem objects.
    """
    result = classes_with_max_severity([_p("alpha", "CRITICAL")], "CRITICAL")
    assert isinstance(result, frozenset), "Must return frozenset; got " + repr(type(result))
    assert "alpha" in result
