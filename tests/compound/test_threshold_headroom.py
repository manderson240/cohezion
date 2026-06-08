"""Item 220: threshold_headroom() — per-class remaining budget (2026-06-08).

``threshold_headroom(problems: list[Problem], thresholds: dict[str, int])``
-> ``dict[str, int]``:
Returns ``{class: threshold - count}`` for every monitored class that is AT OR
BELOW its threshold (i.e. classes still within budget).  Over-threshold classes
are absent.  Unmonitored classes are absent.  Empty *thresholds* -> ``{}``.
Pure; no I/O.

The positive complement to ``threshold_violations`` (which returns excesses for
over-threshold classes).  Together they cover the full picture::

    headroom = threshold_headroom(findings, limits)
    violations = threshold_violations(findings, limits)

Discriminating tests -- each kills a plausible wrong implementation:

  1. PRIMARY DISC.: value is threshold - count (not a boolean flag).
     Kills an impl that returns {class: True} or {class: 1} instead of
     the actual remaining budget magnitude.
  2. Over-threshold class is absent.
     Kills an impl that includes all monitored classes with value clamped to 0.
  3. At-threshold class is present with headroom=0.
     Kills an impl that treats headroom=0 as "no remaining budget" and omits it.
  4. Unmonitored class is absent.
     Kills an impl that returns headroom for all classes present in problems.
  5. Empty thresholds -> {}.
     Kills an impl that raises or returns None on empty thresholds.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import (
    Problem,
    threshold_headroom,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _p(cls: str, idx: int = 0) -> Problem:
    return Problem(problem_class=cls, finding_id=f"{cls}:{idx}")


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_headroom_value_is_threshold_minus_count() -> None:
    """Headroom is threshold - count, not a boolean or capped value.

    PRIMARY DISCRIMINATOR: kills an impl that returns True/1 instead of
    the actual remaining budget.
    alpha: count=2, threshold=5 -> headroom=3.
    beta:  count=0, threshold=4 -> headroom=4.
    """
    problems = [_p("alpha", i) for i in range(2)]
    thresholds = {"alpha": 5, "beta": 4}

    result = threshold_headroom(problems, thresholds)

    assert result.get("alpha") == 3, "alpha headroom must be 5-2=3; got " + repr(
        result.get("alpha")
    )
    assert result.get("beta") == 4, "beta headroom must be 4-0=4; got " + repr(result.get("beta"))


def test_over_threshold_class_absent() -> None:
    """Class exceeding threshold must be absent from headroom dict.

    Kills an impl that clamps all values to 0 and includes everything.
    """
    problems = [_p("complexity_outlier", i) for i in range(5)]
    thresholds = {"complexity_outlier": 3}  # count=5 > threshold=3 -> over -> absent

    result = threshold_headroom(problems, thresholds)

    assert "complexity_outlier" not in result, "over-threshold class must be absent; got " + repr(
        result
    )
    assert result == {}


def test_at_threshold_class_present_with_zero_headroom() -> None:
    """At-threshold class is present with headroom=0.

    Kills an impl that omits zero-headroom classes as if they were violations.
    count == threshold -> headroom = 0 -> still within budget, still in result.
    """
    problems = [_p("alpha", i) for i in range(3)]
    thresholds = {"alpha": 3}  # count=3 == threshold=3 -> headroom=0

    result = threshold_headroom(problems, thresholds)

    assert "alpha" in result, "at-threshold class must be present; got " + repr(result)
    assert result["alpha"] == 0, "at-threshold headroom must be 0; got " + repr(result["alpha"])


def test_unmonitored_class_absent() -> None:
    """Class not in thresholds must be absent from headroom dict.

    Kills an impl that includes all classes found in problems.
    """
    problems = [_p("nesting_outlier")]
    thresholds = {"complexity_outlier": 5}

    result = threshold_headroom(problems, thresholds)

    assert "nesting_outlier" not in result, "unmonitored class must be absent; got " + repr(result)


def test_empty_thresholds_returns_empty_dict() -> None:
    """Empty thresholds -> {}.

    Kills an impl that raises or returns None on empty thresholds.
    """
    problems = [_p("alpha"), _p("beta")]
    result = threshold_headroom(problems, {})
    assert result == {}, "Empty thresholds must return {}; got " + repr(result)
