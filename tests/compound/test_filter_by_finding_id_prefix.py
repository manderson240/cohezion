"""Item 218: filter_by_finding_id_prefix() — prefix-filtered list (2026-06-08).

``filter_by_finding_id_prefix(problems: list[Problem], id_prefixes: set[str])``
-> ``list[Problem]``:
Returns Problem objects whose ``finding_id`` starts with ANY prefix in
*id_prefixes*, in input order.  Empty *id_prefixes* -> ``[]``.
Empty *problems* -> ``[]``.  Pure; no I/O.

The list face of ``count_problems_added_since`` — same filter logic but returns
the matching Problem objects for downstream inspection::

    recent = filter_by_finding_id_prefix(findings, {"scan-2026-06-08:"})
    for p in recent:
        inspect(p)

Discriminating tests -- each kills a plausible wrong implementation:

  1. PRIMARY DISC.: only Problems whose finding_id matches a prefix are returned.
     Kills an impl that returns all problems regardless of the prefix filter.
  2. Input order preserved in returned list.
     Kills an impl that sorts by finding_id or class.
  3. Empty id_prefixes -> [] (not all problems).
     Kills an impl that treats empty prefix set as "match all".
  4. Empty problems -> [].
     Kills an impl that raises or returns None on empty input.
  5. Return type is list[Problem].
     Kills an impl that returns a set or the finding_ids only.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import (
    Problem,
    filter_by_finding_id_prefix,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _p(cls: str, fid: str) -> Problem:
    return Problem(problem_class=cls, finding_id=fid)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_only_prefix_matching_problems_returned() -> None:
    """Only Problems with matching finding_id prefix are returned.

    PRIMARY DISCRIMINATOR: kills an impl that returns all problems.
    """
    p1 = _p("alpha", "scan-A:001")
    p2 = _p("alpha", "scan-A:002")
    p3 = _p("beta", "scan-B:001")
    problems = [p1, p2, p3]

    result = filter_by_finding_id_prefix(problems, {"scan-A:"})

    assert result == [p1, p2], "Only scan-A: problems must be returned; got " + repr(result)
    assert p3 not in result


def test_input_order_preserved() -> None:
    """Matching Problems are returned in input order.

    Kills an impl that sorts by finding_id or class.
    """
    p1 = _p("beta", "scan-X:002")
    p2 = _p("alpha", "scan-X:001")  # alpha comes after beta in input
    problems = [p1, p2]

    result = filter_by_finding_id_prefix(problems, {"scan-X:"})

    assert result == [p1, p2], "Input order must be preserved; got " + repr(result)


def test_empty_prefixes_returns_empty_list() -> None:
    """Empty id_prefixes -> [], not all problems.

    Kills an impl that treats empty prefix as match-all.
    """
    problems = [_p("alpha", "scan-A:001"), _p("beta", "scan-B:002")]
    result = filter_by_finding_id_prefix(problems, set())
    assert result == [], "Empty prefixes must return []; got " + repr(result)


def test_empty_problems_returns_empty_list() -> None:
    """Empty problems list -> [].

    Kills an impl that raises or returns None on empty input.
    """
    result = filter_by_finding_id_prefix([], {"scan-A:"})
    assert result == [], "Empty problems must return []; got " + repr(result)


def test_return_type_is_list_of_problem() -> None:
    """Return value is list[Problem], not a set or list of finding_ids.

    Kills an impl that returns finding_id strings instead of Problem objects.
    """
    p = _p("alpha", "scan-A:001")
    result = filter_by_finding_id_prefix([p], {"scan-A:"})
    assert isinstance(result, list), "Return type must be list; got " + repr(type(result))
    assert len(result) == 1
    assert isinstance(result[0], Problem), "Elements must be Problem; got " + repr(type(result[0]))
