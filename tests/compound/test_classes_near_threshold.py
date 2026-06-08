"""Item 234: classes_near_threshold() — early-warning set with tolerance (2026-06-08).

``classes_near_threshold(problems, thresholds, tolerance=1) -> frozenset[str]``:
Returns monitored classes where ``0 <= threshold - count <= tolerance``,
i.e. within *tolerance* findings of their limit.  Includes at-threshold
classes (threshold - count = 0).  Excludes over-threshold and classes far
from their limit.  Empty *thresholds* → ``frozenset()``.  Pure; no I/O.

Special case: tolerance=0 is equivalent to classes_at_threshold (only classes
exactly at their threshold).

Discriminating tests -- each kills a plausible wrong implementation:

  1. PRIMARY DISC.: class within tolerance IS in result; class beyond tolerance
     is absent.  Kills impl returning ALL compliant classes.
  2. Over-threshold class absent.
     Kills impl that includes violating classes.
  3. tolerance=0 equivalent to classes_at_threshold (strict boundary).
     Kills impl using > instead of >= for the lower bound.
  4. Empty thresholds -> frozenset().
     Kills impl that raises or returns non-empty.
  5. Default tolerance=1 excludes classes far from threshold.
     Kills impl ignoring tolerance parameter.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import (
    Problem,
    classes_near_threshold,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _p(cls: str, idx: int = 0) -> Problem:
    return Problem(problem_class=cls, finding_id=f"{cls}:{idx}")


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_within_tolerance_present_beyond_tolerance_absent() -> None:
    """Class within tolerance IS in result; class too far from limit is absent.

    PRIMARY DISCRIMINATOR: kills an impl returning all compliant classes.
    alpha: count=4, threshold=5 -> headroom=1 = tolerance -> present.
    beta:  count=1, threshold=5 -> headroom=4 > tolerance=1 -> absent.
    """
    problems = [_p("alpha", i) for i in range(4)] + [_p("beta")]
    thresholds = {"alpha": 5, "beta": 5}

    result = classes_near_threshold(problems, thresholds, tolerance=1)

    assert "alpha" in result, "alpha (headroom=1 == tolerance=1) must be present; got " + repr(
        result
    )
    assert "beta" not in result, "beta (headroom=4 > tolerance=1) must be absent; got " + repr(
        result
    )


def test_over_threshold_class_absent() -> None:
    """Over-threshold class (headroom < 0) is absent.

    Kills an impl that includes violating classes.
    alpha: count=7, threshold=5 -> headroom=-2 -> over threshold -> absent.
    """
    problems = [_p("alpha", i) for i in range(7)]
    thresholds = {"alpha": 5}

    result = classes_near_threshold(problems, thresholds, tolerance=2)

    assert "alpha" not in result, (
        "alpha (count=7 > threshold=5) must be absent from near-threshold; got " + repr(result)
    )


def test_tolerance_zero_equivalent_to_at_threshold() -> None:
    """tolerance=0 returns only exactly-at-threshold classes.

    Kills an impl using > instead of >= for the lower bound (which would
    include no classes when tolerance=0).
    alpha: count=3 == threshold=3 -> headroom=0 = tolerance=0 -> present.
    beta:  count=2, threshold=3  -> headroom=1 > tolerance=0 -> absent.
    """
    problems = [_p("alpha", i) for i in range(3)] + [_p("beta", i) for i in range(2)]
    thresholds = {"alpha": 3, "beta": 3}

    result = classes_near_threshold(problems, thresholds, tolerance=0)

    assert "alpha" in result, "alpha at-threshold (headroom=0 == tolerance=0) must be present"
    assert "beta" not in result, "beta (headroom=1 > tolerance=0) must be absent"


def test_empty_thresholds_returns_empty_frozenset() -> None:
    """Empty thresholds -> frozenset().

    Kills an impl that raises or returns non-empty.
    """
    problems = [_p("alpha"), _p("beta")]
    result = classes_near_threshold(problems, {})
    assert result == frozenset(), "Empty thresholds must return frozenset(); got " + repr(result)


def test_default_tolerance_excludes_classes_far_from_threshold() -> None:
    """Default tolerance=1 only includes classes within 1 of their threshold.

    Kills an impl ignoring the tolerance parameter.
    alpha: headroom=0 (at threshold) -> present.
    beta:  headroom=1 (1 away) -> present.
    gamma: headroom=3 (3 away) -> absent.
    """
    problems = (
        [_p("alpha", i) for i in range(5)]
        + [_p("beta", i) for i in range(4)]
        + [_p("gamma", i) for i in range(2)]
    )
    thresholds = {"alpha": 5, "beta": 5, "gamma": 5}

    result = classes_near_threshold(problems, thresholds)  # default tolerance=1

    assert "alpha" in result, "alpha (headroom=0) must be present with default tolerance=1"
    assert "beta" in result, "beta (headroom=1) must be present with default tolerance=1"
    assert "gamma" not in result, "gamma (headroom=3) must be absent with default tolerance=1"
