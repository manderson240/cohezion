"""Item 366: finding_ids_above_count() -- finding_ids with record count > n (2026-06-08).

``finding_ids_above_count(problems, n) -> frozenset[str]``:
Returns the frozenset of finding_id strings whose total record count exceeds n.
Strictly GREATER than n (not >=).  n=0 returns all distinct finding_ids.
Empty -> frozenset().  Pure; no I/O.

Discriminating tests:

  1. PRIMARY DISC.: returns finding_id STRINGS not Problem objects.
     Kills impl returning Problem list.
  2. Strictly GREATER than n, not >=.
     Kills impl using >= threshold.
  3. n=0 returns ALL distinct finding_ids.
     Kills impl returning empty for n=0.
  4. Empty input returns frozenset().
     Kills impl raising on empty.
  5. Multiple records with same finding_id counted cumulatively.
     Kills impl counting unique finding_ids per class only.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import (
    Problem,
    finding_ids_above_count,
)


def _p(cls: str, fid: str) -> Problem:
    return Problem(problem_class=cls, finding_id=fid)


def test_returns_strings_not_problem_objects() -> None:
    """Returns frozenset of strings, not Problem objects.

    PRIMARY DISCRIMINATOR: kills impl returning list[Problem].
    """
    problems = [_p("a", "CVE-001"), _p("a", "CVE-001"), _p("b", "CVE-001")]
    result = finding_ids_above_count(problems, 1)
    assert isinstance(result, frozenset), "Must return frozenset"
    assert all(isinstance(fid, str) for fid in result), "Elements must be strings"
    assert "CVE-001" in result, "CVE-001 appears 3 times > 1"


def test_strictly_greater_than_not_gte() -> None:
    """Uses strictly GREATER than n, not >=.

    Kills impl using >= threshold.
    Two records with count==2: n=2 must NOT include them; n=1 must include them.
    """
    problems = [_p("a", "F-001"), _p("b", "F-001"), _p("c", "F-002"), _p("d", "F-002")]
    # Both F-001 and F-002 appear exactly 2 times
    result_gte = finding_ids_above_count(problems, 2)
    assert result_gte == frozenset(), "count==n: must NOT be included (strictly >)"
    result_gt = finding_ids_above_count(problems, 1)
    assert result_gt == frozenset({"F-001", "F-002"}), "count > 1: both included"


def test_n_zero_returns_all_distinct_finding_ids() -> None:
    """n=0 returns ALL distinct finding_ids.

    Kills impl returning empty for n=0.
    Every record has count >= 1 > 0.
    """
    problems = [_p("a", "X-001"), _p("b", "X-002"), _p("a", "X-001")]
    result = finding_ids_above_count(problems, 0)
    assert result == frozenset({"X-001", "X-002"}), "n=0 -> all distinct fids"


def test_empty_returns_frozenset() -> None:
    """Empty input returns frozenset(), not error.

    Kills impl raising on empty.
    """
    result = finding_ids_above_count([], 0)
    assert result == frozenset()
    result2 = finding_ids_above_count([], 5)
    assert result2 == frozenset()


def test_cumulative_count_across_classes() -> None:
    """Records from different classes count toward the same finding_id.

    Kills impl counting per-class rather than globally.
    F-001 in class a + class b + class c = count 3 > 2.
    """
    problems = [
        _p("sec", "F-001"),
        _p("perf", "F-001"),
        _p("style", "F-001"),
        _p("sec", "F-002"),
    ]
    result = finding_ids_above_count(problems, 2)
    assert "F-001" in result, "F-001 count=3 > 2"
    assert "F-002" not in result, "F-002 count=1, not > 2"
