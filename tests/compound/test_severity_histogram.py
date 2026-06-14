"""Item 389: severity_histogram() — frequency histogram of severity values (2026-06-08).

``severity_histogram(problems) -> dict[str, int]``:
Returns {severity: record_count} for every distinct severity string.
The empty-string '' is included when any unlabelled problems are present.
Empty -> {}.  Pure; no I/O.

Discriminating tests — each kills a plausible wrong implementation:

  1. PRIMARY DISC.: values are INTEGER counts (dict[str, int]).
     Kills impl returning severity_to_finding_ids (frozensets).
  2. '' (unlabelled) is included as a key when present.
     Kills impl filtering out unlabelled problems.
  3. Counts all records (not distinct finding_ids per severity).
     Kills impl counting distinct fids per severity.
  4. Empty input returns {}.
     Kills impl raising on empty.
  5. Sum of all histogram values equals len(problems).
     Kills impl double-counting or missing records.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import (
    Problem,
    severity_histogram,
)


def _p(cls: str, fid: str, sev: str = "") -> Problem:
    return Problem(problem_class=cls, finding_id=fid, severity=sev)


def test_values_are_integer_counts_not_frozensets() -> None:
    """Values are integers, not frozensets.

    PRIMARY DISCRIMINATOR: kills impl returning severity_to_finding_ids.
    """
    problems = [_p("a", "f:0", "HIGH"), _p("b", "f:1", "HIGH"), _p("c", "f:2", "LOW")]
    result = severity_histogram(problems)
    assert isinstance(result, dict), "Must return dict; got " + repr(type(result))
    assert all(isinstance(v, int) for v in result.values()), "Values must be int"
    assert result["HIGH"] == 2, "HIGH appears twice; got " + repr(result.get("HIGH"))
    assert result["LOW"] == 1, "LOW appears once; got " + repr(result.get("LOW"))


def test_unlabelled_empty_string_included_as_key() -> None:
    """'' is a key when any unlabelled problems are present.

    Kills impl filtering out unlabelled problems.
    """
    problems = [_p("a", "f:0", "HIGH"), _p("b", "f:1"), _p("c", "f:2")]
    result = severity_histogram(problems)
    assert "" in result, "'' key must be present for unlabelled; got " + repr(result)
    assert result[""] == 2, "2 unlabelled records; got " + repr(result.get(""))
    assert result["HIGH"] == 1, "1 HIGH record; got " + repr(result.get("HIGH"))


def test_counts_all_records_not_distinct_fids() -> None:
    """Counts total records per severity, not distinct finding_ids.

    Kills impl using len(set(fids)) instead of raw count.
    """
    problems = [
        _p("a", "same-fid", "HIGH"),
        _p("b", "same-fid", "HIGH"),
        _p("c", "same-fid", "HIGH"),
    ]
    result = severity_histogram(problems)
    assert result["HIGH"] == 3, "3 records with HIGH (same fid) = 3; got " + repr(
        result.get("HIGH")
    )


def test_empty_returns_empty_dict() -> None:
    """Empty input returns {}."""
    assert severity_histogram([]) == {}


def test_sum_equals_total_record_count() -> None:
    """Sum of all histogram values equals the total number of records.

    Kills impl double-counting or missing records.
    """
    problems = [
        _p("a", "f:0", "HIGH"),
        _p("b", "f:1", "LOW"),
        _p("c", "f:2"),
        _p("d", "f:3", "HIGH"),
        _p("e", "f:4"),
    ]
    result = severity_histogram(problems)
    assert sum(result.values()) == len(problems), (
        "Sum of counts must equal len(problems)=" + str(len(problems)) + "; got " + repr(result)
    )
