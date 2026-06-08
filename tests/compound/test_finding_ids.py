"""Item 189: finding_ids() — insertion-order ID extraction accessor (2026-06-08).

``finding_ids(problems: list[Problem])`` → ``list[str]``:
Returns the ``finding_id`` values of all findings in *problems* in insertion
order.  Empty list → ``[]``.  Pure; no I/O.

Enables set construction without inline comprehensions::

    exclude_problems(all_findings, frozenset(finding_ids(actioned)))

Discriminating tests — each kills a plausible wrong implementation:

  1. PRIMARY DISC.: non-alphabetical insertion order → IDs returned in
     INSERTION order (not sorted).
     Kills an impl that delegates to ``sorted_finding_ids()`` or sorts.
  2. Empty list → ``[]`` (no raises).
     Kills an impl that raises on empty input.
  3. Single element → list of that one ID.
     Kills an impl that returns ``[]`` for single-element input.
  4. Result contains strings, not Problem instances.
     Kills an impl that returns the Problem objects instead of their IDs.
  5. Length matches input length (no deduplication).
     Kills an impl that deduplicates or omits elements.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import (
    Problem,
    finding_ids,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _p(cls: str, idx: int = 0) -> Problem:
    return Problem(problem_class=cls, finding_id=f"{cls}:{idx}")


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_insertion_order_preserved_not_sorted() -> None:
    """Non-alphabetical insertion order → IDs returned in input order.

    PRIMARY DISCRIMINATOR: kills an impl that sorts the result (e.g. by
    delegating to sorted_finding_ids) instead of preserving insertion order.
    'z→a→m' input must produce 'z→a→m' output, NOT 'a→m→z'.
    """
    problems = [
        Problem(problem_class="cls", finding_id="z_id"),
        Problem(problem_class="cls", finding_id="a_id"),
        Problem(problem_class="cls", finding_id="m_id"),
    ]

    result = finding_ids(problems)

    assert result == ["z_id", "a_id", "m_id"], f"Insertion order must be preserved; got {result!r}"


def test_empty_list_returns_empty() -> None:
    """Empty list → [] (no raises).

    Kills an impl that raises IndexError or returns None on empty input.
    """
    result = finding_ids([])

    assert result == [], f"Empty input must return []; got {result!r}"


def test_single_element_returns_one_id() -> None:
    """Single-element list → [that finding_id].

    Kills an impl that returns [] for any input with fewer than 2 elements.
    """
    problems = [_p("complexity_outlier", 7)]

    result = finding_ids(problems)

    assert result == ["complexity_outlier:7"], (
        f"Single element must return [its id]; got {result!r}"
    )


def test_result_contains_strings_not_problems() -> None:
    """Each element of the result is a str, not a Problem.

    Kills an impl that returns the Problem objects instead of extracting
    their finding_id attribute.
    """
    problems = [_p("nesting_outlier")]

    result = finding_ids(problems)

    assert isinstance(result[0], str), (
        f"Elements must be str; got {type(result[0])} for {result[0]!r}"
    )
    assert result[0] == "nesting_outlier:0", f"ID string must match finding_id; got {result[0]!r}"


def test_length_matches_input_no_dedup() -> None:
    """Duplicate IDs are preserved (no deduplication).

    Kills an impl that deduplicates via set conversion, producing a shorter
    result than the input.
    """
    dup = _p("complexity_outlier", 0)
    problems = [dup, dup, _p("nesting_outlier")]

    result = finding_ids(problems)

    assert len(result) == 3, (
        f"Length must equal input length (no dedup); got {len(result)}: {result!r}"
    )
