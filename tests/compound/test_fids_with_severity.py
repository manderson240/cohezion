"""Item 464: fids_with_severity() -- finding IDs with a given severity (2026-06-08).

``fids_with_severity(problems, severity) -> list[str]``:
Returns sorted list of distinct finding_id values where severity matches.
[] for empty or absent severity.  Pure; no I/O.

Discriminating tests -- each kills a plausible wrong implementation:

  1. PRIMARY DISC.: returns SORTED LIST of fid strings (not frozenset, not classes).
     Kills impl reusing classes_with_severity (returns frozenset of class names).
  2. [] for absent/unknown severity (not raise).
     Kills impl with unguarded access on missing key.
  3. [] for empty input.
     Kills impl with unguarded access.
  4. Result is sorted alphabetically (deterministic ordering).
     Kills impl returning in insertion or arbitrary order.
  5. Only fids where severity matches (excluded fids omitted).
     Kills impl that returns all fids regardless of severity.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import (
    Problem,
    fids_with_severity,
)


def _p(cls: str, fid: str, sev: str) -> Problem:
    return Problem(problem_class=cls, finding_id=fid, severity=sev)


def test_returns_sorted_list_not_frozenset() -> None:
    """PRIMARY DISC.: returns sorted list of fid strings, not frozenset of classes.

    Both f1 and f2 have HIGH severity.  Result is ['f1', 'f2'] (sorted list).
    classes_with_severity would return frozenset{'cls_a', 'cls_b'} -- wrong type.
    Kills impl reusing classes_with_severity.
    """
    problems = [
        _p("cls_a", "f1", "HIGH"),
        _p("cls_b", "f2", "HIGH"),
        _p("cls_c", "f3", "LOW"),
    ]
    result = fids_with_severity(problems, "HIGH")
    assert isinstance(result, list), "Must return list; got " + repr(type(result))
    assert result == ["f1", "f2"], "Sorted HIGH fids=['f1','f2']; got " + repr(result)


def test_absent_severity_returns_empty() -> None:
    """Absent severity -> [] (not raise)."""
    problems = [_p("c", "f1", "HIGH")]
    result = fids_with_severity(problems, "NONEXISTENT")
    assert result == [], "Absent severity -> []; got " + repr(result)


def test_empty_input_returns_empty() -> None:
    """Empty input -> []."""
    result = fids_with_severity([], "HIGH")
    assert result == [], "Empty -> []; got " + repr(result)
    assert isinstance(result, list)


def test_result_sorted_alphabetically() -> None:
    """Finding IDs are returned in sorted (alphabetical) order."""
    problems = [
        _p("c", "fid_z", "HIGH"),
        _p("c", "fid_a", "HIGH"),
        _p("c", "fid_m", "HIGH"),
    ]
    result = fids_with_severity(problems, "HIGH")
    assert result == sorted(result), "Must be sorted; got " + repr(result)
    assert result == ["fid_a", "fid_m", "fid_z"], "Expected sorted order; got " + repr(result)


def test_only_matching_fids_included() -> None:
    """Only fids where severity matches are returned; others excluded."""
    problems = [
        _p("c", "f_high", "HIGH"),
        _p("c", "f_low", "LOW"),
        _p("c", "f_also_high", "HIGH"),
    ]
    result = fids_with_severity(problems, "HIGH")
    assert "f_high" in result, "f_high should be included; got " + repr(result)
    assert "f_also_high" in result, "f_also_high should be included; got " + repr(result)
    assert "f_low" not in result, "f_low should NOT be included; got " + repr(result)
