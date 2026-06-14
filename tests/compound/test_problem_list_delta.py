"""Item 240: problem_list_delta() — added/resolved diff between two scans (2026-06-08).

``problem_list_delta(baseline: list[Problem], current: list[Problem])``
-> ``tuple[list[Problem], list[Problem]]``:
Returns ``(added, resolved)`` where:
  - ``added``    = problems in ``current`` not present in ``baseline`` (by finding_id)
  - ``resolved`` = problems in ``baseline`` not present in ``current`` (by finding_id)
Both lists preserve their respective input orders.
Identical inputs → both empty.  Empty inputs → both empty.  Pure; no I/O.

NOTE: distinct from ``scan_delta(before: dict, after: dict)`` (item 225) which
diffs two ``summarize_scan()`` summary dicts — this function operates on raw
Problem lists.

Discriminating tests -- each kills a plausible wrong implementation:

  1. PRIMARY DISC.: added = problems new in current (not in baseline).
     Kills an impl that swaps added/resolved.
  2. resolved = baseline problems absent from current (not retained).
     Kills an impl returning the same list for both slots.
  3. Both lists empty when inputs are identical (no change).
     Kills an impl returning non-empty when inputs match.
  4. Return type is a 2-tuple of lists (not a dict).
     Kills an impl returning a dict like scan_delta().
  5. Order preserved: added in current-input order; resolved in baseline order.
     Kills an impl that sorts either list.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import (
    Problem,
    problem_list_delta,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _p(cls: str, idx: int = 0) -> Problem:
    return Problem(problem_class=cls, finding_id=f"{cls}:{idx}")


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_added_contains_problems_new_in_current() -> None:
    """added = problems in current not in baseline.

    PRIMARY DISCRIMINATOR: kills an impl that swaps added/resolved (i.e.
    puts resolved problems in the 'added' slot).
    baseline has p0, p1. current has p1, p2. added = [p2]; resolved = [p0].
    """
    p0 = _p("alpha", 0)
    p1 = _p("alpha", 1)
    p2 = _p("alpha", 2)

    added, _resolved = problem_list_delta([p0, p1], [p1, p2])

    assert len(added) == 1, "added must have 1 new problem (p2); got " + repr(added)
    assert added[0].finding_id == p2.finding_id, "added must contain p2; got " + repr(
        added[0].finding_id
    )


def test_resolved_contains_baseline_problems_absent_from_current() -> None:
    """resolved = baseline problems not in current.

    Kills an impl that puts the same list in both slots.
    """
    p0 = _p("alpha", 0)
    p1 = _p("alpha", 1)
    p2 = _p("alpha", 2)

    _added, resolved = problem_list_delta([p0, p1], [p1, p2])

    assert len(resolved) == 1, "resolved must have 1 problem (p0); got " + repr(resolved)
    assert resolved[0].finding_id == p0.finding_id, "resolved must contain p0; got " + repr(
        resolved[0].finding_id
    )


def test_identical_inputs_give_empty_both() -> None:
    """Identical baseline and current → ([], []).

    Kills an impl that returns non-empty on no change.
    """
    problems = [_p("alpha", i) for i in range(3)]
    added, resolved = problem_list_delta(problems, problems)

    assert added == [], "No change → added must be []; got " + repr(added)
    assert resolved == [], "No change → resolved must be []; got " + repr(resolved)


def test_return_type_is_two_tuple_of_lists() -> None:
    """Return value is a 2-tuple of lists, not a dict.

    Kills an impl returning a dict like scan_delta() (item 225).
    """
    result = problem_list_delta([_p("alpha")], [_p("beta")])

    assert isinstance(result, tuple), "Must return a tuple; got " + repr(type(result))
    assert len(result) == 2, "Must return exactly 2 elements; got " + repr(len(result))
    added, resolved = result
    assert isinstance(added, list), "added must be a list; got " + repr(type(added))
    assert isinstance(resolved, list), "resolved must be a list; got " + repr(type(resolved))


def test_order_preserved_in_both_lists() -> None:
    """added is in current-input order; resolved is in baseline order.

    Kills an impl that sorts either list.
    baseline: p_z, p_a (in that order). current: p_m, p_a.
    added = [p_m] (current order); resolved = [p_z] (baseline order).
    """
    p_z = Problem(problem_class="alpha", finding_id="alpha:z")
    p_a = Problem(problem_class="alpha", finding_id="alpha:a")
    p_m = Problem(problem_class="alpha", finding_id="alpha:m")

    added, resolved = problem_list_delta([p_z, p_a], [p_m, p_a])

    assert len(added) == 1 and added[0].finding_id == "alpha:m", (
        "added must contain p_m in current order; got " + repr(added)
    )
    assert len(resolved) == 1 and resolved[0].finding_id == "alpha:z", (
        "resolved must contain p_z in baseline order; got " + repr(resolved)
    )
