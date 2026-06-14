"""Item 373: class_count_above_threshold() -- class names with count > n (2026-06-08).

``class_count_above_threshold(problems, n) -> frozenset[str]``:
Returns the frozenset of class names whose total problem record count exceeds n.
Strictly GREATER than n.  n=0 returns all distinct classes.
Empty -> frozenset().  Pure; no I/O.  Sister to finding_ids_above_count.

Discriminating tests:

  1. PRIMARY DISC.: operates on CLASS names not finding_ids.
     Kills impl re-using finding_ids_above_count.
  2. Strictly > n, not >= (kills impl using >= threshold).
  3. n=0 returns ALL distinct classes (kills impl returning empty for n=0).
  4. Empty returns frozenset() (kills impl raising).
  5. Returns frozenset of strings, not Problem objects.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import (
    Problem,
    class_count_above_threshold,
)


def _p(cls: str, fid: str) -> Problem:
    return Problem(problem_class=cls, finding_id=fid)


def test_operates_on_class_not_finding_id() -> None:
    """Returns class names, not finding_ids.

    PRIMARY DISCRIMINATOR: kills impl re-using finding_ids_above_count.
    Same finding_id across 3 classes; class 'sec' appears 3x, 'perf' 1x.
    """
    problems = [
        _p("sec", "CVE-001"),
        _p("sec", "CVE-002"),
        _p("sec", "CVE-003"),
        _p("perf", "PERF-001"),
    ]
    result = class_count_above_threshold(problems, 2)
    assert "sec" in result, "sec count=3 > 2; got " + repr(result)
    assert "perf" not in result, "perf count=1, not > 2; got " + repr(result)
    assert all(isinstance(v, str) for v in result), "Elements must be strings"


def test_strictly_greater_than_not_gte() -> None:
    """Uses strictly > n, not >= n.

    Kills impl using >= threshold.
    alpha×2: n=2 must NOT include it; n=1 must include it.
    """
    problems = [_p("alpha", "f:0"), _p("alpha", "f:1"), _p("beta", "f:2")]
    result_n2 = class_count_above_threshold(problems, 2)
    assert "alpha" not in result_n2, "count==2 not > 2: must be excluded"
    result_n1 = class_count_above_threshold(problems, 1)
    assert "alpha" in result_n1, "count==2 > 1: must be included"


def test_n_zero_returns_all_distinct_classes() -> None:
    """n=0 returns ALL distinct classes (every class has count >= 1 > 0).

    Kills impl returning empty for n=0.
    """
    problems = [_p("a", "f:0"), _p("b", "f:1"), _p("a", "f:2")]
    result = class_count_above_threshold(problems, 0)
    assert result == frozenset({"a", "b"}), "n=0 -> all distinct classes"


def test_empty_returns_frozenset() -> None:
    """Empty input returns frozenset(), not error."""
    assert class_count_above_threshold([], 0) == frozenset()
    assert class_count_above_threshold([], 5) == frozenset()


def test_returns_frozenset_of_strings() -> None:
    """Returns frozenset of class name strings, not Problem objects."""
    problems = [_p("x", "f:0"), _p("x", "f:1"), _p("y", "f:2")]
    result = class_count_above_threshold(problems, 1)
    assert isinstance(result, frozenset), "Must return frozenset"
    assert result == frozenset({"x"}), "Only x has count > 1"
