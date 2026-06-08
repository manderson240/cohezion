"""Item 367: finding_ids_at_most_count() -- finding_ids with count <= n (2026-06-08).

``finding_ids_at_most_count(problems, n) -> frozenset[str]``:
Returns the frozenset of finding_id strings whose total record count is <= n.
n=0 always returns frozenset() (no id can have count <= 0 in a non-empty list).
Complement invariant: finding_ids_above_count(p, n) | finding_ids_at_most_count(p, n)
equals the full set of distinct finding_ids.  Empty -> frozenset().  Pure; no I/O.

Discriminating tests:

  1. PRIMARY DISC.: uses <= n (at most), not < n.
     Kills impl using strict < threshold.
  2. n=0 returns frozenset() not all ids.
     Kills impl returning all ids for n=0.
  3. Complement invariant: above_count | at_most_count == all distinct finding_ids.
     Kills impl with overlap or gap.
  4. Empty input returns frozenset().
     Kills impl raising on empty.
  5. Returns frozenset of strings, not Problem objects.
     Kills impl returning Problem list.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import (
    Problem,
    finding_ids_above_count,
    finding_ids_at_most_count,
)


def _p(cls: str, fid: str) -> Problem:
    return Problem(problem_class=cls, finding_id=fid)


def test_at_most_is_lte_not_lt() -> None:
    """Returns finding_ids with count <= n, not < n.

    PRIMARY DISCRIMINATOR: kills impl using strict < threshold.
    F-001 appears exactly 2 times; n=2 MUST include it (<=), n=1 must NOT.
    """
    problems = [_p("a", "F-001"), _p("b", "F-001"), _p("c", "F-002")]
    result_n2 = finding_ids_at_most_count(problems, 2)
    assert "F-001" in result_n2, "count==2 <= 2: must be included"
    result_n1 = finding_ids_at_most_count(problems, 1)
    assert "F-001" not in result_n1, "count==2 > 1: must NOT be included"
    assert "F-002" in result_n1, "count==1 <= 1: must be included"


def test_n_zero_returns_empty() -> None:
    """n=0 returns frozenset() because no finding_id has count <= 0.

    Kills impl returning all ids for n=0.
    Every finding_id in a non-empty problem list has count >= 1.
    """
    problems = [_p("a", "X-001"), _p("b", "X-002")]
    result = finding_ids_at_most_count(problems, 0)
    assert result == frozenset(), "n=0 -> empty (no count can be <= 0)"


def test_complement_invariant() -> None:
    """above_count(n) | at_most_count(n) == all distinct finding_ids.

    Kills impl with overlap or gap between the two functions.
    """
    problems = [
        _p("a", "F-001"),
        _p("b", "F-001"),
        _p("c", "F-001"),
        _p("a", "F-002"),
        _p("b", "F-002"),
        _p("a", "F-003"),
    ]
    all_fids = frozenset(p.finding_id for p in problems)
    for n in (0, 1, 2, 3, 4):
        above = finding_ids_above_count(problems, n)
        at_most = finding_ids_at_most_count(problems, n)
        union = above | at_most
        assert union == all_fids, f"n={n}: union must equal all fids; got {union}"
        assert above & at_most == frozenset(), f"n={n}: must be disjoint"


def test_empty_returns_frozenset() -> None:
    """Empty input returns frozenset(), not error."""
    assert finding_ids_at_most_count([], 0) == frozenset()
    assert finding_ids_at_most_count([], 5) == frozenset()


def test_returns_strings_not_problem_objects() -> None:
    """Returns frozenset of strings, not Problem objects.

    PRIMARY structure check: kills impl returning list[Problem].
    """
    problems = [_p("a", "CVE-001"), _p("b", "CVE-002")]
    result = finding_ids_at_most_count(problems, 5)
    assert isinstance(result, frozenset), "Must return frozenset"
    assert all(isinstance(fid, str) for fid in result), "Elements must be strings"
    assert "CVE-001" in result and "CVE-002" in result
