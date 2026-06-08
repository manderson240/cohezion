"""Item 210: count_unique_finding_ids() — distinct finding_id cardinality (2026-06-08).

``count_unique_finding_ids(problems: list[Problem])``
-> ``int``:
Returns ``len({p.finding_id for p in problems})``.
Empty -> 0.  All distinct -> len(problems).  All identical -> 1.
Pure; no I/O.

Enables ``n = count_unique_finding_ids(findings)`` as a quick dedup health
check without building an external set::

    n = count_unique_finding_ids(findings)
    if n < len(findings):
        warn("duplicate finding ids present")

Discriminating tests -- each kills a plausible wrong implementation:

  1. PRIMARY DISC.: returns distinct count, not len(problems).
     Kills an impl that returns len(problems) without deduplication.
  2. All identical ids -> 1.
     Kills an impl that returns 0 or raises on pure-duplicate input.
  3. Empty list -> 0 (not raises, not None).
     Kills an impl that raises IndexError on empty input.
  4. Return type is int.
     Kills an impl that returns a set or a float.
  5. Mixed distinct+duplicate -> exact distinct count.
     Kills an impl that over-counts or under-counts on mixed input.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import (
    Problem,
    count_unique_finding_ids,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _p(cls: str, idx: int = 0) -> Problem:
    return Problem(problem_class=cls, finding_id=f"{cls}:{idx}")


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_distinct_count_not_total_count() -> None:
    """Returns distinct count, not len(problems) when duplicates exist.

    PRIMARY DISCRIMINATOR: kills an impl that returns len(problems) without
    deduplication.  2 problems share the same finding_id -> count=1, not 2.
    """
    p = Problem(problem_class="alpha", finding_id="shared:1")
    problems = [p, p]  # same object; same finding_id twice

    result = count_unique_finding_ids(problems)

    assert result == 1, "two entries with the same finding_id must count as 1; got " + repr(result)


def test_all_identical_ids_returns_one() -> None:
    """When every finding_id is the same string -> 1.

    Kills an impl that returns 0 or raises on pure-duplicate input.
    """
    same_id = Problem(problem_class="beta", finding_id="beta:0")
    problems = [same_id] * 5

    result = count_unique_finding_ids(problems)

    assert result == 1, "5 copies of the same id must yield 1; got " + repr(result)


def test_empty_list_returns_zero() -> None:
    """Empty list -> 0 (not raises, not None).

    Kills an impl that raises IndexError on empty input.
    """
    result = count_unique_finding_ids([])

    assert result == 0, "empty input must return 0; got " + repr(result)
    assert isinstance(result, int), "return type must be int; got " + repr(type(result))


def test_return_type_is_int() -> None:
    """Return value is int, not set or float.

    Kills an impl that returns the set itself or a float.
    """
    problems = [_p("alpha", i) for i in range(3)]

    result = count_unique_finding_ids(problems)

    assert isinstance(result, int), "must return int; got " + repr(type(result))
    assert result == 3


def test_mixed_distinct_and_duplicate() -> None:
    """Mixed input with some duplicates -> exact distinct count.

    Kills an impl that over- or under-counts on mixed input.
    3 distinct ids among 5 total problems -> 3.
    """
    problems = [
        Problem(problem_class="a", finding_id="id:1"),
        Problem(problem_class="b", finding_id="id:2"),
        Problem(problem_class="a", finding_id="id:1"),  # duplicate of first
        Problem(problem_class="c", finding_id="id:3"),
        Problem(problem_class="b", finding_id="id:2"),  # duplicate of second
    ]

    result = count_unique_finding_ids(problems)

    assert result == 3, "5 problems with 3 distinct ids must yield 3; got " + repr(result)
