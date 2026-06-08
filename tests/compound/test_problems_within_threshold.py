"""Item 201: problems_within_threshold() — class-count keep filter (2026-06-08).

``problems_within_threshold(problems: list[Problem], thresholds: dict[str, int])``
→ ``list[Problem]``:
Returns findings whose ``problem_class`` is monitored in *thresholds* AND
whose class count does NOT exceed the configured limit.  Unmonitored
classes are excluded.  Empty *thresholds* → ``[]``.  Pure; no I/O.

Complement of :func:`problems_above_threshold` (which returns findings from
classes that EXCEED the limit — this returns findings from classes that
are AT OR BELOW the limit)::

    safe_classes = problems_within_threshold(
        findings, {"complexity_outlier": 5}
    )

Discriminating tests -- each kills a plausible wrong implementation:

  1. PRIMARY DISC.: class at/under threshold -> that class's findings returned.
     Kills an impl that returns only OVER-threshold findings (inversion of 200).
  2. Class over threshold -> excluded.
     Kills a no-op impl that returns all monitored-class findings.
  3. Unmonitored class -> excluded.
     Kills an impl that returns all classes with count <= threshold.
  4. Empty thresholds -> [].
     Kills an impl that treats empty thresholds as "keep all".
  5. Insertion order of kept findings preserved.
     Kills an impl that sorts the result.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import (
    Problem,
    problems_within_threshold,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _p(cls: str, idx: int = 0) -> Problem:
    return Problem(problem_class=cls, finding_id=f"{cls}:{idx}")


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_class_within_threshold_in_result() -> None:
    """Class whose count is at or below threshold -> its findings returned.

    PRIMARY DISCRIMINATOR: kills an impl that returns only OVER-threshold
    findings (i.e. behaves like problems_above_threshold instead of the
    complement).
    """
    problems = [
        _p("complexity_outlier", 0),
        _p("nesting_outlier"),
        _p("complexity_outlier", 1),
    ]  # complexity_outlier: 2 (at limit=2), nesting_outlier: 1 (under limit=3)
    thresholds = {"complexity_outlier": 2, "nesting_outlier": 3}

    result = problems_within_threshold(problems, thresholds)

    classes = {p.problem_class for p in result}
    assert "complexity_outlier" in classes, (
        "complexity_outlier (count=2, limit=2) must be in result; got " + repr(classes)
    )
    assert "nesting_outlier" in classes, (
        "nesting_outlier (count=1, limit=3) must be in result; got " + repr(classes)
    )


def test_class_over_threshold_excluded() -> None:
    """Class with count exceeding threshold -> excluded from result.

    Kills a no-op impl that returns all monitored-class findings regardless
    of whether the count exceeds the limit.
    """
    problems = [_p("complexity_outlier", i) for i in range(4)]
    thresholds = {"complexity_outlier": 2}  # count=4 exceeds limit=2

    result = problems_within_threshold(problems, thresholds)

    assert result == [], "Count=4 exceeds limit=2; result must be []; got " + repr(result)


def test_unmonitored_class_excluded() -> None:
    """Class absent from thresholds -> excluded even with low count.

    Kills an impl that returns all classes with count <= max_threshold.
    """
    problems = [_p("complexity_outlier")]  # count=1
    thresholds = {"nesting_outlier": 5}  # complexity_outlier is unmonitored

    result = problems_within_threshold(problems, thresholds)

    assert result == [], "Unmonitored class must be excluded; got " + repr(result)


def test_empty_thresholds_returns_empty() -> None:
    """Empty thresholds -> [] (not all findings).

    Kills an impl that treats empty thresholds as "no filter" and returns all.
    """
    problems = [_p("complexity_outlier"), _p("nesting_outlier")]

    result = problems_within_threshold(problems, {})

    assert result == [], "Empty thresholds must return []; got " + repr(result)


def test_insertion_order_preserved() -> None:
    """Returned findings appear in their original insertion order.

    Kills an impl that sorts the result.
    """
    p0 = _p("complexity_outlier", 2)
    p1 = _p("complexity_outlier", 0)
    p2 = _p("complexity_outlier", 1)
    problems = [p0, p1, p2]
    thresholds = {"complexity_outlier": 5}  # count=3 is within limit=5

    result = problems_within_threshold(problems, thresholds)

    fids = [p.finding_id for p in result]
    assert fids == [
        "complexity_outlier:2",
        "complexity_outlier:0",
        "complexity_outlier:1",
    ], "Insertion order must be preserved; got " + repr(fids)
