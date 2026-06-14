"""Item 233: scan_pressure() — composite scan pressure score (2026-06-08).

``scan_pressure(problems: list[Problem], thresholds: dict[str, int])``
-> ``float``:
Returns ``float(violations_count + total_violation_depth(...))``.
A single number summarising overall scan pressure.
  - 0.0 when scan is fully healthy (no violations).
  - Increases with more violating classes AND deeper violations.
Pure; no I/O.  Always ≥ 0.0.

Discriminating tests -- each kills a plausible wrong implementation:

  1. PRIMARY DISC.: returns 0.0 when the scan is healthy (kills impls that
     return total finding count or violation count alone when there are
     findings but no violations).
  2. Combines violations_count AND total_depth (not just one component).
     Kills an impl returning only violation count (misses depth).
     Kills an impl returning only total_violation_depth (misses class count).
  3. Return type is float, not int or dict.
     Kills an impl returning int or violation_depth dict directly.
  4. Empty thresholds -> 0.0.
     Kills an impl that raises or returns a non-zero value.
  5. Single violating class: pressure = 1 (class) + depth.
     Kills an impl that double-counts or misses the class component.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import (
    Problem,
    scan_pressure,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _p(cls: str, idx: int = 0) -> Problem:
    return Problem(problem_class=cls, finding_id=f"{cls}:{idx}")


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_zero_when_no_violations() -> None:
    """scan_pressure = 0.0 when all classes are within threshold.

    PRIMARY DISCRIMINATOR: kills an impl that returns total finding count
    or any non-zero value for a healthy scan.
    """
    problems = [_p("alpha", i) for i in range(3)] + [_p("beta", i) for i in range(2)]
    thresholds = {"alpha": 5, "beta": 5}

    result = scan_pressure(problems, thresholds)

    assert result == 0.0, "Healthy scan must yield pressure=0.0; got " + repr(result)


def test_combines_violation_count_and_depth() -> None:
    """Pressure = violations_count + total_violation_depth (both components).

    Kills an impl returning only violation_count (1) or only total_depth (3).
    alpha: count=6, threshold=3 -> 1 violating class, depth=3.
    Expected pressure = 1 + 3 = 4.0.
    """
    problems = [_p("alpha", i) for i in range(6)]
    thresholds = {"alpha": 3}

    result = scan_pressure(problems, thresholds)

    assert result == 4.0, "1 class + depth=3 -> pressure=4.0; got " + repr(result)


def test_return_type_is_float() -> None:
    """Return type is float, not int.

    Kills an impl returning int or the violation_depth dict.
    """
    problems = [_p("alpha", i) for i in range(5)]
    thresholds = {"alpha": 2}

    result = scan_pressure(problems, thresholds)

    assert isinstance(result, float), "Return type must be float; got " + repr(type(result))
    # 1 violating class + depth=3 -> 4.0
    assert result == 4.0


def test_empty_thresholds_returns_zero_float() -> None:
    """Empty thresholds -> 0.0.

    Kills an impl that raises or returns non-zero.
    """
    problems = [_p("alpha", i) for i in range(10)]
    result = scan_pressure(problems, {})
    assert result == 0.0, "Empty thresholds must return 0.0; got " + repr(result)
    assert isinstance(result, float)


def test_multiple_violations_pressure_sums_both_axes() -> None:
    """Multiple violating classes: count and depth both accumulate.

    alpha: count=5, threshold=3 -> depth=2
    beta:  count=7, threshold=4 -> depth=3
    violations_count=2, total_depth=5, pressure=2+5=7.0.
    Kills an impl that returns max(count, depth) or either alone.
    """
    problems = [_p("alpha", i) for i in range(5)] + [_p("beta", i) for i in range(7)]
    thresholds = {"alpha": 3, "beta": 4}

    result = scan_pressure(problems, thresholds)

    assert result == 7.0, "2 classes + total_depth=5 -> pressure=7.0; got " + repr(result)
