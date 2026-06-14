"""Item 182: sorted_finding_ids() — deterministic snapshot accessor (2026-06-08).

``sorted_finding_ids(problems: list[Problem])`` → ``list[str]``:
Returns a sorted list of all ``finding_id`` values in *problems*.
Empty input → ``[]``.  Pure; no I/O.

Useful for snapshot assertions::

    assert sorted_finding_ids(findings) == expected_ids

Discriminating tests — each kills a plausible wrong implementation:

  1. PRIMARY DISC.: mixed list → IDs sorted lexicographically.
     Kills an impl that returns insertion-order (or reverses the sort).
  2. Empty list → ``[]`` (no raises).
     Kills an impl that raises on empty input.
  3. Single-element list → that one ID in a list.
     Kills an impl that requires ≥2 elements to return a non-empty result.
  4. Already-sorted input → same order preserved.
     Kills an impl that accidentally reverses the sort.
  5. Duplicates preserved (not deduplicated).
     Kills an impl that deduplicates via set() before sorting.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import (
    Problem,
    sorted_finding_ids,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _p(cls: str, fid: str) -> Problem:
    return Problem(problem_class=cls, finding_id=fid)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_mixed_list_sorted_lexicographically() -> None:
    """Mixed list → IDs sorted lexicographically (ascending).

    PRIMARY DISCRIMINATOR: kills an impl that returns insertion order
    (which would give ["c_id", "a_id", "b_id"] instead of sorted order).
    """
    problems = [
        _p("cls", "c_id"),
        _p("cls", "a_id"),
        _p("cls", "b_id"),
    ]

    result = sorted_finding_ids(problems)

    assert result == ["a_id", "b_id", "c_id"], (
        f"IDs must be sorted lexicographically; got {result!r}"
    )


def test_empty_list_returns_empty() -> None:
    """Empty list → [] (no raises).

    Kills an impl that raises IndexError or returns None on empty input.
    """
    result = sorted_finding_ids([])

    assert result == [], f"Empty input must return []; got {result!r}"


def test_single_element_returns_single_id() -> None:
    """Single-element list → [that finding_id].

    Kills an impl that requires ≥2 elements to produce a non-empty result.
    """
    problems = [_p("complexity_outlier", "complexity_outlier:src/foo.py:10")]

    result = sorted_finding_ids(problems)

    assert result == ["complexity_outlier:src/foo.py:10"], (
        f"Single element must return [that id]; got {result!r}"
    )


def test_already_sorted_unchanged() -> None:
    """Already-sorted input → same order returned.

    Kills an impl that accidentally reverses the sort (descending instead of
    ascending lexicographic order).
    """
    problems = [
        _p("cls", "alpha:1"),
        _p("cls", "beta:2"),
        _p("cls", "gamma:3"),
    ]

    result = sorted_finding_ids(problems)

    assert result == ["alpha:1", "beta:2", "gamma:3"], (
        f"Already-sorted input must preserve order; got {result!r}"
    )


def test_duplicates_preserved() -> None:
    """Duplicate finding_ids kept (not deduplicated via set()).

    Kills an impl that calls set() before sorting, which would silently
    drop duplicates and produce a shorter list.
    """
    duplicate_id = "complexity_outlier:src/foo.py:10"
    problems = [_p("cls", duplicate_id), _p("cls", duplicate_id)]

    result = sorted_finding_ids(problems)

    assert len(result) == 2, f"Duplicates must be preserved; got {result!r}"
    assert result == [duplicate_id, duplicate_id], (
        f"Both duplicate IDs must appear in result; got {result!r}"
    )
