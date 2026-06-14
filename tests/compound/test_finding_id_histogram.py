"""Item 390: finding_id_histogram() — frequency histogram of finding_id values (2026-06-08).

``finding_id_histogram(problems) -> dict[str, int]``:
Returns {finding_id: record_count} for every distinct finding_id.
The same finding_id under two different classes counts as 2.
Empty -> {}.  Pure; no I/O.

Discriminating tests — each kills a plausible wrong implementation:

  1. PRIMARY DISC.: same fid under two classes counts as 2, not 1.
     Kills impl that deduplicates by finding_id before counting.
  2. Values are integer counts (dict[str, int]), not frozensets.
     Kills impl returning finding_id_to_classes output.
  3. Every distinct finding_id appears exactly once as a key.
     Kills impl missing fids.
  4. Empty input returns {}.
     Kills impl raising on empty.
  5. Sum of all histogram values equals len(problems).
     Kills impl double-counting or missing records.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import (
    Problem,
    finding_id_histogram,
)


def _p(cls: str, fid: str, sev: str = "") -> Problem:
    return Problem(problem_class=cls, finding_id=fid, severity=sev)


def test_same_fid_in_two_classes_counts_as_two() -> None:
    """Same finding_id under two different classes counts as 2.

    PRIMARY DISCRIMINATOR: kills impl deduplicating by finding_id.
    shared-fid in classes a and b = count 2; unique-fid in a only = count 1.
    """
    problems = [
        _p("a", "shared-fid"),
        _p("b", "shared-fid"),
        _p("a", "unique-fid"),
    ]
    result = finding_id_histogram(problems)
    assert result["shared-fid"] == 2, "shared-fid across 2 classes → count=2; got " + repr(result)
    assert result["unique-fid"] == 1, "unique-fid in 1 class → count=1; got " + repr(result)


def test_values_are_integer_counts_not_frozensets() -> None:
    """Values are integers, not frozensets.

    Kills impl returning finding_id_to_classes.
    """
    problems = [_p("a", "f:0"), _p("b", "f:0"), _p("a", "f:1")]
    result = finding_id_histogram(problems)
    assert isinstance(result, dict), "Must return dict; got " + repr(type(result))
    assert all(isinstance(v, int) for v in result.values()), "Values must be int"


def test_every_finding_id_appears_exactly_once() -> None:
    """Every distinct finding_id is a key exactly once.

    Kills impl missing or duplicating keys.
    """
    problems = [_p("a", "f:0"), _p("b", "f:1"), _p("a", "f:0"), _p("c", "f:2")]
    result = finding_id_histogram(problems)
    assert set(result.keys()) == {"f:0", "f:1", "f:2"}, "Keys: " + repr(set(result.keys()))
    assert result["f:0"] == 2, "f:0 appears twice; got " + repr(result["f:0"])
    assert result["f:1"] == 1
    assert result["f:2"] == 1


def test_empty_returns_empty_dict() -> None:
    """Empty input returns {}."""
    assert finding_id_histogram([]) == {}


def test_sum_equals_total_record_count() -> None:
    """Sum of all histogram values equals the total number of records.

    Kills impl double-counting or missing records.
    """
    problems = [
        _p("a", "f:0"),
        _p("b", "f:0"),
        _p("a", "f:1"),
        _p("b", "f:2"),
        _p("c", "f:1"),
    ]
    result = finding_id_histogram(problems)
    assert sum(result.values()) == len(problems), (
        "Sum must equal len(problems)=" + str(len(problems)) + "; got " + repr(result)
    )
