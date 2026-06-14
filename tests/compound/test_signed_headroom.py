"""Item 229: signed_headroom() — full signed headroom map (2026-06-08).

``signed_headroom(problems: list[Problem], thresholds: dict[str, int])``
-> ``dict[str, int]``:
Returns ``{cls: threshold - count}`` for every monitored class.
  - Positive value  → class is under budget (remaining headroom).
  - Zero            → class is exactly at threshold (no headroom left).
  - Negative value  → class is a violation (how many findings over the limit).
Unlike ``threshold_headroom`` (which omits violating classes), this function
covers ALL monitored classes.  Unmonitored classes are absent.
Empty *thresholds* → ``{}``.  Pure; no I/O.

Discriminating tests -- each kills a plausible wrong implementation:

  1. PRIMARY DISC.: compliant class has POSITIVE headroom value.
     Kills an impl that clamps to 0, takes abs(), or returns count instead of
     (threshold - count).
  2. Violating class has NEGATIVE headroom value (violation depth).
     Kills an impl that omits violating classes (= threshold_headroom) or
     clamps negatives to 0.
  3. At-threshold class has headroom = 0 (not absent, not positive).
     Kills an impl that skips headroom=0 classes.
  4. Unmonitored class absent from the returned dict.
     Kills an impl that returns all problem classes.
  5. Empty thresholds -> {}.
     Kills an impl that raises or returns a non-empty dict.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import (
    Problem,
    signed_headroom,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _p(cls: str, idx: int = 0) -> Problem:
    return Problem(problem_class=cls, finding_id=f"{cls}:{idx}")


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_compliant_class_has_positive_headroom() -> None:
    """Compliant class headroom = threshold - count > 0.

    PRIMARY DISCRIMINATOR: kills an impl that clamps negatives to 0,
    returns count instead of (threshold - count), or delegates to
    threshold_headroom but forgets the sign direction.
    alpha: count=2, threshold=5 -> headroom = 5 - 2 = 3 (positive).
    """
    problems = [_p("alpha", i) for i in range(2)]
    thresholds = {"alpha": 5}

    result = signed_headroom(problems, thresholds)

    assert result == {"alpha": 3}, "alpha (count=2, threshold=5) headroom must be 3; got " + repr(
        result
    )


def test_violating_class_has_negative_headroom() -> None:
    """Violating class headroom = threshold - count < 0.

    Kills an impl that omits violating classes (like threshold_headroom does)
    or that clamps negative headroom to 0.
    alpha: count=7, threshold=3 -> headroom = 3 - 7 = -4 (negative).
    """
    problems = [_p("alpha", i) for i in range(7)]
    thresholds = {"alpha": 3}

    result = signed_headroom(problems, thresholds)

    assert "alpha" in result, "violating class must be present in signed_headroom; got " + repr(
        result
    )
    assert result["alpha"] == -4, "alpha (count=7, threshold=3) headroom must be -4; got " + repr(
        result["alpha"]
    )


def test_at_threshold_class_has_zero_headroom() -> None:
    """At-threshold class headroom = 0 (not absent, not positive).

    Kills an impl that skips classes with headroom=0 or treats them as
    violating.
    alpha: count=4, threshold=4 -> headroom = 4 - 4 = 0.
    """
    problems = [_p("alpha", i) for i in range(4)]
    thresholds = {"alpha": 4}

    result = signed_headroom(problems, thresholds)

    assert "alpha" in result, "at-threshold class must be present; got " + repr(result)
    assert result["alpha"] == 0, "alpha (count=4, threshold=4) headroom must be 0; got " + repr(
        result["alpha"]
    )


def test_unmonitored_class_absent() -> None:
    """Class not in thresholds must not appear in the result.

    Kills an impl that returns headroom for all problem classes.
    """
    problems = [_p("untracked")]
    thresholds = {"alpha": 10}  # untracked not monitored; alpha: count=0 -> headroom=10

    result = signed_headroom(problems, thresholds)

    assert "untracked" not in result, "unmonitored class must not appear; got " + repr(result)
    assert "alpha" in result and result["alpha"] == 10, (
        "alpha (count=0, threshold=10) must have headroom=10; got " + repr(result)
    )


def test_empty_thresholds_returns_empty_dict() -> None:
    """Empty thresholds -> {}.

    Kills an impl that raises or returns a non-empty dict.
    """
    problems = [_p("alpha"), _p("beta")]
    result = signed_headroom(problems, {})
    assert result == {}, "Empty thresholds must return {}; got " + repr(result)
