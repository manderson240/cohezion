"""Item 307: most_volatile_class() — class with highest total absolute severity delta (2026-06-08).

``most_volatile_class(scan_a, scan_b) -> str | None``:
Returns the class name with the highest sum(abs(delta)) across all its severity
deltas (using severity_delta_per_class).  A class that gained 3 CRITICAL and
lost 3 LOW has volatility 6 even if net delta is 0.
Ties broken by class name ascending.  No severity changes -> None.
Pure; no I/O.

Discriminating tests — each kills a plausible wrong implementation:

  1. PRIMARY DISC.: volatility = sum(abs(delta)) over all severities, NOT max delta.
     Kills impl that uses the single largest delta instead of the sum.
  2. Correct class returned when multiple classes have severity deltas.
     Kills impl returning any arbitrary class.
  3. Tie-break by class name ascending (alphabetically first wins on equal volatility).
     Kills impl with wrong tie-break direction.
  4. No severity changes -> None (not a class with 0 volatility).
     Kills impl returning a string on no-change input.
  5. Unlabelled problems (severity='') are ignored in volatility calculation.
     Kills impl that counts empty-severity as a severity bucket.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import (
    Problem,
    most_volatile_class,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _p(cls: str, sev: str, idx: int) -> Problem:
    return Problem(problem_class=cls, finding_id=f"{cls}:{sev}:{idx}", severity=sev)


def _pu(cls: str, idx: int) -> Problem:
    """Unlabelled problem (severity='')."""
    return Problem(problem_class=cls, finding_id=f"{cls}:u:{idx}")


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_sum_of_absolute_deltas_not_max_delta() -> None:
    """Volatility = sum(abs(delta)) over all severities, not max delta.

    PRIMARY DISCRIMINATOR: kills impl using max delta.
    alpha: +1 CRITICAL only -> volatility=1.
    beta: +2 HIGH, -3 LOW -> volatility=5 (sum of abs).
    beta should win despite alpha having a smaller single peak.
    """
    scan_a = [
        _p("alpha", "CRITICAL", 0),          # alpha: 1 CRITICAL
        _p("beta", "LOW", 0), _p("beta", "LOW", 1), _p("beta", "LOW", 2),  # beta: 3 LOW
    ]
    scan_b = [
        _p("alpha", "CRITICAL", 0), _p("alpha", "CRITICAL", 1),  # alpha: 2 CRITICAL (+1)
        _p("beta", "HIGH", 0), _p("beta", "HIGH", 1),            # beta: 2 HIGH (+2)
        # beta LOW: 0 (disappeared, -3)
    ]
    result = most_volatile_class(scan_a, scan_b)
    assert result == "beta", (
        "beta: |+2|+|-3|=5 > alpha: |+1|=1 -> beta wins; got " + repr(result)
    )


def test_correct_class_returned_among_multiple() -> None:
    """Returns the class with the highest sum(abs(delta)).

    Kills impl returning an arbitrary class.
    gamma: |+3|=3 vs delta_cls: |+1|=1 -> gamma wins.
    """
    scan_a = [_p("delta_cls", "MEDIUM", 0)]
    scan_b = [
        _p("delta_cls", "MEDIUM", 0), _p("delta_cls", "MEDIUM", 1),  # delta_cls: +1
        _p("gamma", "HIGH", 0), _p("gamma", "HIGH", 1), _p("gamma", "HIGH", 2),  # gamma: +3
    ]
    result = most_volatile_class(scan_a, scan_b)
    assert result == "gamma", (
        "gamma volatility 3 > delta_cls volatility 1; got " + repr(result)
    )


def test_tie_break_by_class_name_ascending() -> None:
    """Equal volatility -> alphabetically first class name wins.

    Kills impl with wrong tie-break.
    alpha and beta both have volatility=2; alpha < beta -> alpha wins.
    """
    scan_a = [
        _p("beta", "HIGH", 0), _p("beta", "HIGH", 1),
        _p("alpha", "CRITICAL", 0), _p("alpha", "CRITICAL", 1),
    ]
    scan_b = []  # both gone -> alpha: |-2|=2, beta: |-2|=2
    result = most_volatile_class(scan_a, scan_b)
    assert result == "alpha", (
        "alpha < beta on tie -> alpha wins; got " + repr(result)
    )


def test_no_severity_changes_returns_none() -> None:
    """No severity changes at all -> None.

    Kills impl returning a class string when volatility is 0.
    Both scans have same problems -> no delta -> None.
    """
    scan_a = [_p("alpha", "HIGH", 0), _p("alpha", "HIGH", 1)]
    scan_b = [_p("alpha", "HIGH", 0), _p("alpha", "HIGH", 1)]  # unchanged
    result = most_volatile_class(scan_a, scan_b)
    assert result is None, "No changes -> None; got " + repr(result)


def test_unlabelled_problems_ignored_in_volatility() -> None:
    """Problems with empty severity label don't count toward volatility.

    Kills impl that treats '' as a severity bucket.
    alpha: only unlabelled problems change -> volatility=0 -> not counted.
    beta: 1 CRITICAL added -> volatility=1 -> beta wins.
    """
    scan_a = [_pu("alpha", 0)]
    scan_b = [
        _pu("alpha", 0), _pu("alpha", 1),     # alpha: unlabelled changed (ignored)
        _p("beta", "CRITICAL", 0),             # beta: 1 CRITICAL new
    ]
    result = most_volatile_class(scan_a, scan_b)
    assert result == "beta", (
        "alpha unlabelled changes ignored; beta has CRITICAL delta -> beta; got " + repr(result)
    )
