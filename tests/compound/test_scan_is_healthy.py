"""Item 226: scan_is_healthy() — single boolean health gate (2026-06-08).

``scan_is_healthy(problems: list[Problem], thresholds: dict[str, int]) -> bool``
Returns ``True`` when ``violation_summary(problems, thresholds) == 0``, i.e.
no monitored class exceeds its threshold.  Empty *thresholds* -> ``True``
(nothing to violate).  Pure; no I/O.

Enables a single-line CI gate::

    assert scan_is_healthy(findings, limits), "Health gate failed"

Discriminating tests -- each kills a plausible wrong implementation:

  1. PRIMARY DISC.: returns False when any class exceeds threshold.
     Kills an impl that always returns True.
  2. Returns True when all classes are within threshold.
     Kills an impl that returns False on any findings.
  3. Empty thresholds -> True.
     Kills an impl that raises or returns False on empty thresholds.
  4. Return type is bool, not int.
     Kills an impl that returns violations_count (0/1) instead of True/False.
  5. At-threshold is healthy (not a violation).
     Kills an impl that treats at-threshold as unhealthy.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import (
    Problem,
    scan_is_healthy,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _p(cls: str, idx: int = 0) -> Problem:
    return Problem(problem_class=cls, finding_id=f"{cls}:{idx}")


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_returns_false_when_class_exceeds_threshold() -> None:
    """Returns False when any monitored class exceeds its threshold.

    PRIMARY DISCRIMINATOR: kills an impl that always returns True.
    alpha: 5 findings > threshold=2 -> unhealthy.
    """
    problems = [_p("alpha", i) for i in range(5)]
    thresholds = {"alpha": 2}

    result = scan_is_healthy(problems, thresholds)

    assert result is False, "Violated threshold must return False; got " + repr(result)


def test_returns_true_when_all_within_threshold() -> None:
    """Returns True when all monitored classes are within their thresholds.

    Kills an impl that returns False on any findings.
    """
    problems = [_p("alpha", i) for i in range(2)] + [_p("beta")]
    thresholds = {"alpha": 5, "beta": 3}

    result = scan_is_healthy(problems, thresholds)

    assert result is True, "All within threshold must return True; got " + repr(result)


def test_empty_thresholds_returns_true() -> None:
    """Empty thresholds -> True (no rules = no violations).

    Kills an impl that raises or returns False on empty thresholds.
    """
    problems = [_p("alpha"), _p("beta")]
    result = scan_is_healthy(problems, {})
    assert result is True, "Empty thresholds must return True; got " + repr(result)


def test_return_type_is_bool_not_int() -> None:
    """Return value is bool, not int (0/1).

    Kills an impl that returns violation_summary(...) == 0 without bool cast.
    Actually violation_summary == 0 IS a bool via ==, but test: isinstance(result, bool).
    """
    problems = [_p("alpha", i) for i in range(3)]
    thresholds = {"alpha": 5}

    result = scan_is_healthy(problems, thresholds)

    assert isinstance(result, bool), "Return type must be bool; got " + repr(type(result))
    assert result is True


def test_at_threshold_is_healthy() -> None:
    """At-threshold (count == threshold) is healthy -- not a violation.

    Kills an impl that treats at-threshold as unhealthy (using >= instead of >).
    """
    problems = [_p("alpha", i) for i in range(3)]
    thresholds = {"alpha": 3}  # count == threshold -> healthy

    result = scan_is_healthy(problems, thresholds)

    assert result is True, "At-threshold must be healthy (True); got " + repr(result)
