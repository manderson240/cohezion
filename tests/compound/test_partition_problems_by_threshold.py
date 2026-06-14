"""Item 202: partition_problems_by_threshold() — two-way threshold partition (2026-06-08).

``partition_problems_by_threshold(problems: list[Problem], thresholds: dict[str, int])``
→ ``tuple[list[Problem], list[Problem]]``:
Returns ``(above, within)`` in one pass:

* ``above``  — findings from monitored classes whose count EXCEEDS the limit.
* ``within`` — findings from monitored classes whose count is AT OR BELOW the limit.
* Unmonitored classes (absent from *thresholds*) appear in NEITHER partition.

Empty *thresholds* → ``([], [])``.  Pure; no I/O.

Avoids two separate calls to :func:`problems_above_threshold` and
:func:`problems_within_threshold` when both halves are needed::

    above, within = partition_problems_by_threshold(
        findings, {"complexity_outlier": 3}
    )

Discriminating tests -- each kills a plausible wrong implementation:

  1. PRIMARY DISC.: unmonitored classes absent from BOTH partitions.
     Kills an impl that puts unmonitored findings in one of the partitions.
  2. Count-exceeding class -> in above, not in within.
     Kills an impl that puts everything in within (like problems_within_threshold).
  3. Count-within class -> in within, not in above.
     Kills an impl that puts everything in above (like problems_above_threshold).
  4. Empty thresholds -> ([], []) as a tuple.
     Kills an impl that returns (all_findings, []) on empty thresholds.
  5. Return type is a tuple (not a list).
     Kills an impl that returns a list of two lists.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import (
    Problem,
    partition_problems_by_threshold,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _p(cls: str, idx: int = 0) -> Problem:
    return Problem(problem_class=cls, finding_id=f"{cls}:{idx}")


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_unmonitored_class_absent_from_both_partitions() -> None:
    """Unmonitored class absent from both above and within.

    PRIMARY DISCRIMINATOR: kills an impl that puts unmonitored findings
    into one of the partitions (e.g. always into within or always into above).
    """
    problems = [
        _p("complexity_outlier", 0),
        _p("unmonitored_class"),  # not in thresholds
        _p("nesting_outlier"),
    ]
    thresholds = {"complexity_outlier": 5, "nesting_outlier": 5}

    above, within = partition_problems_by_threshold(problems, thresholds)

    all_ids = {p.finding_id for p in above + within}
    assert "unmonitored_class:0" not in all_ids, (
        "Unmonitored class must not appear in either partition; "
        "above="
        + repr([p.finding_id for p in above])
        + " within="
        + repr([p.finding_id for p in within])
    )


def test_over_threshold_class_in_above_not_within() -> None:
    """Class with count exceeding limit -> findings in above, not in within.

    Kills an impl that puts all monitored findings in within regardless of count.
    """
    problems = [_p("complexity_outlier", i) for i in range(4)]
    thresholds = {"complexity_outlier": 2}  # count=4 > limit=2

    above, within = partition_problems_by_threshold(problems, thresholds)

    assert len(above) == 4, "All 4 complexity_outlier findings must be in above; got " + repr(
        len(above)
    )
    assert within == [], "Within must be empty for over-threshold class; got " + repr(within)


def test_within_threshold_class_in_within_not_above() -> None:
    """Class with count at or below limit -> findings in within, not in above.

    Kills an impl that puts all monitored findings in above regardless of count.
    """
    problems = [_p("nesting_outlier", i) for i in range(2)]
    thresholds = {"nesting_outlier": 5}  # count=2 <= limit=5

    above, within = partition_problems_by_threshold(problems, thresholds)

    assert above == [], "Above must be empty for within-threshold class; got " + repr(above)
    assert len(within) == 2, "Both nesting_outlier findings must be in within; got " + repr(
        len(within)
    )


def test_empty_thresholds_returns_empty_tuple() -> None:
    """Empty thresholds -> ([], []) as a two-element tuple.

    Kills an impl that returns (all_findings, []) when thresholds is empty.
    """
    problems = [_p("complexity_outlier"), _p("nesting_outlier")]

    result = partition_problems_by_threshold(problems, {})

    assert result == ([], []), "Empty thresholds must return ([], []); got " + repr(result)


def test_return_type_is_tuple() -> None:
    """Return value is a tuple, not a list of two lists.

    Kills an impl that returns list[list[Problem]] instead of a tuple.
    """
    result = partition_problems_by_threshold([_p("complexity_outlier")], {"complexity_outlier": 5})

    assert isinstance(result, tuple), "Return type must be tuple; got " + str(type(result))
    assert len(result) == 2
