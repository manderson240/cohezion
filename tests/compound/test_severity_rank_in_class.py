"""Item 275: severity_rank_in_class() — ordinal rank of a severity within a class (2026-06-08).

``severity_rank_in_class(problems: list[Problem], cls: str, severity: str) -> int | None``:
Returns the 1-based rank of *severity* by frequency among the labelled problems in *cls*.
Rank 1 = most frequent. Ties broken by severity string ascending. Returns None when:
  - cls is absent from problems
  - cls has no labelled problems
  - severity does not appear in cls (even if cls has other labelled problems)
Pure; no I/O.

Discriminating tests — each kills a plausible wrong implementation:

  1. PRIMARY DISC.: rank is by FREQUENCY, not alphabetical. A low-frequency severity that
     sorts first alphabetically should not receive rank 1.
     Kills impl ranking alphabetically instead of by count.
  2. Tie-break: alphabetically ascending severity string.
     Kills impl with wrong tie-break direction.
  3. None when severity absent from class.
     Kills impl returning 0 or len+1 for absent severity.
  4. None when class has no labelled problems.
     Kills impl that counts unlabelled as labelled.
  5. Return type is int | None (not float or list).
     Kills impl returning a count instead of a rank.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import (
    Problem,
    severity_rank_in_class,
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


def test_rank_is_by_frequency_not_alphabet() -> None:
    """Rank is by FREQUENCY descending, not alphabetical order.

    PRIMARY DISCRIMINATOR: kills impl ranking alphabetically.
    alpha class: LOW x3, CRITICAL x1. LOW is more frequent -> LOW rank=1.
    CRITICAL is less frequent -> CRITICAL rank=2.
    Alphabetically CRITICAL < LOW, so alphabetical impl would give CRITICAL rank=1.
    """
    problems = [
        _ps("alpha", i, "LOW") for i in range(3)
    ] + [_ps("alpha", 10, "CRITICAL")]
    assert severity_rank_in_class(problems, "alpha", "LOW") == 1, (
        "LOW is most frequent (3) -> rank 1"
    )
    assert severity_rank_in_class(problems, "alpha", "CRITICAL") == 2, (
        "CRITICAL is less frequent (1) -> rank 2"
    )


def test_tie_break_alphabetically_ascending() -> None:
    """Tie-break on equal frequency: alphabetically ascending severity gets lower rank.

    Kills impl with wrong tie-break direction (e.g. descending).
    alpha class: HIGH x2, LOW x2. HIGH < LOW alphabetically -> HIGH rank=1.
    """
    problems = [
        _ps("alpha", 0, "HIGH"),
        _ps("alpha", 1, "HIGH"),
        _ps("alpha", 2, "LOW"),
        _ps("alpha", 3, "LOW"),
    ]
    assert severity_rank_in_class(problems, "alpha", "HIGH") == 1, (
        "HIGH tied with LOW; HIGH < LOW alphabetically -> rank 1"
    )
    assert severity_rank_in_class(problems, "alpha", "LOW") == 2, (
        "LOW tied with HIGH; LOW > HIGH alphabetically -> rank 2"
    )


def test_none_when_severity_absent_from_class() -> None:
    """None when the severity does not appear in the class.

    Kills impl returning 0 or len+1 for absent severity.
    """
    problems = [_ps("alpha", 0, "HIGH"), _ps("alpha", 1, "HIGH")]
    result = severity_rank_in_class(problems, "alpha", "CRITICAL")
    assert result is None, "CRITICAL not in alpha -> None; got " + repr(result)


def test_none_when_class_has_no_labelled_problems() -> None:
    """None when class has problems but all are unlabelled (severity='').

    Kills impl that counts unlabelled as labelled.
    """
    problems = [_p("alpha", 0), _p("alpha", 1)]
    result = severity_rank_in_class(problems, "alpha", "")
    assert result is None, "No labelled problems in alpha -> None; got " + repr(result)


def test_return_type_is_int_or_none() -> None:
    """Return type is int | None, not float or list.

    Kills impl returning count instead of rank.
    """
    problems = [_ps("alpha", 0, "HIGH"), _ps("alpha", 1, "HIGH")]
    result = severity_rank_in_class(problems, "alpha", "HIGH")
    assert isinstance(result, int), "With match -> int; got " + repr(type(result))
    none_result = severity_rank_in_class(problems, "alpha", "CRITICAL")
    assert none_result is None, "Without match -> None; got " + repr(none_result)
