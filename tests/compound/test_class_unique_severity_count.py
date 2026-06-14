"""Item 554: class_unique_severity_count() -- distinct severity labels per class (2026-06-08).

``class_unique_severity_count(problems) -> dict[str, int]``:
Returns {class: count_of_distinct_severities} for each class.
Counts distinct severity STRING labels, not weighted scores.
Empty -> {}.  Pure; no I/O.

Discriminating tests -- each kills a plausible wrong implementation:

  1. PRIMARY DISC.: counts DISTINCT severity labels (not total problems).
     Class A: [HIGH, HIGH, LOW] -> distinct=2 (not 3 total problems).
     Kills impl reusing class_problem_count (returns 3, not 2).
  2. Returns dict (not float), keyed on class name.
     Kills impl returning a single float.
  3. Empty class (empty input) -> {} (not 0.0 or raise).
     Kills impl without empty guard.
  4. Two classes each get their own independent distinct count.
     Kills impl returning only a global count.
  5. Severity strings are compared exactly (case-sensitive).
     "HIGH" and "high" are two distinct severities.
     Kills impl doing case-insensitive deduplication.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import Problem, class_unique_severity_count


def _p(cls: str, fid: str, sev: str) -> Problem:
    return Problem(problem_class=cls, finding_id=fid, severity=sev)


def test_counts_distinct_severities_not_total_problems() -> None:
    """PRIMARY DISC.: counts DISTINCT severity strings, not total problem count.

    Class A: 3 problems [HIGH, HIGH, LOW] -> 2 distinct severities.
    class_problem_count would return 3 -- kills that impl.
    """
    problems = [
        _p("A", "f1", "HIGH"),  # A severities: {HIGH}
        _p("A", "f2", "HIGH"),  # A severities: {HIGH}    (duplicate)
        _p("A", "f3", "LOW"),  # A severities: {HIGH, LOW}  -> distinct=2
        _p("B", "f4", "MED"),  # B severities: {MED} -> distinct=1
    ]
    result = class_unique_severity_count(problems)
    assert isinstance(result, dict), "Must return dict; got " + repr(type(result))
    assert result == {"A": 2, "B": 1}, (
        f"distinct severities: A=2, B=1; got {result} (A=3 = total problem count is wrong)"
    )


def test_returns_dict_not_float() -> None:
    """Returns dict[str, int], not a float.

    Kills impl reusing any float-returning function.
    """
    problems = [_p("X", "f1", "S")]
    result = class_unique_severity_count(problems)
    assert isinstance(result, dict), f"Must return dict; got {type(result)}"
    assert result == {"X": 1}, f"Single problem -> {{'X': 1}}; got {result}"


def test_empty_returns_empty_dict() -> None:
    """Empty problems -> {} (not 0.0 or raise)."""
    result = class_unique_severity_count([])
    assert result == {}, f"Empty -> {{}}; got {result}"


def test_each_class_gets_independent_distinct_count() -> None:
    """Two classes independently count their own distinct severities.

    Class P: [HIGH, LOW, MED] -> 3 distinct.
    Class Q: [HIGH, HIGH] -> 1 distinct.
    Kills impl returning a global deduplicated count.
    """
    problems = [
        _p("P", "f1", "HIGH"),
        _p("P", "f2", "LOW"),
        _p("P", "f3", "MED"),
        _p("Q", "f4", "HIGH"),
        _p("Q", "f5", "HIGH"),
    ]
    result = class_unique_severity_count(problems)
    assert result == {"P": 3, "Q": 1}, f"distinct: P=3, Q=1; got {result}"


def test_severity_strings_are_case_sensitive() -> None:
    """Severity labels are compared case-sensitively: 'HIGH' \!= 'high'.

    Class A: [HIGH, high] -> 2 distinct (not 1).
    Kills impl doing case-insensitive deduplication.
    """
    problems = [
        _p("A", "f1", "HIGH"),
        _p("A", "f2", "high"),
    ]
    result = class_unique_severity_count(problems)
    assert result.get("A") == 2, (
        f"'HIGH' and 'high' are distinct -> 2; got {result.get('A')} "
        f"(1 = case-insensitive dedup is wrong)"
    )
