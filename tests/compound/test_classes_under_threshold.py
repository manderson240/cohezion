"""Item 206: classes_under_threshold() — classes still within budget (2026-06-08).

``classes_under_threshold(problems: list[Problem], thresholds: dict[str, int])``
-> ``frozenset[str]``:
Returns a frozenset of every monitored class whose count is AT OR BELOW the
configured threshold.  Unmonitored classes are absent.  Empty *thresholds*
-> ``frozenset()``.  Empty *problems* -> all monitored classes (count=0
satisfies any positive threshold).  Pure; no I/O.

Set complement of threshold_violations: while violations shows WHO is over
budget, classes_under_threshold shows WHO is still compliant::

    safe = classes_under_threshold(findings, limits)
    if "complexity_outlier" in safe:
        proceed()

Discriminating tests -- each kills a plausible wrong implementation:

  1. PRIMARY DISC.: monitored class at/under threshold -> in frozenset.
     Kills an impl that returns only classes WITH violations (the inverse).
  2. Monitored class over threshold -> absent.
     Kills an impl that includes all monitored classes regardless of count.
  3. Empty problems -> all monitored classes included (count=0 passes).
     Kills an impl that returns frozenset() when no findings exist.
  4. Unmonitored class -> absent.
     Kills an impl that returns all known classes with any remaining budget.
  5. Return type is frozenset[str].
     Kills an impl that returns a list or plain set.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import (
    Problem,
    classes_under_threshold,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _p(cls: str, idx: int = 0) -> Problem:
    return Problem(problem_class=cls, finding_id=f"{cls}:{idx}")


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_compliant_class_in_frozenset() -> None:
    """Monitored class at or below threshold -> in frozenset.

    PRIMARY DISCRIMINATOR: kills an impl that returns the violating classes
    (the inverse of this function -- threshold_violations as a set).
    alpha: count=2, threshold=3 -> compliant -> in result.
    """
    problems = [_p("alpha", i) for i in range(2)]
    thresholds = {"alpha": 3, "beta": 1}  # alpha: 2 <= 3 compliant; beta: 0 <= 1 compliant

    result = classes_under_threshold(problems, thresholds)

    assert "alpha" in result, "alpha (count=2 <= threshold=3) must be in result; got " + repr(
        result
    )
    assert "beta" in result, "beta (count=0 <= threshold=1) must be in result; got " + repr(result)


def test_over_threshold_class_absent() -> None:
    """Monitored class exceeding threshold -> absent from frozenset.

    Kills an impl that includes all monitored classes regardless of count.
    """
    problems = [_p("complexity_outlier", i) for i in range(5)]
    thresholds = {"complexity_outlier": 3}  # count=5 > limit=3 -> violation

    result = classes_under_threshold(problems, thresholds)

    assert "complexity_outlier" not in result, (
        f"complexity_outlier (count=5 > threshold=3) must be absent; got {result!r}"
    )
    assert result == frozenset()


def test_empty_problems_includes_all_monitored() -> None:
    """Empty problems list -> all monitored classes included (count=0 passes).

    Kills an impl that returns frozenset() when no findings exist because
    count=0 satisfies ANY positive threshold.
    """
    thresholds = {"alpha": 5, "beta": 1, "gamma": 10}

    result = classes_under_threshold([], thresholds)

    assert result == frozenset({"alpha", "beta", "gamma"}), (
        f"All monitored classes must be in result for empty problems; got {result!r}"
    )


def test_unmonitored_class_absent() -> None:
    """Class not in thresholds -> absent even with very low count.

    Kills an impl that returns all classes with count <= max_threshold.
    """
    problems = [_p("nesting_outlier")]  # count=1, but not monitored
    thresholds = {"complexity_outlier": 5}  # nesting_outlier not a key

    result = classes_under_threshold(problems, thresholds)

    assert "nesting_outlier" not in result, (
        f"nesting_outlier not in thresholds; must be absent; got {result!r}"
    )


def test_return_type_is_frozenset() -> None:
    """Return value is frozenset[str], not list or mutable set.

    Kills an impl that returns list(classes) or set(classes).
    """
    problems = [_p("alpha")]
    thresholds = {"alpha": 5}

    result = classes_under_threshold(problems, thresholds)

    assert isinstance(result, frozenset), f"Return type must be frozenset; got {type(result)!r}"
    assert "alpha" in result
