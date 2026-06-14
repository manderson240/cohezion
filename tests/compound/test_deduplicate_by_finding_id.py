"""Item 212: deduplicate_by_finding_id() — dedup keeping first occurrence (2026-06-08).

``deduplicate_by_finding_id(problems: list[Problem])``
-> ``list[Problem]``:
Returns a new list with duplicates removed, keeping the FIRST occurrence of
each ``finding_id`` in input order.  Empty -> ``[]``.  All-distinct -> same
length.  Pure; no I/O.

Corrective face of :func:`has_duplicate_finding_ids` (item 211)::

    clean = deduplicate_by_finding_id(findings)
    assert not has_duplicate_finding_ids(clean)

Discriminating tests -- each kills a plausible wrong implementation:

  1. PRIMARY DISC.: keeps FIRST occurrence, not LAST.
     Kills an impl that builds a dict {finding_id: problem} (keeps last).
  2. Return is list[Problem], not list[str].
     Kills an impl that extracts finding_id strings instead of Problems.
  3. Empty list -> [] (not raises).
     Kills an impl that raises on empty input.
  4. Already-distinct list -> same length, same order.
     Kills an impl that incorrectly drops distinct entries.
  5. Preserves insertion order among kept items.
     Kills an impl that sorts the result.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import (
    Problem,
    deduplicate_by_finding_id,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _p(cls: str, idx: int = 0) -> Problem:
    return Problem(problem_class=cls, finding_id=f"{cls}:{idx}")


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_keeps_first_occurrence_not_last() -> None:
    """Keeps the FIRST occurrence of each finding_id, not the last.

    PRIMARY DISCRIMINATOR: kills an impl that builds
    ``{p.finding_id: p for p in problems}`` (which keeps the last occurrence).
    The first 'alpha' has problem_class='alpha'; the second (last) has
    problem_class='beta' but the same finding_id. First-kept must be 'alpha'.
    """
    first = Problem(problem_class="alpha", finding_id="shared:1")
    last = Problem(problem_class="beta", finding_id="shared:1")  # same id, different class
    problems = [first, last]

    result = deduplicate_by_finding_id(problems)

    assert len(result) == 1, "one unique id -> one element; got " + repr(result)
    assert result[0].problem_class == "alpha", (
        "first occurrence (class=alpha) must be kept; got class=" + repr(result[0].problem_class)
    )


def test_return_is_list_of_problem_objects() -> None:
    """Return type is list[Problem], not list[str].

    Kills an impl that returns finding_id strings instead of Problems.
    """
    problems = [_p("alpha", 0), _p("alpha", 0)]

    result = deduplicate_by_finding_id(problems)

    assert len(result) == 1
    assert isinstance(result[0], Problem), "elements must be Problem objects; got " + repr(
        type(result[0])
    )


def test_empty_list_returns_empty() -> None:
    """Empty list -> [] (not raises).

    Kills an impl that raises IndexError on empty input.
    """
    result = deduplicate_by_finding_id([])

    assert result == [], "empty input must return []; got " + repr(result)


def test_already_distinct_same_length_and_order() -> None:
    """Already-distinct list -> same length, same order.

    Kills an impl that incorrectly drops entries or reorders them.
    """
    problems = [_p("alpha", 0), _p("beta", 0), _p("gamma", 0)]

    result = deduplicate_by_finding_id(problems)

    assert len(result) == len(problems), "all-distinct must preserve length; got " + repr(
        len(result)
    )
    assert [p.finding_id for p in result] == [p.finding_id for p in problems], (
        "order must be preserved; got " + repr([p.finding_id for p in result])
    )


def test_preserves_insertion_order_among_kept() -> None:
    """Kept items appear in the same relative order as in the original list.

    Kills an impl that sorts the kept items alphabetically or by hash.
    Order in input: zeta(0), alpha(0), beta(0), alpha(0 duplicate), zeta(1).
    Expected kept order: zeta(0), alpha(0), beta(0) — first occurrences only.
    """
    problems = [
        Problem(problem_class="c", finding_id="zeta:0"),
        Problem(problem_class="a", finding_id="alpha:0"),
        Problem(problem_class="b", finding_id="beta:0"),
        Problem(problem_class="a2", finding_id="alpha:0"),  # dup of second
        Problem(problem_class="c2", finding_id="zeta:1"),  # new id — kept
    ]

    result = deduplicate_by_finding_id(problems)

    kept_ids = [p.finding_id for p in result]
    assert kept_ids == ["zeta:0", "alpha:0", "beta:0", "zeta:1"], (
        "must keep in insertion order; got " + repr(kept_ids)
    )
