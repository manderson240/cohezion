"""Item 207: budget_status() — per-class budget compliance summary (2026-06-08).

``budget_status(problems: list[Problem], thresholds: dict[str, int])``
-> ``dict[str, str]``:
Returns ``{problem_class: "ok"|"over"}`` for every monitored class.
``"ok"`` = count <= threshold; ``"over"`` = count > threshold.
Unmonitored classes absent.  Empty thresholds -> ``{}``.
Empty problems -> all monitored classes map to ``"ok"`` (count=0).
Pure; no I/O.

Composes items 203+206 into a single dashboard payload::

    status_by_class = budget_status(findings, limits)
    # {"complexity_outlier": "over", "nesting_outlier": "ok"}

Discriminating tests -- each kills a plausible wrong implementation:

  1. PRIMARY DISC.: compliant class -> "ok" (not absent, not "over").
     Kills an impl that returns only violating classes (omitting "ok" entries).
  2. Violating class -> "over" (not "ok", not absent).
     Kills an impl that returns "ok" for all classes regardless of count.
  3. Empty problems -> all monitored classes -> "ok".
     Kills an impl that short-circuits on empty problems.
  4. Unmonitored class absent from result.
     Kills an impl that includes all classes from problems.
  5. Values are ONLY "ok" or "over" (not int counts, not booleans).
     Kills an impl that returns violation counts as values.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import (
    Problem,
    budget_status,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _p(cls: str, idx: int = 0) -> Problem:
    return Problem(problem_class=cls, finding_id=f"{cls}:{idx}")


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_compliant_class_maps_to_ok() -> None:
    """Monitored class at/below threshold -> "ok" in result.

    PRIMARY DISCRIMINATOR: kills an impl that only returns violating classes
    (omitting the "ok" entries entirely from the result dict).
    """
    problems = [_p("complexity_outlier", i) for i in range(2)]
    thresholds = {"complexity_outlier": 5}  # count=2 <= threshold=5

    result = budget_status(problems, thresholds)

    assert "complexity_outlier" in result, "compliant class must appear in result; got " + repr(
        result
    )
    assert result["complexity_outlier"] == "ok", "at/below threshold must map to 'ok'; got " + repr(
        result["complexity_outlier"]
    )


def test_violating_class_maps_to_over() -> None:
    """Monitored class exceeding threshold -> "over" in result.

    Kills an impl that returns "ok" for all classes regardless of count.
    """
    problems = [_p("nesting_outlier", i) for i in range(4)]
    thresholds = {"nesting_outlier": 2}  # count=4 > threshold=2

    result = budget_status(problems, thresholds)

    assert result.get("nesting_outlier") == "over", (
        "exceeding threshold must map to 'over'; got " + repr(result.get("nesting_outlier"))
    )


def test_empty_problems_all_ok() -> None:
    """Empty problems -> all monitored classes map to "ok" (count=0 <= threshold).

    Kills an impl that short-circuits on empty problems and returns {}.
    """
    thresholds = {"alpha": 3, "beta": 1}

    result = budget_status([], thresholds)

    assert result == {"alpha": "ok", "beta": "ok"}, (
        "Empty problems: count=0 satisfies all thresholds; got " + repr(result)
    )


def test_unmonitored_class_absent() -> None:
    """Class not in thresholds -> absent from result.

    Kills an impl that includes every class from problems in the result.
    """
    problems = [_p("complexity_outlier"), _p("nesting_outlier")]
    thresholds = {"complexity_outlier": 5}  # nesting_outlier not monitored

    result = budget_status(problems, thresholds)

    assert "nesting_outlier" not in result, "unmonitored class must be absent; got " + repr(result)
    assert "complexity_outlier" in result


def test_values_are_strings_not_counts() -> None:
    """Values are "ok" or "over" (str), not integer counts or booleans.

    Kills an impl that returns violation counts or True/False as values.
    """
    problems = [
        _p("alpha", i)
        for i in range(3)  # count=3, threshold=1 -> "over"
    ] + [
        _p("beta")  # count=1, threshold=5 -> "ok"
    ]
    thresholds = {"alpha": 1, "beta": 5}

    result = budget_status(problems, thresholds)

    assert result["alpha"] == "over", "over-threshold must be string 'over'; got " + repr(
        result["alpha"]
    )
    assert result["beta"] == "ok", "compliant must be string 'ok'; got " + repr(result["beta"])
    assert all(isinstance(v, str) for v in result.values()), "all values must be str; got " + repr(
        result
    )
