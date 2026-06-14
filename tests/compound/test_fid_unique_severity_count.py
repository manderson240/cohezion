"""Item 555: fid_unique_severity_count() -- distinct severity labels per fid (2026-06-08).

``fid_unique_severity_count(problems) -> dict[str, int]``:
Returns {finding_id: count_of_distinct_severities} for each fid.
Counts distinct severity strings per fid (case-sensitive).
Empty -> {}.  Pure; no I/O.

Discriminating tests -- each kills a plausible wrong implementation:

  1. PRIMARY DISC.: keyed on FID axis (not class axis).
     One class, 2 fids: fid_a has [HIGH, LOW, HIGH] -> distinct=2;
     fid_b has [MED] -> distinct=1.
     class_unique_severity_count = {'SameClass': 3} (HIGH, LOW, MED distinct in class).
     fid_unique_severity_count = {'fid_a': 2, 'fid_b': 1}.
     Kills impl reusing class_unique_severity_count on wrong axis.
  2. Counts DISTINCT per fid (not total occurrences per fid).
     fid with [HIGH, HIGH] -> 1 distinct, not 2.
     Kills impl reusing fid_problem_count (counts all problems, not distinct).
  3. Empty -> {} (not raise).
     Kills impl without empty guard.
  4. Each fid gets its own independent set of distinct severities.
     Kills impl using a global severity set across all fids.
  5. Case-sensitive severity strings.
     "MED" and "med" are two distinct severities within a fid.
     Kills impl normalizing case.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import Problem, fid_unique_severity_count


def _p(cls: str, fid: str, sev: str) -> Problem:
    return Problem(problem_class=cls, finding_id=fid, severity=sev)


def test_returns_fid_axis_distinct_count_not_class_axis() -> None:
    """PRIMARY DISC.: keyed on FID axis (not class axis).

    All problems in ONE class. fid_a: [HIGH, LOW, HIGH] -> 2 distinct.
    fid_b: [MED] -> 1 distinct.
    class_unique_severity_count = {'SameClass': 3} (H, L, M in class)
    fid_unique_severity_count = {'fid_a': 2, 'fid_b': 1}
    Kills impl reusing class_unique_severity_count on wrong axis.
    """
    problems = [
        _p("SameClass", "fid_a", "HIGH"),
        _p("SameClass", "fid_a", "LOW"),
        _p("SameClass", "fid_a", "HIGH"),  # duplicate -- still 2 distinct for fid_a
        _p("SameClass", "fid_b", "MED"),
    ]
    result = fid_unique_severity_count(problems)
    assert isinstance(result, dict), "Must return dict; got " + repr(type(result))
    assert result == {"fid_a": 2, "fid_b": 1}, (
        f"fid_a=2, fid_b=1; got {result} ({{'SameClass':3}} = class axis is wrong)"
    )


def test_counts_distinct_not_total_per_fid() -> None:
    """Counts DISTINCT severity labels per fid, not total problem count.

    fid_x: [HIGH, HIGH] -> distinct=1, total=2.
    Kills impl reusing fid_problem_count (returns 2, not 1).
    """
    problems = [
        _p("A", "fid_x", "HIGH"),
        _p("B", "fid_x", "HIGH"),  # same fid, same severity: still 1 distinct
    ]
    result = fid_unique_severity_count(problems)
    assert result.get("fid_x") == 1, (
        f"2 problems with same fid+severity -> distinct=1; got {result.get('fid_x')} "
        f"(2 = problem count is wrong)"
    )


def test_empty_returns_empty_dict() -> None:
    """Empty problems -> {} (not raise)."""
    result = fid_unique_severity_count([])
    assert result == {}, f"Empty -> {{}}; got {result}"


def test_each_fid_has_independent_severity_set() -> None:
    """Each fid's distinct severities are independent of other fids.

    fid_a: {HIGH, LOW} -> 2.  fid_b: {HIGH} -> 1.  fid_c: {LOW, MED, HIGH} -> 3.
    Kills impl using a global set shared across all fids.
    """
    problems = [
        _p("X", "fid_a", "HIGH"),
        _p("X", "fid_a", "LOW"),
        _p("Y", "fid_b", "HIGH"),
        _p("Z", "fid_c", "LOW"),
        _p("Z", "fid_c", "MED"),
        _p("Z", "fid_c", "HIGH"),
    ]
    result = fid_unique_severity_count(problems)
    assert result == {"fid_a": 2, "fid_b": 1, "fid_c": 3}, (
        f"Distinct severities: fid_a=2, fid_b=1, fid_c=3; got {result}"
    )


def test_severity_strings_are_case_sensitive() -> None:
    """Severity strings are case-sensitive: 'LOW' \!= 'low' within one fid.

    Kills impl normalizing case before deduplication.
    """
    problems = [
        _p("A", "fid_z", "LOW"),
        _p("B", "fid_z", "low"),  # different case -> 2 distinct
    ]
    result = fid_unique_severity_count(problems)
    assert result.get("fid_z") == 2, (
        f"'LOW' and 'low' are distinct -> 2; got {result.get('fid_z')} "
        f"(1 = case-insensitive is wrong)"
    )
