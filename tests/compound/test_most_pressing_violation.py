"""Item 230: most_pressing_violation() — the single most-over-threshold class (2026-06-08).

``most_pressing_violation(problems: list[Problem], thresholds: dict[str, int])``
-> ``str | None``:
Returns the name of the monitored class with the most-negative signed headroom
(``threshold - count``), i.e. the class furthest over its limit.  When no class
is violating (all signed headroom ≥ 0), returns ``None``.  Empty *thresholds*
→ ``None``.  Pure; no I/O.

Uses :func:`signed_headroom` internally; distinct from :func:`worst_violation`
(which returns a ``(class, excess)`` tuple and measures excess separately).

Discriminating tests — each kills a plausible wrong implementation:

  1. PRIMARY DISC.: returns the class with the deepest violation, NOT the
     class with the highest raw count.
     Kills an impl that sorts by count rather than by ``threshold - count``.
  2. Returns None when no violations exist.
     Kills an impl that always returns the class with the most problems.
  3. Multiple violations: returns the one with the most-negative headroom.
     Kills an impl that returns the first violating class in insertion order.
  4. Empty thresholds -> None.
     Kills an impl that raises or returns a default class name.
  5. Returns None when all classes are exactly at or under threshold.
     Kills an impl that returns at-threshold classes as pressing violations.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import (
    Problem,
    most_pressing_violation,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _p(cls: str, idx: int = 0) -> Problem:
    return Problem(problem_class=cls, finding_id=f"{cls}:{idx}")


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_returns_deepest_violation_not_highest_raw_count() -> None:
    """Returns the class deepest over its threshold, not the one with the most findings.

    PRIMARY DISCRIMINATOR: kills an impl that sorts by raw count.
    alpha: count=10, threshold=8  -> headroom=-2  (violation depth 2)
    beta:  count=4,  threshold=1  -> headroom=-3  (violation depth 3 — DEEPER)
    most_pressing_violation must return 'beta', not 'alpha' (alpha has more findings).
    """
    problems = [_p("alpha", i) for i in range(10)] + [_p("beta", i) for i in range(4)]
    thresholds = {"alpha": 8, "beta": 1}

    result = most_pressing_violation(problems, thresholds)

    assert result == "beta", (
        "beta (depth=3) is deeper than alpha (depth=2); expected 'beta', got " + repr(result)
    )


def test_returns_none_when_no_violations() -> None:
    """Returns None when all classes are within threshold.

    Kills an impl that always returns the most-common class.
    """
    problems = [_p("alpha", i) for i in range(2)] + [_p("beta")]
    thresholds = {"alpha": 5, "beta": 3}

    result = most_pressing_violation(problems, thresholds)

    assert result is None, "No violations -> must return None; got " + repr(result)


def test_multiple_violations_returns_deepest() -> None:
    """With multiple violating classes, returns the one with the most-negative headroom.

    Kills an impl that returns the first violating class in insertion order.
    alpha: 4 problems, threshold=3  -> depth=1
    beta:  7 problems, threshold=3  -> depth=4  (DEEPEST)
    gamma: 5 problems, threshold=3  -> depth=2
    """
    problems = (
        [_p("alpha", i) for i in range(4)]
        + [_p("beta", i) for i in range(7)]
        + [_p("gamma", i) for i in range(5)]
    )
    thresholds = {"alpha": 3, "beta": 3, "gamma": 3}

    result = most_pressing_violation(problems, thresholds)

    assert result == "beta", "beta has deepest violation (depth=4); expected 'beta', got " + repr(
        result
    )


def test_empty_thresholds_returns_none() -> None:
    """Empty thresholds -> None (no monitored classes, no violations possible).

    Kills an impl that raises or invents a class name.
    """
    problems = [_p("alpha"), _p("beta")]
    result = most_pressing_violation(problems, {})
    assert result is None, "Empty thresholds must return None; got " + repr(result)


def test_at_threshold_class_not_a_pressing_violation() -> None:
    """At-threshold class (signed_headroom=0) is not returned as a pressing violation.

    Kills an impl that treats 'headroom <= 0' as a violation rather than '< 0'.
    alpha: count=3 == threshold=3 -> headroom=0 -> compliant (at limit)
    """
    problems = [_p("alpha", i) for i in range(3)]
    thresholds = {"alpha": 3}

    result = most_pressing_violation(problems, thresholds)

    assert result is None, (
        "alpha at-threshold (headroom=0) must not be a pressing violation; got " + repr(result)
    )
