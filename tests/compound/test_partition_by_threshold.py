"""Item 219: partition_by_threshold() — over/under split (2026-06-08).

``partition_by_threshold(problems: list[Problem], thresholds: dict[str, int])``
-> ``tuple[frozenset[str], frozenset[str]]``:
Returns ``(over, under)`` where:
  - ``over``  = monitored classes strictly above their threshold
  - ``under`` = monitored classes at or below their threshold
Unmonitored classes are absent from both sets.
Empty *thresholds* -> ``(frozenset(), frozenset())``.  Pure; no I/O.

Invariant: ``over | under == frozenset(thresholds.keys())``
           ``over & under == frozenset()``  (disjoint partition)

Discriminating tests -- each kills a plausible wrong implementation:

  1. PRIMARY DISC.: over | under == frozenset(thresholds.keys()) AND
     over & under == frozenset() (perfect disjoint partition).
     Kills any impl where a class appears in both sets or in neither.
  2. over contains exactly the classes above threshold.
     Kills an impl that puts at-threshold classes in `over`.
  3. under contains exactly the classes at-or-below threshold.
     Kills an impl that omits classes with count=0.
  4. Unmonitored classes absent from both sets.
     Kills an impl that includes all classes with findings.
  5. Empty thresholds -> (frozenset(), frozenset()).
     Kills an impl that raises or returns None on empty thresholds.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import (
    Problem,
    partition_by_threshold,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _p(cls: str, idx: int = 0) -> Problem:
    return Problem(problem_class=cls, finding_id=f"{cls}:{idx}")


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_partition_is_complete_and_disjoint() -> None:
    """over | under == all monitored classes AND over & under == empty.

    PRIMARY DISCRIMINATOR: kills any impl where a class appears in both sets
    or is absent from both sets (i.e. not a true partition).
    """
    # alpha: 4 findings > threshold=2 -> over
    # beta:  2 findings == threshold=2 -> under (at-threshold is NOT a violation)
    # gamma: 0 findings < threshold=5 -> under
    problems = [_p("alpha", i) for i in range(4)] + [_p("beta", i) for i in range(2)]
    thresholds = {"alpha": 2, "beta": 2, "gamma": 5}

    over, under = partition_by_threshold(problems, thresholds)

    all_monitored = frozenset(thresholds.keys())
    assert over | under == all_monitored, (
        "over | under must equal all monitored classes; got over="
        + repr(over)
        + " under="
        + repr(under)
    )
    assert over & under == frozenset(), "over and under must be disjoint; intersection=" + repr(
        over & under
    )


def test_over_excludes_at_threshold_class() -> None:
    """Class at exactly the threshold count must be in under, not over.

    Kills an impl that uses >= instead of > for the over set.
    """
    problems = [_p("alpha", i) for i in range(3)]
    thresholds = {"alpha": 3}  # count == threshold -> under

    over, under = partition_by_threshold(problems, thresholds)

    assert "alpha" not in over, "at-threshold class must not be in over; got over=" + repr(over)
    assert "alpha" in under, "at-threshold class must be in under; got under=" + repr(under)


def test_under_includes_zero_count_monitored_class() -> None:
    """Monitored class with 0 findings must be in under.

    Kills an impl that omits classes absent from the problems list.
    """
    problems = [_p("alpha")]
    thresholds = {"alpha": 5, "beta": 1}  # beta: count=0 <= threshold=1 -> under

    _over, under = partition_by_threshold(problems, thresholds)

    assert "beta" in under, "zero-count monitored class must be in under; got under=" + repr(under)


def test_unmonitored_class_absent_from_both() -> None:
    """Class not in thresholds must not appear in either set.

    Kills an impl that includes all classes present in problems.
    """
    problems = [_p("nesting_outlier")]
    thresholds = {"complexity_outlier": 5}

    over, under = partition_by_threshold(problems, thresholds)

    assert "nesting_outlier" not in over, "unmonitored class must not be in over"
    assert "nesting_outlier" not in under, "unmonitored class must not be in under"


def test_empty_thresholds_returns_empty_pair() -> None:
    """Empty thresholds -> (frozenset(), frozenset()).

    Kills an impl that raises or returns None on empty thresholds.
    """
    problems = [_p("alpha"), _p("beta")]
    over, under = partition_by_threshold(problems, {})
    assert over == frozenset(), "Empty thresholds must return empty over; got " + repr(over)
    assert under == frozenset(), "Empty thresholds must return empty under; got " + repr(under)
