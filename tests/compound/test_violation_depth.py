"""Item 231: violation_depth() — per-class violation depth map (2026-06-08).

``violation_depth(problems: list[Problem], thresholds: dict[str, int])``
-> ``dict[str, int]``:
Returns ``{cls: count - threshold}`` for every monitored class where
``count > threshold``.  Compliant classes (count ≤ threshold) are absent.
Empty *thresholds* or no violations → ``{}``.  Pure; no I/O.

The value is always positive (count - threshold > 0).  This is the
absolute-value complement of :func:`signed_headroom`'s negative portion:
more readable for "how many over the limit is each violating class?".

Discriminating tests -- each kills a plausible wrong implementation:

  1. PRIMARY DISC.: violating class depth = count - threshold (positive).
     Kills an impl that returns signed headroom (threshold - count, negative)
     or raw count rather than the excess.
  2. Compliant class (count ≤ threshold) absent.
     Kills an impl that includes all monitored classes.
  3. At-threshold class absent (count == threshold → depth 0, not a violation).
     Kills an impl using ≥ instead of > for the violation check.
  4. Multiple violations all present with correct depths.
     Kills an impl that only returns the worst violator.
  5. Empty thresholds -> {}.
     Kills an impl that raises or returns a non-empty dict.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import (
    Problem,
    violation_depth,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _p(cls: str, idx: int = 0) -> Problem:
    return Problem(problem_class=cls, finding_id=f"{cls}:{idx}")


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_violating_class_has_positive_depth() -> None:
    """Violating class depth = count - threshold (always positive).

    PRIMARY DISCRIMINATOR: kills an impl that returns signed headroom
    (threshold - count, which would be negative) or raw count.
    alpha: count=7, threshold=3 -> depth = 7 - 3 = 4 (positive).
    """
    problems = [_p("alpha", i) for i in range(7)]
    thresholds = {"alpha": 3}

    result = violation_depth(problems, thresholds)

    assert result == {"alpha": 4}, (
        "alpha (count=7, threshold=3) depth must be 4; got " + repr(result)
    )


def test_compliant_class_absent() -> None:
    """Compliant class (count ≤ threshold) is absent from the result.

    Kills an impl that returns all monitored classes.
    alpha: count=2, threshold=5 -> compliant -> absent.
    """
    problems = [_p("alpha", i) for i in range(2)]
    thresholds = {"alpha": 5, "beta": 10}  # alpha: under; beta: count=0 under

    result = violation_depth(problems, thresholds)

    assert result == {}, "No violations -> result must be {}; got " + repr(result)


def test_at_threshold_class_absent() -> None:
    """Class exactly at threshold (count == threshold) is not a violation.

    Kills an impl using >= instead of > for the violation check.
    alpha: count=4, threshold=4 -> depth=0 -> NOT in result.
    """
    problems = [_p("alpha", i) for i in range(4)]
    thresholds = {"alpha": 4}

    result = violation_depth(problems, thresholds)

    assert "alpha" not in result, (
        "alpha (count=4 == threshold=4) must not appear in violation_depth; got " + repr(result)
    )
    assert result == {}, "at-threshold class must give empty dict; got " + repr(result)


def test_multiple_violations_all_present() -> None:
    """All violating classes appear with their individual depths.

    Kills an impl that only returns the worst violator.
    alpha: count=6, threshold=3 -> depth=3
    beta:  count=9, threshold=5 -> depth=4
    gamma: count=4, threshold=4 -> depth=0 (at-threshold, absent)
    """
    problems = (
        [_p("alpha", i) for i in range(6)]
        + [_p("beta", i) for i in range(9)]
        + [_p("gamma", i) for i in range(4)]
    )
    thresholds = {"alpha": 3, "beta": 5, "gamma": 4}

    result = violation_depth(problems, thresholds)

    assert result.get("alpha") == 3, f"alpha depth must be 3; got {result!r}"
    assert result.get("beta") == 4, f"beta depth must be 4; got {result!r}"
    assert "gamma" not in result, f"gamma at-threshold must be absent; got {result!r}"


def test_empty_thresholds_returns_empty_dict() -> None:
    """Empty thresholds -> {}.

    Kills an impl that raises or returns a non-empty dict.
    """
    problems = [_p("alpha", i) for i in range(10)]
    result = violation_depth(problems, {})
    assert result == {}, "Empty thresholds must return {}; got " + repr(result)
