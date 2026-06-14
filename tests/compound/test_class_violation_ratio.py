"""Item 221: class_violation_ratio() — relative load per monitored class (2026-06-08).

``class_violation_ratio(problems: list[Problem], thresholds: dict[str, int])``
-> ``dict[str, float]``:
Returns ``{cls: count / threshold}`` for every monitored class with
``threshold > 0``.  Ratio > 1.0 = over threshold; 1.0 = exactly at;
< 1.0 = under.  Unmonitored classes absent.  Zero-threshold classes absent
(division guard).  Empty thresholds -> ``{}``.  Pure; no I/O.

Unlike ``threshold_headroom`` (absolute remaining budget for under-threshold
classes only), this covers ALL monitored classes with a relative load::

    ratios = class_violation_ratio(findings, limits)
    worst = max(ratios, key=ratios.get)  # class under most relative pressure

Discriminating tests -- each kills a plausible wrong implementation:

  1. PRIMARY DISC.: ratio is float count/threshold (not int or clipped-to-1).
     Kills an impl that returns integer division or caps ratio at 1.0.
  2. Over-threshold class IS included (ratio > 1.0), unlike headroom which
     excludes over-threshold classes.
     Kills an impl that omits over-threshold entries.
  3. Zero-threshold class is absent (division guard, no ZeroDivisionError).
     Kills an impl that raises or returns inf for threshold=0.
  4. Unmonitored class is absent.
     Kills an impl that returns ratios for all classes present in problems.
  5. Empty thresholds -> {}.
     Kills an impl that raises or iterates over all problems.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import (
    Problem,
    class_violation_ratio,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _p(cls: str, idx: int = 0) -> Problem:
    return Problem(problem_class=cls, finding_id=f"{cls}:{idx}")


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_ratio_is_float_not_integer() -> None:
    """Ratio is count/threshold as a true float, not integer division or 0/1.

    PRIMARY DISCRIMINATOR: kills an impl returning int(count/threshold) or
    a boolean.  alpha: count=1, threshold=4 -> ratio=0.25 (not 0).
    """
    problems = [_p("alpha", 0)]
    thresholds = {"alpha": 4}

    result = class_violation_ratio(problems, thresholds)

    assert result.get("alpha") == 0.25, "ratio must be 1/4=0.25 (float); got " + repr(
        result.get("alpha")
    )
    assert isinstance(result.get("alpha"), float), "value type must be float; got " + repr(
        type(result.get("alpha"))
    )


def test_over_threshold_class_included_with_ratio_above_one() -> None:
    """Over-threshold class IS present in result with ratio > 1.0.

    Kills an impl that omits over-threshold classes (like threshold_headroom
    does) instead of reporting them with ratio > 1.0.
    count=6, threshold=3 -> ratio=2.0.
    """
    problems = [_p("complexity_outlier", i) for i in range(6)]
    thresholds = {"complexity_outlier": 3}

    result = class_violation_ratio(problems, thresholds)

    assert "complexity_outlier" in result, "over-threshold class must be in result; got " + repr(
        result
    )
    assert result["complexity_outlier"] == 2.0, "ratio must be 6/3=2.0; got " + repr(
        result["complexity_outlier"]
    )


def test_zero_threshold_class_absent_no_division_error() -> None:
    """threshold=0 class is absent (division guard — no ZeroDivisionError).

    Kills an impl that raises ZeroDivisionError or returns inf/nan for
    threshold=0.
    """
    problems = [_p("alpha", 0)]
    thresholds = {"alpha": 0, "beta": 4}

    result = class_violation_ratio(problems, thresholds)

    assert "alpha" not in result, "zero-threshold class must be absent; got " + repr(result)
    # beta: count=0, threshold=4 -> 0/4=0.0
    assert result.get("beta") == 0.0, "beta ratio must be 0/4=0.0; got " + repr(result.get("beta"))


def test_unmonitored_class_absent() -> None:
    """Class not in thresholds is not included in the result.

    Kills an impl that computes ratios for all classes in problems.
    """
    problems = [_p("alpha", 0), _p("gamma", 0)]
    thresholds = {"alpha": 2}

    result = class_violation_ratio(problems, thresholds)

    assert "gamma" not in result, "unmonitored class must be absent; got " + repr(result)
    assert result.get("alpha") == 0.5, "alpha ratio must be 1/2=0.5; got " + repr(
        result.get("alpha")
    )


def test_empty_thresholds_returns_empty_dict() -> None:
    """Empty thresholds -> {}.

    Kills an impl that raises or iterates over all problems.
    """
    problems = [_p("alpha"), _p("beta")]
    result = class_violation_ratio(problems, {})
    assert result == {}, "Empty thresholds must return {}; got " + repr(result)
