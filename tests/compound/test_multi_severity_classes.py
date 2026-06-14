"""Item 333: multi_severity_classes() — classes at 2+ distinct severity levels (2026-06-08).

``multi_severity_classes(problems) -> frozenset[str]``:
Returns frozenset of class names that have labelled problems at >=2 distinct severity values.
Unlabelled problems do not contribute to the severity count.
Classes with only one distinct severity (even many records) are excluded.
Empty input -> frozenset().  Pure; no I/O.

Discriminating tests — each kills a plausible wrong implementation:

  1. PRIMARY DISC.: class with 2 distinct severities IS in result.
     Kills impl returning all classes or empty.
  2. Class with problems at only ONE severity is NOT in result.
     Kills impl counting records instead of distinct severities.
  3. Unlabelled problems don't count toward severity variety.
     Kills impl treating unlabelled as an additional severity level.
  4. Empty input returns frozenset().
     Kills impl raising on empty.
  5. Class with 3+ distinct severities IS included.
     Kills impl requiring exactly 2 (not >= 2).
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import (
    Problem,
    multi_severity_classes,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _ps(cls: str, idx: int, sev: str) -> Problem:
    return Problem(problem_class=cls, finding_id=f"{cls}:{idx}", severity=sev)


def _p(cls: str, idx: int) -> Problem:
    return Problem(problem_class=cls, finding_id=f"{cls}:{idx}")


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_class_with_two_distinct_severities_is_included() -> None:
    """Class appearing at 2 distinct severities is in result.

    PRIMARY DISCRIMINATOR: kills impl returning all classes or empty.
    alpha: HIGH + LOW (2 severities) -> in result.
    beta: HIGH only -> not in result.
    """
    problems = [
        _ps("alpha", 0, "HIGH"),
        _ps("alpha", 1, "LOW"),
        _ps("beta", 0, "HIGH"),
        _ps("beta", 1, "HIGH"),
    ]
    result = multi_severity_classes(problems)
    assert "alpha" in result, "alpha has HIGH+LOW -> in multi_severity_classes"
    assert "beta" not in result, "beta has only HIGH -> NOT in result"


def test_class_with_single_severity_excluded() -> None:
    """Class with many records but only ONE severity is excluded.

    Kills impl counting records instead of distinct severity values.
    alpha: 5 HIGH records (all same severity) -> NOT in result.
    """
    problems = [_ps("alpha", i, "HIGH") for i in range(5)]
    result = multi_severity_classes(problems)
    assert "alpha" not in result, "5 HIGH records (1 severity) -> alpha NOT in result; got " + repr(
        result
    )


def test_unlabelled_do_not_count_as_severity() -> None:
    """Unlabelled problems do not contribute to severity variety.

    Kills impl treating '' as an additional severity level.
    alpha: 1 HIGH (labelled) + 2 unlabelled -> only 1 distinct severity -> not in result.
    """
    problems = [
        _ps("alpha", 0, "HIGH"),
        _p("alpha", 1),  # unlabelled
        _p("alpha", 2),  # unlabelled
    ]
    result = multi_severity_classes(problems)
    assert "alpha" not in result, (
        "alpha has 1 labelled severity (HIGH) + unlabelled -> not in result; got " + repr(result)
    )


def test_empty_input_returns_empty_frozenset() -> None:
    """Empty input returns frozenset() without raising.

    Kills impl raising on empty.
    """
    result = multi_severity_classes([])
    assert result == frozenset(), "empty -> frozenset(); got " + repr(result)


def test_class_with_three_distinct_severities_included() -> None:
    """Class with 3 distinct severities is included (>= 2, not exactly 2).

    Kills impl requiring exactly 2 severities.
    alpha: CRITICAL + HIGH + LOW (3 severities) -> in result.
    """
    problems = [
        _ps("alpha", 0, "CRITICAL"),
        _ps("alpha", 1, "HIGH"),
        _ps("alpha", 2, "LOW"),
    ]
    result = multi_severity_classes(problems)
    assert "alpha" in result, "alpha has 3 severities (>=2) -> in result; got " + repr(result)
