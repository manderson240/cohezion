"""Item 282: class_severity_vector() — fixed-order severity count vector for a class (2026-06-08).

``class_severity_vector(problems: list[Problem], cls: str, severities: list[str]) -> tuple[int, ...]``:
Returns a tuple of counts, one per label in *severities* (in the exact specified order),
counting only problems in *cls*.  Absent severities get count 0.
Empty *severities* → ().  Empty *problems* → all-zeros tuple.  Pure; no I/O.

Discriminating tests — each kills a plausible wrong implementation:

  1. PRIMARY DISC.: counts in the SPECIFIED ORDER, not alphabetical/frequency order.
     Kills impl sorting severity labels before building the vector.
  2. Absent severity in the class gets count 0 (not KeyError or skipped slot).
     Kills impl that omits absent severities from the output tuple.
  3. Only counts problems for *cls* (not all classes).
     Kills impl aggregating across all classes.
  4. Empty severities list → () empty tuple.
     Kills impl raising or returning None.
  5. Return type is tuple[int, ...] (not list or dict).
     Kills impl returning a list.
"""
from __future__ import annotations

from cohezion.compound.problem_discovery import (
    Problem,
    class_severity_vector,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _p(cls: str, idx: int, sev: str = "") -> Problem:
    return Problem(problem_class=cls, finding_id=f"{cls}:{idx}", severity=sev)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_counts_in_specified_order_not_alpha() -> None:
    """Counts are in the caller-specified order, NOT alphabetical or frequency order.

    PRIMARY DISCRIMINATOR: kills impl that sorts severity labels.
    severities=['LOW', 'HIGH', 'CRITICAL']. alpha: 2 HIGH, 1 LOW, 0 CRITICAL.
    Vector must be (1, 2, 0) matching the specified order LOW→HIGH→CRITICAL.
    Alphabetical order would be CRITICAL→HIGH→LOW → (0, 2, 1) (different).
    """
    problems = [
        _p("alpha", 0, "HIGH"), _p("alpha", 1, "HIGH"),
        _p("alpha", 2, "LOW"),
    ]
    result = class_severity_vector(problems, "alpha", ["LOW", "HIGH", "CRITICAL"])
    assert result == (1, 2, 0), (
        "LOW→HIGH→CRITICAL order: expected (1, 2, 0); got " + repr(result)
    )


def test_absent_severity_gets_zero() -> None:
    """Absent severity in the class gets count 0, not an error or omission.

    Kills impl that omits absent severities or raises KeyError.
    alpha has only HIGH. Requesting ['HIGH', 'LOW', 'CRITICAL'] → (count_HIGH, 0, 0).
    """
    problems = [_p("alpha", 0, "HIGH"), _p("alpha", 1, "HIGH")]
    result = class_severity_vector(problems, "alpha", ["HIGH", "LOW", "CRITICAL"])
    assert result == (2, 0, 0), (
        "alpha has 2 HIGH, 0 LOW, 0 CRITICAL; expected (2, 0, 0); got " + repr(result)
    )


def test_counts_only_for_specified_class() -> None:
    """Only counts problems in *cls*, ignoring other classes.

    Kills impl aggregating across all classes.
    alpha: 2 HIGH; beta: 3 HIGH. Vector for alpha must use alpha's 2, not 5.
    """
    problems = [
        _p("alpha", 0, "HIGH"), _p("alpha", 1, "HIGH"),
        _p("beta", 0, "HIGH"), _p("beta", 1, "HIGH"), _p("beta", 2, "HIGH"),
    ]
    result = class_severity_vector(problems, "alpha", ["HIGH"])
    assert result == (2,), (
        "Vector for alpha only: expected (2,); beta ignored; got " + repr(result)
    )


def test_empty_severities_returns_empty_tuple() -> None:
    """Empty severities list → () empty tuple.

    Kills impl raising or returning None.
    """
    problems = [_p("alpha", 0, "HIGH")]
    result = class_severity_vector(problems, "alpha", [])
    assert result == (), "Empty severities → (); got " + repr(result)


def test_return_type_is_tuple_of_ints() -> None:
    """Return type is tuple[int, ...], not list or dict.

    Kills impl returning a list.
    """
    problems = [_p("alpha", 0, "HIGH"), _p("alpha", 1, "LOW")]
    result = class_severity_vector(problems, "alpha", ["HIGH", "LOW"])
    assert isinstance(result, tuple), "Must return tuple; got " + repr(type(result))
    assert all(isinstance(c, int) for c in result), (
        "All elements must be int; got " + repr(result)
    )
