"""Item 279: most_common_severity() — globally most frequent severity label (2026-06-08).

``most_common_severity(problems: list[Problem]) -> str | None``:
Returns the labelled severity string (severity != '') with the highest
count across ALL problems.  Tie-break: ascending severity string.
None when input is empty or all problems are unlabelled.  Pure; no I/O.

Discriminating tests — each kills a plausible wrong implementation:

  1. PRIMARY DISC.: only LABELLED severities (severity != '') are considered.
     Kills impl including unlabelled ('') in the frequency count, which would
     return '' when there are more unlabelled problems than any labelled severity.
  2. Returns the most FREQUENT labelled severity, not alphabetically first.
     Kills impl returning the alphabetically first severity regardless of count.
  3. Tie-break: ascending severity string (alphabetically smaller wins).
     Kills impl with descending tie-break or insertion-order.
  4. Returns None on empty input or all-unlabelled input.
     Kills impl raising or returning '' for all-unlabelled.
  5. Return type is str | None.
     Kills impl returning a count or tuple.
"""
from __future__ import annotations

from cohezion.compound.problem_discovery import (
    Problem,
    most_common_severity,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _p(cls: str, idx: int, sev: str = "") -> Problem:
    return Problem(problem_class=cls, finding_id=f"{cls}:{idx}", severity=sev)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_excludes_unlabelled_from_frequency() -> None:
    """Only labelled severities are considered; unlabelled ('') excluded.

    PRIMARY DISCRIMINATOR: kills impl including '' in frequency count.
    5 unlabelled + 3 HIGH + 1 LOW. Most frequent LABELLED = HIGH.
    If '' included, '' would win (5 > 3). Must return 'HIGH'.
    """
    problems = (
        [_p("alpha", i) for i in range(5)]  # unlabelled
        + [_p("beta", i, "HIGH") for i in range(3)]
        + [_p("beta", 10, "LOW")]
    )
    result = most_common_severity(problems)
    assert result == "HIGH", (
        "HIGH is most frequent labelled (3); '' excluded; got " + repr(result)
    )


def test_returns_most_frequent_not_alphabetical() -> None:
    """Returns the most FREQUENT severity, not alphabetically first.

    Kills impl returning alphabetically first regardless of count.
    CRITICAL×1, HIGH×3. HIGH more frequent. 'CRITICAL' < 'HIGH' alphabetically.
    Must return 'HIGH' not 'CRITICAL'.
    """
    problems = [
        _p("alpha", 0, "CRITICAL"),
        _p("alpha", 1, "HIGH"), _p("alpha", 2, "HIGH"), _p("alpha", 3, "HIGH"),
    ]
    result = most_common_severity(problems)
    assert result == "HIGH", (
        "HIGH is most frequent (3); must not return alphabetically first 'CRITICAL'; got " + repr(result)
    )


def test_tiebreak_ascending_severity_string() -> None:
    """Tie-break: ascending severity string (alphabetically earlier wins).

    Kills impl with descending or insertion-order tie-break.
    HIGH×2 and LOW×2. 'HIGH' < 'LOW' → HIGH wins.
    """
    problems = [
        _p("alpha", 0, "LOW"), _p("alpha", 1, "LOW"),
        _p("alpha", 2, "HIGH"), _p("alpha", 3, "HIGH"),
    ]
    result = most_common_severity(problems)
    assert result == "HIGH", (
        "HIGH and LOW tied at 2; 'HIGH' < 'LOW' → HIGH wins; got " + repr(result)
    )


def test_returns_none_on_empty_or_all_unlabelled() -> None:
    """Returns None on empty input or all-unlabelled.

    Kills impl raising or returning '' for all-unlabelled.
    """
    assert most_common_severity([]) is None, "Empty → None"
    all_unlabelled = [_p("alpha", i) for i in range(5)]
    assert most_common_severity(all_unlabelled) is None, "All-unlabelled → None"


def test_return_type_is_str_or_none() -> None:
    """Return type is str (non-empty) or None.

    Kills impl returning a count or tuple.
    """
    result = most_common_severity([_p("alpha", 0, "HIGH")])
    assert isinstance(result, str), "Must return str; got " + repr(type(result))
    assert result != "", "Must return non-empty str; got " + repr(result)
