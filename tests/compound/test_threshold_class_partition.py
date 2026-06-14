"""Item 245: threshold_class_partition() — three-way class partition (2026-06-08).

``threshold_class_partition(problems: list[Problem], thresholds: dict[str, int])``
-> ``dict[str, frozenset[str]]``:
Returns ``{"within_budget": frozenset, "at_threshold": frozenset,
           "over_budget": frozenset}`` where:

* ``within_budget``  = monitored classes whose count < threshold
* ``at_threshold``   = monitored classes whose count == threshold
* ``over_budget``    = monitored classes whose count > threshold

The three sets are disjoint; their union equals the keyset of *thresholds*.
Unmonitored classes (not in *thresholds*) appear in none of the three sets.
Empty *thresholds* → all three sets empty.  Pure; no I/O.

NOTE: distinct from ``partition_problems_by_threshold`` (item 202) which
returns a 2-tuple of Problem lists.  This function operates on class names.

Discriminating tests — each kills a plausible wrong implementation:

  1. PRIMARY DISC.: the three frozensets are disjoint — no class appears in
     two sets.  Kills an impl using ≤/≥ boundaries that overlap at threshold.
  2. Union of three sets equals keyset of thresholds.
     Kills an impl that drops a class from the partition.
  3. Each class lands in the correct partition (within / at / over).
     Kills an impl that miscategorises boundary or over-budget cases.
  4. Unmonitored classes appear in none of the three sets.
     Kills an impl that puts unmonitored classes into within_budget.
  5. Return is a dict with exactly the three keys.
     Kills an impl returning a tuple or a dict with different keys.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import (
    Problem,
    threshold_class_partition,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _p(cls: str, idx: int = 0) -> Problem:
    return Problem(problem_class=cls, finding_id=f"{cls}:{idx}")


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_three_sets_are_disjoint() -> None:
    """No class appears in more than one of the three sets.

    PRIMARY DISCRIMINATOR: kills an impl using ≤/≥ boundaries so a class
    at the exact threshold appears in both within_budget and at_threshold.
    alpha: count=2, threshold=2 → at_threshold.  Must NOT be in within_budget.
    """
    problems = [_p("alpha", 0), _p("alpha", 1)]  # count=2
    thresholds = {"alpha": 2}
    result = threshold_class_partition(problems, thresholds)

    within = result["within_budget"]
    at = result["at_threshold"]
    over = result["over_budget"]

    assert len(within & at) == 0, "within_budget ∩ at_threshold must be empty; got overlap " + repr(
        within & at
    )
    assert len(within & over) == 0, "within_budget ∩ over_budget must be empty"
    assert len(at & over) == 0, "at_threshold ∩ over_budget must be empty"
    assert "alpha" in at, "alpha(count=2, threshold=2) must be in at_threshold; got " + repr(at)
    assert "alpha" not in within, "alpha must NOT be in within_budget"


def test_union_equals_threshold_keyset() -> None:
    """Union of the three sets equals the keyset of thresholds.

    Kills an impl that drops a class from the partition (e.g. a class whose
    count is exactly at threshold falls through).
    """
    problems = [
        _p("alpha", 0),
        _p("alpha", 1),
        _p("alpha", 2),  # count=3, threshold=2 → over
        _p("beta", 0),  # count=1, threshold=2 → within
        _p("gamma", 0),
        _p("gamma", 1),  # count=2, threshold=2 → at
    ]
    thresholds = {"alpha": 2, "beta": 2, "gamma": 2}
    result = threshold_class_partition(problems, thresholds)

    union = result["within_budget"] | result["at_threshold"] | result["over_budget"]
    assert union == frozenset(thresholds), (
        "Union of three sets must equal threshold keyset; got " + repr(union)
    )


def test_each_class_in_correct_partition() -> None:
    """alpha→within, beta→at, gamma→over land in the right slots.

    Kills an impl that miscategorises boundary or over-budget cases.
    """
    problems = [
        _p("alpha", 0),  # count=1, threshold=3 → within
        _p("beta", 0),
        _p("beta", 1),
        _p("beta", 2),  # count=3, threshold=3 → at
        _p("gamma", 0),
        _p("gamma", 1),
        _p("gamma", 2),
        _p("gamma", 3),  # count=4, threshold=3 → over
    ]
    thresholds = {"alpha": 3, "beta": 3, "gamma": 3}
    result = threshold_class_partition(problems, thresholds)

    assert "alpha" in result["within_budget"], "alpha(1<3) must be within_budget"
    assert "beta" in result["at_threshold"], "beta(3==3) must be at_threshold"
    assert "gamma" in result["over_budget"], "gamma(4>3) must be over_budget"


def test_unmonitored_classes_in_no_set() -> None:
    """Classes not in thresholds appear in none of the three sets.

    Kills an impl that puts unmonitored classes into within_budget.
    """
    problems = [_p("alpha"), _p("unmonitored")]
    thresholds = {"alpha": 5}
    result = threshold_class_partition(problems, thresholds)

    for key in ("within_budget", "at_threshold", "over_budget"):
        assert "unmonitored" not in result[key], (
            f"unmonitored class must not appear in {key}; got " + repr(result[key])
        )


def test_return_type_is_dict_with_three_keys() -> None:
    """Return is a dict with exactly keys within_budget, at_threshold, over_budget.

    Kills an impl returning a tuple or a dict with different keys.
    """
    result = threshold_class_partition([], {})
    assert isinstance(result, dict), "Must return a dict; got " + repr(type(result))
    assert set(result.keys()) == {"within_budget", "at_threshold", "over_budget"}, (
        "Must have exactly three keys; got " + repr(set(result.keys()))
    )
    for key, val in result.items():
        assert isinstance(val, frozenset), f"{key} must be frozenset; got " + repr(type(val))
