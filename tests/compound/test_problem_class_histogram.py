"""Item 388: problem_class_histogram() — class frequency histogram (2026-06-08).

``problem_class_histogram(problems) -> dict[str, int]``:
Returns {class_name: record_count} for every distinct class.
Counts ALL records regardless of severity label.
Empty -> {}.  Pure; no I/O.

Discriminating tests — each kills a plausible wrong implementation:

  1. PRIMARY DISC.: values are INTEGER counts, not frozensets or sets.
     Kills impl returning class_to_finding_ids output.
  2. Counts ALL records including unlabelled ones.
     Kills impl filtering out unlabelled problems before counting.
  3. Every distinct class appears exactly once as a key.
     Kills impl missing some classes.
  4. Empty input returns {}.
     Kills impl raising on empty.
  5. Count reflects total record count not distinct finding_id count.
     Kills impl using len(set(fids)) instead of raw record count.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import (
    Problem,
    problem_class_histogram,
)


def _p(cls: str, fid: str, sev: str = "") -> Problem:
    return Problem(problem_class=cls, finding_id=fid, severity=sev)


def test_values_are_integer_counts_not_frozensets() -> None:
    """Values are integers, not frozensets or lists.

    PRIMARY DISCRIMINATOR: kills impl returning class_to_finding_ids.
    """
    problems = [_p("alpha", "f:0"), _p("alpha", "f:1"), _p("beta", "f:2")]
    result = problem_class_histogram(problems)
    assert isinstance(result, dict), "Must return dict; got " + repr(type(result))
    for cls, count in result.items():
        assert isinstance(count, int), (
            "Value for " + repr(cls) + " must be int; got " + repr(type(count))
        )
    assert result["alpha"] == 2, "alpha has 2 records; got " + repr(result["alpha"])
    assert result["beta"] == 1, "beta has 1 record; got " + repr(result["beta"])


def test_counts_unlabelled_records() -> None:
    """Unlabelled records are counted the same as labelled ones.

    Kills impl filtering out unlabelled problems.
    """
    problems = [
        _p("cls", "f:0", "HIGH"),
        _p("cls", "f:1"),  # unlabelled
        _p("cls", "f:2"),  # unlabelled
    ]
    result = problem_class_histogram(problems)
    assert result["cls"] == 3, "All 3 records (labelled + unlabelled) counted; got " + repr(result)


def test_every_class_appears_exactly_once() -> None:
    """Every distinct class appears exactly once as a key.

    Kills impl missing some classes.
    """
    problems = [_p("a", "f:0"), _p("b", "f:1"), _p("c", "f:2"), _p("a", "f:3")]
    result = problem_class_histogram(problems)
    assert set(result.keys()) == {"a", "b", "c"}, "Keys: " + repr(set(result.keys()))
    assert result["a"] == 2, "a appears twice; got " + repr(result["a"])


def test_empty_returns_empty_dict() -> None:
    """Empty input returns {}."""
    assert problem_class_histogram([]) == {}


def test_count_is_records_not_distinct_fids() -> None:
    """Count reflects total record count, not distinct finding_id count.

    Kills impl using len(set(fids)) instead of raw record count.
    Same finding_id appearing 3 times under a class counts as 3.
    """
    problems = [_p("cls", "same-fid") for _ in range(4)]
    result = problem_class_histogram(problems)
    assert result["cls"] == 4, "4 records with same fid → count=4; got " + repr(result["cls"])
