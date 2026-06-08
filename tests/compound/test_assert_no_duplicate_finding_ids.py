"""Item 180: assert_no_duplicate_finding_ids() — structural integrity guard (2026-06-08).

``assert_no_duplicate_finding_ids(problems: list[Problem]) -> None``:
Raises ``AssertionError`` listing all duplicate ``finding_id`` values if any
appear more than once.  Empty list → no-op.  All-unique list → no-op.
Pure; no I/O.

Prevents silent data corruption when two templates emit overlapping IDs and
downstream diff/group logic silently deduplicates.

Discriminating tests — each kills a plausible wrong implementation:

  1. PRIMARY DISC.: one duplicate ID → AssertionError naming the duplicate.
     Kills an impl that always passes silently (no-op impl).
  2. Multiple distinct duplicates → AssertionError listing ALL of them.
     Kills an impl that reports only the first violation.
  3. All-unique list → no-op (no raises).
     Kills an impl that always raises (or raises on >1 element).
  4. Empty list → no-op (no raises).
     Kills an impl that raises on empty input.
  5. Single-element list → no-op (no raises).
     Kills an impl that requires ≥2 elements before it can pass silently.
"""

from __future__ import annotations

import pytest

from cohezion.compound.problem_discovery import (
    Problem,
    assert_no_duplicate_finding_ids,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _p(cls: str, idx: int = 0) -> Problem:
    return Problem(problem_class=cls, finding_id=f"{cls}:{idx}")


def _pf(finding_id: str) -> Problem:
    """Create a Problem with an explicit finding_id."""
    return Problem(problem_class="any_class", finding_id=finding_id)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_single_duplicate_raises_naming_it() -> None:
    """One duplicate finding_id → AssertionError that mentions the duplicate.

    PRIMARY DISCRIMINATOR: kills a no-op impl (one that always passes
    silently regardless of duplicates).
    """
    duplicate_id = "complexity_outlier:src/foo.py:10"
    problems = [_pf(duplicate_id), _p("other_class"), _pf(duplicate_id)]

    with pytest.raises(AssertionError) as exc_info:
        assert_no_duplicate_finding_ids(problems)

    assert duplicate_id in str(exc_info.value), (
        f"AssertionError must name the duplicate finding_id; got {exc_info.value!r}"
    )


def test_multiple_duplicates_all_listed() -> None:
    """Two distinct duplicate IDs → AssertionError listing BOTH.

    Kills an impl that reports only the first violation and returns/raises
    before checking remaining IDs (fail-fast rather than fail-all).
    """
    dup_a = "nesting_outlier:a.py:1"
    dup_b = "long_function:b.py:5"
    problems = [_pf(dup_a), _pf(dup_b), _pf(dup_a), _pf(dup_b)]

    with pytest.raises(AssertionError) as exc_info:
        assert_no_duplicate_finding_ids(problems)

    msg = str(exc_info.value)
    assert dup_a in msg, f"Both duplicate IDs must appear in error; '{dup_a}' missing from {msg!r}"
    assert dup_b in msg, f"Both duplicate IDs must appear in error; '{dup_b}' missing from {msg!r}"


def test_all_unique_no_raises() -> None:
    """All-unique finding_ids → no raises (valid input).

    Kills an impl that always raises or raises when there are multiple elements.
    """
    problems = [_p("complexity_outlier"), _p("nesting_outlier"), _p("long_function")]

    # Must not raise
    assert_no_duplicate_finding_ids(problems)


def test_empty_list_no_raises() -> None:
    """Empty list → no-op (no raises).

    Kills an impl that raises on empty input (e.g. IndexError).
    """
    assert_no_duplicate_finding_ids([])


def test_single_element_no_raises() -> None:
    """Single-element list → no-op (no raises).

    Kills an impl that requires ≥2 elements before it can pass silently.
    """
    assert_no_duplicate_finding_ids([_p("complexity_outlier")])
