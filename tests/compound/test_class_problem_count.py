"""Item 551: class_problem_count() -- count of problems per class (2026-06-08).

``class_problem_count(problems) -> dict[str, int]``:
Returns a {class_name: count} mapping of problem counts per class.
Unweighted -- counts problems, ignores severity.
Empty -> {}.  Pure; no I/O.

Discriminating tests -- each kills a plausible wrong implementation:

  1. PRIMARY DISC.: returns dict (not float) and uses COUNTS (not weights).
     2 problems in same class: count=2, but weighted score may differ.
     Kills impl reusing class_score_sum (returns float 15.0, not {cls: 2}).
  2. Multiple classes each get their own count.
     Kills impl returning only one entry.
  3. Count is unweighted -- same for any severity.
     Kills impl that applies severity weights to counting.
  4. Empty -> {} (empty dict, not 0.0 or raise).
     Kills impl without empty guard.
  5. Problems with same class but different severities all count.
     Kills impl that deduplicates on finding_id.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import Problem, class_problem_count


def _p(cls: str, fid: str, sev: str) -> Problem:
    return Problem(problem_class=cls, finding_id=fid, severity=sev)


def test_returns_dict_of_counts_not_float() -> None:
    """PRIMARY DISC.: returns dict[str, int] with COUNTS, not float/score.

    2 problems in class A (HIGH + LOW), 1 problem in class B.
    class_score_sum with weights {HIGH:10, LOW:1} = 11.0 for A, 10.0 for B.
    class_problem_count = {'A': 2, 'B': 1} -- unweighted integer counts.
    Kills impl reusing class_score_sum (returns float, not dict).
    """
    problems = [
        _p("A", "f1", "HIGH"),  # A count: +1
        _p("A", "f2", "LOW"),  # A count: +1 -> A=2
        _p("B", "f3", "HIGH"),  # B count: +1 -> B=1
    ]
    result = class_problem_count(problems)
    assert isinstance(result, dict), "Must return dict; got " + repr(type(result))
    assert result == {"A": 2, "B": 1}, (
        f"class_problem_count = {{'A': 2, 'B': 1}}; got {result} "
        f"(float = wrong type; {{'A': 11.0}} = weighted score is wrong)"
    )


def test_each_class_gets_independent_count() -> None:
    """Multiple classes each have their own independent count.

    3 classes: A=1, B=2, C=3.
    Kills impl returning only the total or only one class.
    """
    problems = [
        _p("A", "f1", "X"),
        _p("B", "f2", "X"),
        _p("B", "f3", "X"),
        _p("C", "f4", "X"),
        _p("C", "f5", "X"),
        _p("C", "f6", "X"),
    ]
    result = class_problem_count(problems)
    assert result == {"A": 1, "B": 2, "C": 3}, f"Counts: A=1, B=2, C=3; got {result}"


def test_count_ignores_severity_weights() -> None:
    """Count is unweighted -- severity has no effect on count.

    3 problems in class X (all different severities): count = 3 regardless.
    Kills impl that multiplies or weights by severity.
    """
    problems = [
        _p("X", "f1", "CRITICAL"),  # +1
        _p("X", "f2", "LOW"),  # +1
        _p("X", "f3", "MEDIUM"),  # +1 -> X=3
    ]
    result = class_problem_count(problems)
    assert result == {"X": 3}, (
        f"3 problems in X -> count=3; got {result} (weighted sum would be wrong)"
    )


def test_empty_returns_empty_dict() -> None:
    """Empty problems -> {} (not 0.0, not raise)."""
    result = class_problem_count([])
    assert result == {}, f"Empty -> {{}}; got {result}"


def test_same_class_different_fids_all_counted() -> None:
    """All problems with same class are counted even with different finding_ids.

    Kills impl that deduplicates on finding_id within a class.
    """
    problems = [
        _p("BUG", "bug-001", "HIGH"),
        _p("BUG", "bug-002", "HIGH"),
        _p("BUG", "bug-003", "LOW"),
        _p("PERF", "perf-001", "MED"),
    ]
    result = class_problem_count(problems)
    assert result.get("BUG") == 3, (
        f"3 problems in BUG class -> count=3; got BUG={result.get('BUG')} "
        f"(1 = deduplicated by fid is wrong)"
    )
    assert result.get("PERF") == 1, f"1 problem in PERF -> count=1; got {result.get('PERF')}"
