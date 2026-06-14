"""Item 200: problems_above_threshold() — class-count gate filter (2026-06-08).

``problems_above_threshold(problems: list[Problem], thresholds: dict[str, int])``
→ ``list[Problem]``:
Returns findings whose ``problem_class`` is monitored in *thresholds* AND
whose class count exceeds the configured limit.  Unmonitored classes
(absent from *thresholds*) are always excluded.  Empty *thresholds* →
``[]``.  Pure; no I/O.

Functional counterpart to :func:`assert_class_counts_under` — instead of
raising, it returns the offending findings::

    high_priority = problems_above_threshold(
        findings, {"complexity_outlier": 2}
    )

Discriminating tests -- each kills a plausible wrong implementation:

  1. PRIMARY DISC.: class count exceeding threshold -> that class's findings
     in result.
     Kills a no-op impl that returns all findings unconditionally.
  2. Class under threshold -> excluded from result.
     Kills an impl that returns all monitored-class findings regardless of count.
  3. Unmonitored class -> excluded even if its count is high.
     Kills an impl that returns all classes with count >= 1.
  4. Empty thresholds -> [] (not all findings).
     Kills an impl that treats empty thresholds as "no filter".
  5. Insertion order of returned findings preserved.
     Kills an impl that sorts the result.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import (
    Problem,
    problems_above_threshold,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _p(cls: str, idx: int = 0) -> Problem:
    return Problem(problem_class=cls, finding_id=f"{cls}:{idx}")


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_class_exceeding_threshold_in_result() -> None:
    """Class whose count exceeds threshold -> that class's findings returned.

    PRIMARY DISCRIMINATOR: kills a no-op impl that returns all findings
    unchanged regardless of whether any class exceeds its threshold.
    """
    problems = [
        _p("complexity_outlier", 0),
        _p("nesting_outlier"),
        _p("complexity_outlier", 1),
        _p("complexity_outlier", 2),
    ]  # complexity_outlier: 3 > threshold of 2
    thresholds = {"complexity_outlier": 2, "nesting_outlier": 5}

    result = problems_above_threshold(problems, thresholds)

    classes = {p.problem_class for p in result}
    assert "complexity_outlier" in classes, (
        "complexity_outlier (count=3 > limit=2) must be in result; got " + repr(classes)
    )
    assert "nesting_outlier" not in classes, (
        "nesting_outlier (count=1, limit=5) must NOT be in result"
    )


def test_class_under_threshold_excluded() -> None:
    """Class with count at or below threshold -> excluded from result.

    Kills an impl that returns all monitored-class findings regardless
    of whether the count actually exceeds the limit.
    """
    problems = [_p("complexity_outlier", 0), _p("complexity_outlier", 1)]
    thresholds = {"complexity_outlier": 2}  # count=2 is NOT > 2

    result = problems_above_threshold(problems, thresholds)

    assert result == [], "Count=2 does not exceed limit=2; result must be []; got " + repr(result)


def test_unmonitored_class_always_excluded() -> None:
    """Class absent from thresholds -> excluded even with high count.

    Kills an impl that returns all classes with count >= 1, ignoring
    which classes are actually monitored.
    """
    problems = [_p("complexity_outlier", i) for i in range(10)]
    thresholds = {"nesting_outlier": 1}  # complexity_outlier is unmonitored

    result = problems_above_threshold(problems, thresholds)

    assert result == [], "Unmonitored class must be excluded regardless of count; got " + repr(
        result
    )


def test_empty_thresholds_returns_empty() -> None:
    """Empty thresholds -> [] (no findings returned).

    Kills an impl that treats empty thresholds as 'no filter' and returns
    all findings.
    """
    problems = [_p("complexity_outlier"), _p("nesting_outlier")]

    result = problems_above_threshold(problems, {})

    assert result == [], "Empty thresholds must return []; got " + repr(result)


def test_insertion_order_preserved() -> None:
    """Returned findings are in original insertion order.

    Kills an impl that sorts the result or returns findings in a different
    order than they appeared in the input list.
    """
    p0 = _p("complexity_outlier", 2)
    p1 = _p("complexity_outlier", 0)
    p2 = _p("complexity_outlier", 1)
    problems = [p0, p1, p2]
    thresholds = {"complexity_outlier": 2}  # count=3 > limit=2

    result = problems_above_threshold(problems, thresholds)

    fids = [p.finding_id for p in result]
    assert fids == [
        "complexity_outlier:2",
        "complexity_outlier:0",
        "complexity_outlier:1",
    ], "Insertion order must be preserved; got " + repr(fids)
