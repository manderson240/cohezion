"""Item 264: duplicate_finding_ids() — finding_ids that appear more than once (2026-06-08).

``duplicate_finding_ids(problems: list[Problem]) -> frozenset[str]``:
Returns the frozenset of ``finding_id`` values that appear in >=2 problems.
Empty input or all-unique ids -> frozenset().  Pure; no I/O.

Discriminating tests -- each kills a plausible wrong implementation:

  1. PRIMARY DISC.: returns only ids that appear >=2 times, not all ids.
     Kills impl returning unique_finding_ids() (all ids, even singletons).
  2. Single-occurrence ids are excluded.
     Kills impl that includes ids appearing exactly once.
  3. frozenset() when all ids are unique.
     Kills impl that raises or returns non-empty on all-unique input.
  4. Empty input -> frozenset().
     Kills impl that raises on empty input.
  5. Return type is frozenset[str], not list or set or int.
     Kills impl returning a count or list.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import (
    Problem,
    duplicate_finding_ids,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _p(cls: str, fid: str) -> Problem:
    return Problem(problem_class=cls, finding_id=fid)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_returns_only_duplicated_ids() -> None:
    """Returns only ids appearing >=2 times, not all ids.

    PRIMARY DISCRIMINATOR: kills impl returning unique_finding_ids().
    'x:1' appears twice -> in result. 'y:1' appears once -> excluded.
    """
    problems = [
        _p("alpha", "x:1"),
        _p("beta", "x:1"),  # duplicate
        _p("gamma", "y:1"),  # unique
    ]
    result = duplicate_finding_ids(problems)
    assert result == frozenset({"x:1"}), "Only 'x:1' is duplicated; got " + repr(result)
    assert "y:1" not in result, "Singleton 'y:1' must not appear"


def test_singleton_ids_excluded() -> None:
    """Ids appearing exactly once are not in the result.

    Kills impl that includes singletons.
    Two ids: 'a:0' appears 3x (duplicate), 'b:0' appears 1x (singleton).
    """
    problems = [
        _p("alpha", "a:0"),
        _p("alpha", "a:0"),
        _p("alpha", "a:0"),
        _p("beta", "b:0"),
    ]
    result = duplicate_finding_ids(problems)
    assert "a:0" in result, "'a:0' appears 3x -> duplicate"
    assert "b:0" not in result, "'b:0' appears once -> excluded"


def test_empty_frozenset_when_all_unique() -> None:
    """Returns frozenset() when all ids are unique.

    Kills impl that returns non-empty on all-unique input.
    """
    problems = [_p("alpha", f"id:{i}") for i in range(5)]
    result = duplicate_finding_ids(problems)
    assert result == frozenset(), "All unique ids -> frozenset(); got " + repr(result)


def test_empty_input_returns_empty_frozenset() -> None:
    """Empty input -> frozenset().

    Kills impl that raises on empty input.
    """
    result = duplicate_finding_ids([])
    assert result == frozenset(), "Empty input -> frozenset(); got " + repr(result)


def test_return_type_is_frozenset() -> None:
    """Return type is frozenset, not set, list, or int.

    Kills impl returning a plain set, list, or duplicate count.
    """
    problems = [_p("alpha", "dup"), _p("beta", "dup")]
    result = duplicate_finding_ids(problems)
    assert isinstance(result, frozenset), "Must return frozenset; got " + repr(type(result))
