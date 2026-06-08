"""Item 496: largest_regression() -- class with highest score increase (2026-06-08).

``largest_regression(before, after, weights) -> tuple[str, float] | None``:
Returns (class_name, delta) for the class with the HIGHEST positive score delta.
None when no class regressed.  Tie-break alphabetically.  Pure; no I/O.

Discriminating tests -- each kills a plausible wrong implementation:

  1. PRIMARY DISC.: returns tuple (class, delta) not frozenset.
     ClassA delta=+5.0 is largest -> ('ClassA', 5.0), not frozenset({'ClassA'}).
     Kills impl reusing regressing_classes.
  2. Returns max positive delta (not max abs delta).
     ClassA delta=-8.0 (big improvement), ClassB delta=+2.0 -> ('ClassB', 2.0).
     Kills impl taking max of abs values (would return ClassA).
  3. None when no class regressed.
     all classes improving or stable -> None (not raise).
  4. Alphabetical tie-break: two classes with same max delta -> alphabetically first.
     Kills impl with non-deterministic tie resolution.
  5. Only positive deltas count; stable/improving classes ignored entirely.
     ClassA delta=0.0 (stable), ClassB delta=-2.0 (improving) -> None.
     Kills impl that returns the "largest" delta even if it's <=0.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import (
    Problem,
    largest_regression,
)


def _p(cls: str, fid: str, sev: str) -> Problem:
    return Problem(problem_class=cls, finding_id=fid, severity=sev)


WEIGHTS = {"HIGH": 3.0, "LOW": 1.0}


def test_returns_tuple_not_frozenset() -> None:
    """PRIMARY DISC.: returns (class, delta) tuple, not frozenset.

    ClassA delta=+5.0 (worst) -> ('ClassA', 5.0).
    Kills impl reusing regressing_classes (wrong type).
    """
    before = [_p("ClassA", "f1", "LOW"), _p("ClassB", "f2", "HIGH"), _p("ClassB", "f3", "HIGH")]
    after  = [_p("ClassA", "f4", "HIGH"), _p("ClassA", "f5", "HIGH"), _p("ClassB", "f6", "LOW")]
    # ClassA: 1.0 -> 6.0 = +5.0; ClassB: 6.0 -> 1.0 = -5.0
    result = largest_regression(before, after, WEIGHTS)
    assert isinstance(result, tuple), "Must return tuple; got " + repr(type(result))
    assert result == ("ClassA", 5.0), "ClassA has max positive delta; got " + repr(result)


def test_max_positive_delta_not_max_abs_delta() -> None:
    """Returns class with max POSITIVE delta, ignoring large negative deltas.

    ClassA: big improvement (-8.0), ClassB: small regression (+2.0).
    -> ('ClassB', 2.0), not ClassA (abs=8.0 but negative).
    Kills impl using max abs delta.
    """
    before = [
        _p("ClassA", "f1", "HIGH"), _p("ClassA", "f2", "HIGH"), _p("ClassA", "f3", "HIGH"),  # 9.0
        _p("ClassB", "f4", "LOW"),  # 1.0
    ]
    after = [
        _p("ClassA", "f5", "LOW"),  # 1.0 (delta = -8.0)
        _p("ClassB", "f6", "HIGH"),  # 3.0 (delta = +2.0)
    ]
    result = largest_regression(before, after, WEIGHTS)
    assert result is not None, "ClassB regressed; result should not be None"
    assert result[0] == "ClassB", "ClassB has max positive delta (+2.0); got " + repr(result)
    assert abs(result[1] - 2.0) < 1e-9, "Delta=+2.0; got " + repr(result)


def test_none_when_no_regression() -> None:
    """None when no class has positive delta (all improving or stable)."""
    before = [_p("ClassA", "f1", "HIGH"), _p("ClassB", "f2", "HIGH")]
    after  = [_p("ClassA", "f3", "LOW"), _p("ClassB", "f4", "LOW")]
    result = largest_regression(before, after, WEIGHTS)
    assert result is None, "No positive delta -> None; got " + repr(result)


def test_alphabetical_tie_break() -> None:
    """Two classes with equal max delta -> alphabetically first class wins."""
    before = [_p("ClassZ", "f1", "LOW"), _p("ClassA", "f2", "LOW")]
    after  = [_p("ClassZ", "f3", "HIGH"), _p("ClassA", "f4", "HIGH")]
    # ClassZ: 1.0->3.0=+2.0; ClassA: 1.0->3.0=+2.0 -> tie; ClassA first alphabetically
    result = largest_regression(before, after, WEIGHTS)
    assert result is not None
    assert result[0] == "ClassA", "Tie -> alphabetically first; got " + repr(result)


def test_stable_and_improving_only_returns_none() -> None:
    """Stable (delta=0) and improving (delta<0) classes -> None."""
    before = [_p("Stable", "f1", "HIGH"), _p("Better", "f2", "HIGH"), _p("Better", "f3", "HIGH")]
    after  = [_p("Stable", "f4", "HIGH"), _p("Better", "f5", "LOW")]
    result = largest_regression(before, after, WEIGHTS)
    assert result is None, "No positive delta -> None; got " + repr(result)
