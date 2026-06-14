"""Item 228: classes_at_threshold() — exactly-at-limit classes (2026-06-08).

``classes_at_threshold(problems: list[Problem], thresholds: dict[str, int])``
-> ``frozenset[str]``:
Returns a frozenset of monitored classes whose finding count equals the
threshold *exactly* (count == threshold, i.e. headroom = 0, not yet a
violation).  Classes strictly below or above are absent.
Empty *thresholds* -> ``frozenset()``.  Pure; no I/O.

Together with ``classes_within_budget`` (count < threshold) and
``threshold_violations``-derived over-threshold classes (count > threshold),
the three sets form a complete tripartite partition of all monitored classes:
  under  ∪  at  ∪  over  ==  frozenset(thresholds.keys())
  (pairwise disjoint)

Discriminating tests -- each kills a plausible wrong implementation:

  1. PRIMARY DISC.: class at exact threshold is in result; strictly-under is absent.
     Kills an impl that returns all compliant classes (i.e. delegates to
     classes_under_threshold, which includes both strictly-under and at-threshold).
  2. Strictly-under class absent.
     Kills an impl that uses <= instead of ==.
  3. Over-threshold class absent.
     Kills an impl that returns all monitored classes.
  4. Empty thresholds -> frozenset().
     Kills an impl that raises or returns a non-empty frozenset.
  5. Tripartite partition: classes_within_budget | classes_at_threshold |
     {over-threshold} == frozenset(thresholds.keys()), all three disjoint.
     Kills an impl that misclassifies boundary classes.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import (
    Problem,
    classes_at_threshold,
    classes_within_budget,
    threshold_violations,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _p(cls: str, idx: int = 0) -> Problem:
    return Problem(problem_class=cls, finding_id=f"{cls}:{idx}")


def _over(problems, thresholds):
    """Return frozenset of monitored classes strictly over threshold."""
    return frozenset(threshold_violations(problems, thresholds).keys())


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_at_threshold_present_strictly_under_absent() -> None:
    """Class at exact threshold is in result; strictly-under is absent.

    PRIMARY DISCRIMINATOR: kills an impl returning all compliant classes.
    alpha: count=3 == threshold=3 -> at-threshold -> present.
    beta:  count=1 <  threshold=3 -> strictly-under -> absent.
    """
    problems = [_p("alpha", i) for i in range(3)] + [_p("beta")]
    thresholds = {"alpha": 3, "beta": 3}

    result = classes_at_threshold(problems, thresholds)

    assert "alpha" in result, (
        "alpha (count=3 == threshold=3) must be in classes_at_threshold; got " + repr(result)
    )
    assert "beta" not in result, (
        "beta (count=1 < threshold=3) must be absent (strictly under); got " + repr(result)
    )


def test_strictly_under_class_absent() -> None:
    """Class with count < threshold is absent (headroom > 0, not at limit).

    Kills an impl using <= instead of ==.
    """
    problems = [_p("alpha", i) for i in range(2)]
    thresholds = {"alpha": 5}  # count=2 < threshold=5 -> NOT at-threshold

    result = classes_at_threshold(problems, thresholds)

    assert "alpha" not in result, (
        "alpha (count=2 < threshold=5) must be absent from classes_at_threshold; got "
        + repr(result)
    )


def test_over_threshold_class_absent() -> None:
    """Class exceeding threshold is absent (it is a violation, not at-threshold).

    Kills an impl returning all monitored classes.
    alpha: count=5 > threshold=3 -> over-threshold -> absent.
    """
    problems = [_p("alpha", i) for i in range(5)]
    thresholds = {"alpha": 3}

    result = classes_at_threshold(problems, thresholds)

    assert "alpha" not in result, (
        "alpha (count=5 > threshold=3) is a violation, must be absent; got " + repr(result)
    )


def test_empty_thresholds_returns_empty_frozenset() -> None:
    """Empty thresholds -> frozenset().

    Kills an impl that raises or returns a non-empty frozenset.
    """
    problems = [_p("alpha"), _p("beta")]
    result = classes_at_threshold(problems, {})
    assert result == frozenset(), "Empty thresholds must return frozenset(); got " + repr(result)


def test_tripartite_partition_invariant() -> None:
    """under | at | over == frozenset(thresholds.keys()), all three disjoint.

    Kills an impl that misclassifies boundary classes (e.g. puts at-threshold
    into both 'under' and 'at', or omits it from all three).
    alpha: count=1 < threshold=3 -> within_budget (under).
    beta:  count=3 == threshold=3 -> at_threshold (at).
    gamma: count=5 > threshold=3 -> threshold_violations (over).
    """
    problems = (
        [_p("alpha", i) for i in range(1)]
        + [_p("beta", i) for i in range(3)]
        + [_p("gamma", i) for i in range(5)]
    )
    thresholds = {"alpha": 3, "beta": 3, "gamma": 3}

    under = classes_within_budget(problems, thresholds)
    at = classes_at_threshold(problems, thresholds)
    over = _over(problems, thresholds)

    all_monitored = frozenset(thresholds.keys())
    assert under | at | over == all_monitored, (
        "Tripartite partition must cover all monitored classes; "
        + f"under={under} at={at} over={over} expected={all_monitored}"
    )
    assert under & at == frozenset(), f"under ∩ at must be empty; got {under & at}"
    assert under & over == frozenset(), f"under ∩ over must be empty; got {under & over}"
    assert at & over == frozenset(), f"at ∩ over must be empty; got {at & over}"
    # Verify membership
    assert "alpha" in under and "alpha" not in at and "alpha" not in over
    assert "beta" in at and "beta" not in under and "beta" not in over
    assert "gamma" in over and "gamma" not in under and "gamma" not in at
