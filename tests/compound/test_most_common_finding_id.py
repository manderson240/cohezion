"""Item 326: most_common_finding_id() — finding_id with highest total record count (2026-06-08).

``most_common_finding_id(problems) -> str | None``:
Returns the finding_id with the most total Problem records (across all classes).
Ties broken by alphabetically ascending finding_id.  Empty -> None.  Pure; no I/O.

Discriminating tests — each kills a plausible wrong implementation:

  1. PRIMARY DISC.: most FREQUENT finding_id wins, not first-encountered.
     Kills impl returning insertion order (first seen).
  2. Tie-break selects alphabetically ascending (smallest) finding_id.
     Kills impl with reverse or arbitrary tie-break.
  3. finding_id count spans classes (fid in alpha+beta = 2 records total).
     Kills impl counting per-class occurrences separately.
  4. Empty -> None (not '' or KeyError).
     Kills impl raising on empty input.
  5. Single problem -> that problem's finding_id.
     Kills impl with off-by-one returning None for size=1.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import (
    Problem,
    most_common_finding_id,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _ps(cls: str, fid: str) -> Problem:
    return Problem(problem_class=cls, finding_id=fid)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_most_frequent_fid_wins_not_first_encountered() -> None:
    """Highest total record count wins over insertion order.

    PRIMARY DISCRIMINATOR: kills impl returning first-seen finding_id.
    fid0: 1 record (appears first). fid1: 3 records. Most frequent = fid1.
    """
    problems = [
        _ps("alpha", "fid0"),  # fid0 appears first, but only 1 time
        _ps("alpha", "fid1"),
        _ps("alpha", "fid1"),
        _ps("alpha", "fid1"),  # fid1 has 3 records
    ]
    result = most_common_finding_id(problems)
    assert result == "fid1", "fid1 (3 records) beats fid0 (1 record); got " + repr(result)


def test_tie_break_selects_alphabetically_first() -> None:
    """Tie broken by ascending alphabetical order (smallest fid wins).

    Kills impl with reverse (last alphabetically) or arbitrary tie-break.
    fid_a: 2 records. fid_z: 2 records. Tie -> 'fid_a' wins (a < z).
    """
    problems = [
        _ps("alpha", "fid_z"),
        _ps("alpha", "fid_z"),
        _ps("alpha", "fid_a"),
        _ps("alpha", "fid_a"),
    ]
    result = most_common_finding_id(problems)
    assert result == "fid_a", (
        "Tie: fid_a and fid_z both 2 records; fid_a < fid_z -> fid_a wins; got " + repr(result)
    )


def test_count_spans_classes() -> None:
    """finding_id count is global across all classes, not per-class.

    Kills impl counting per-class separately.
    fid0: alpha=1 + beta=1 + gamma=1 = 3 total. fid1: alpha=2. fid0 wins.
    """
    problems = [
        _ps("alpha", "fid1"),
        _ps("alpha", "fid1"),  # fid1: 2 records
        _ps("alpha", "fid0"),
        _ps("beta", "fid0"),
        _ps("gamma", "fid0"),  # fid0: 3 records across 3 classes
    ]
    result = most_common_finding_id(problems)
    assert result == "fid0", (
        "fid0 (3 records across 3 classes) beats fid1 (2 records); got " + repr(result)
    )


def test_empty_input_returns_none() -> None:
    """Empty input -> None, not '' or exception.

    Kills impl raising on empty input.
    """
    result = most_common_finding_id([])
    assert result is None, "empty -> None; got " + repr(result)


def test_single_problem_returns_its_finding_id() -> None:
    """A single problem -> its finding_id (minimum case).

    Kills impl returning None for size=1.
    """
    problems = [_ps("alpha", "fid99")]
    result = most_common_finding_id(problems)
    assert result == "fid99", "Single problem -> 'fid99'; got " + repr(result)
