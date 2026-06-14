"""Item 227: classes_within_budget() — monitored classes with positive headroom (2026-06-08).

``classes_within_budget(problems: list[Problem], thresholds: dict[str, int])``
-> ``frozenset[str]``:
Returns a frozenset of monitored classes with COUNT STRICTLY BELOW threshold
(count < threshold, i.e. headroom > 0).  Classes AT threshold (headroom=0) are
NOT included — they have no budget left.  Empty *thresholds* -> ``frozenset()``.
Pure; no I/O.

Distinct from ``classes_under_threshold`` (which includes at-threshold classes):
- ``classes_under_threshold``:  count <= threshold (headroom >= 0)
- ``classes_within_budget``:    count <  threshold (headroom >  0)

Discriminating tests -- each kills a plausible wrong implementation:

  1. PRIMARY DISC.: class at-threshold (count == threshold) is ABSENT.
     Kills an impl that delegates to classes_under_threshold (includes at-threshold).
  2. Class strictly below threshold is present.
     Kills an impl that returns only violating classes.
  3. Unmonitored class is absent.
     Kills an impl that returns all classes with positive headroom.
  4. Empty thresholds -> frozenset().
     Kills an impl that returns frozenset(problems) or raises.
  5. Return type is frozenset[str].
     Kills an impl that returns a list or set.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import (
    Problem,
    classes_within_budget,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _p(cls: str, idx: int = 0) -> Problem:
    return Problem(problem_class=cls, finding_id=f"{cls}:{idx}")


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_at_threshold_class_absent() -> None:
    """At-threshold class (count == threshold) is absent from result.

    PRIMARY DISCRIMINATOR: kills an impl that includes at-threshold classes
    (the same behavior as classes_under_threshold).
    alpha: count=3 == threshold=3 -> headroom=0 -> absent.
    beta:  count=1 < threshold=3  -> headroom=2 -> present.
    """
    problems = [_p("alpha", i) for i in range(3)] + [_p("beta")]
    thresholds = {"alpha": 3, "beta": 3}

    result = classes_within_budget(problems, thresholds)

    assert "alpha" not in result, "at-threshold alpha must be absent (headroom=0); got " + repr(
        result
    )
    assert "beta" in result, "beta (count=1 < threshold=3) must be present; got " + repr(result)


def test_strictly_under_threshold_present() -> None:
    """Class with count < threshold is in result.

    Kills an impl that returns only classes at or above threshold.
    """
    problems = [_p("alpha", i) for i in range(2)]
    thresholds = {"alpha": 5}  # count=2 < threshold=5 -> headroom=3

    result = classes_within_budget(problems, thresholds)

    assert "alpha" in result, "alpha (count=2 < threshold=5) must be present; got " + repr(result)


def test_unmonitored_class_absent() -> None:
    """Class not in thresholds must be absent.

    Kills an impl that includes all classes that appear in problems.
    """
    problems = [_p("nesting_outlier")]
    thresholds = {"complexity_outlier": 5}

    result = classes_within_budget(problems, thresholds)

    assert "nesting_outlier" not in result, "unmonitored class must be absent; got " + repr(result)


def test_empty_thresholds_returns_empty_frozenset() -> None:
    """Empty thresholds -> frozenset().

    Kills an impl that raises or returns a non-empty frozenset.
    """
    problems = [_p("alpha"), _p("beta")]
    result = classes_within_budget(problems, {})
    assert result == frozenset(), "Empty thresholds must return frozenset(); got " + repr(result)


def test_return_type_is_frozenset() -> None:
    """Return value is frozenset[str], not list or mutable set.

    Kills an impl that returns list or set.
    """
    problems = [_p("alpha")]
    thresholds = {"alpha": 5}

    result = classes_within_budget(problems, thresholds)

    assert isinstance(result, frozenset), "Return type must be frozenset; got " + repr(type(result))
    assert "alpha" in result
