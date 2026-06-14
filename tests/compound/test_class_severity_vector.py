"""Item 282: class_severity_vector() — fixed-order severity count vector (2026-06-08).

``class_severity_vector(problems, cls, severities) -> tuple[int, ...]``:
Returns a tuple of counts, one per severity label in *severities*, in the specified
order. Count is 0 for any severity absent from *cls*. Empty severities -> ().
Pure; no I/O.

Discriminating tests -- each kills a plausible wrong implementation:

  1. PRIMARY DISC.: counts returned in the SPECIFIED ORDER (not alphabetical or by
     frequency). [LOW, HIGH] returns (low_count, high_count) even if HIGH > LOW.
     Kills impl sorting by frequency or alphabetically.
  2. Absent severity gets 0 (not KeyError or omitted).
     Kills impl that raises or skips absent severities.
  3. Empty severities list -> empty tuple ().
     Kills impl returning a dict or raising.
  4. Empty problems -> tuple of zeros (one per severity).
     Kills impl returning () when problems is empty.
  5. Return type is tuple (not list or dict).
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


def _ps(cls: str, idx: int, sev: str) -> Problem:
    return Problem(problem_class=cls, finding_id=f"{cls}:{idx}", severity=sev)


def _p(cls: str, idx: int) -> Problem:
    return Problem(problem_class=cls, finding_id=f"{cls}:{idx}")


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_counts_in_specified_order() -> None:
    """Counts are in the order given by severities, not alphabetical or frequency.

    PRIMARY DISCRIMINATOR: kills impl sorting alphabetically or by frequency.
    alpha: HIGH x3, LOW x1. severities=[LOW, HIGH] -> (1, 3) not (3, 1).
    Alphabetical order would give [HIGH, LOW] -> (3, 1) for sorted impl.
    Frequency order would give (3, 1) as HIGH is more frequent.
    """
    problems = [_ps("alpha", i, "HIGH") for i in range(3)] + [_ps("alpha", 10, "LOW")]
    result = class_severity_vector(problems, "alpha", ["LOW", "HIGH"])
    assert result == (1, 3), "[LOW, HIGH] order -> (low_count=1, high_count=3); got " + repr(result)


def test_absent_severity_returns_zero() -> None:
    """Absent severity in the vector gets count 0, not KeyError.

    Kills impl that raises or skips absent severities.
    """
    problems = [_ps("alpha", 0, "HIGH")]
    result = class_severity_vector(problems, "alpha", ["HIGH", "CRITICAL", "LOW"])
    assert result == (1, 0, 0), "CRITICAL and LOW absent -> 0; got " + repr(result)


def test_empty_severities_returns_empty_tuple() -> None:
    """Empty severities list -> empty tuple ().

    Kills impl returning a dict or raising on empty severities.
    """
    problems = [_ps("alpha", 0, "HIGH")]
    result = class_severity_vector(problems, "alpha", [])
    assert result == (), "Empty severities -> (); got " + repr(result)


def test_empty_problems_returns_zeros() -> None:
    """Empty problems -> tuple of zeros (one per severity, not empty tuple).

    Kills impl returning () when problems is empty.
    """
    result = class_severity_vector([], "alpha", ["HIGH", "LOW", "CRITICAL"])
    assert result == (0, 0, 0), "Empty problems -> all zeros, not (); got " + repr(result)


def test_return_type_is_tuple() -> None:
    """Return type is tuple, not list or dict.

    Kills impl returning a list.
    """
    problems = [_ps("alpha", 0, "HIGH")]
    result = class_severity_vector(problems, "alpha", ["HIGH"])
    assert isinstance(result, tuple), "Must return tuple; got " + repr(type(result))
    assert all(isinstance(v, int) for v in result), "Elements must be int"
