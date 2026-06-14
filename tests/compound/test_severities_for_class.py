"""Item 402: severities_for_class() — distinct severity labels for a class (2026-06-08).

``severities_for_class(problems, target_class) -> frozenset[str]``:
Returns a frozenset of all distinct severity strings (including '') in target_class.
Class absent -> frozenset().  Empty -> frozenset().  Pure; no I/O.

Discriminating tests — each kills a plausible wrong implementation:

  1. PRIMARY DISC.: returns FROZENSET[str] of severity labels, not counts.
     Kills impl returning severity_histogram.
  2. '' included when unlabelled records exist in that class.
     Kills impl filtering out unlabelled records.
  3. Deduplicated — same severity appearing multiple times appears once.
     Kills impl returning a list with duplicates.
  4. Class absent -> frozenset() not raise or None.
     Kills impl raising KeyError on absent class.
  5. Only severities from the target class, not from other classes.
     Kills impl returning all severities from all problems.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import (
    Problem,
    severities_for_class,
)


def _p(cls: str, sev: str, fid: str = "f") -> Problem:
    return Problem(problem_class=cls, finding_id=fid, severity=sev)


def test_returns_frozenset_of_severity_labels() -> None:
    """Returns frozenset[str] of distinct severities, not counts.

    PRIMARY DISCRIMINATOR: kills impl returning severity_histogram.
    """
    problems = [_p("alpha", "HIGH"), _p("alpha", "LOW"), _p("alpha", "HIGH")]
    result = severities_for_class(problems, "alpha")
    assert isinstance(result, frozenset), "Must return frozenset; got " + repr(type(result))
    assert result == frozenset({"HIGH", "LOW"}), "Expected {HIGH, LOW}; got " + repr(result)


def test_empty_string_included_for_unlabelled_records() -> None:
    """'' is included when unlabelled records exist in that class.

    Kills impl filtering out unlabelled records.
    """
    problems = [_p("cls", "HIGH"), _p("cls", ""), _p("cls", "")]
    result = severities_for_class(problems, "cls")
    assert "" in result, "'' must be included for unlabelled records"
    assert "HIGH" in result


def test_deduplicated() -> None:
    """Same severity appearing multiple times appears only once.

    Kills impl returning a list with duplicates.
    """
    problems = [_p("cls", "HIGH"), _p("cls", "HIGH"), _p("cls", "HIGH")]
    result = severities_for_class(problems, "cls")
    assert result == frozenset({"HIGH"}), "Deduplicated; got " + repr(result)


def test_class_absent_returns_empty_frozenset() -> None:
    """Class absent returns frozenset() not raise or None."""
    problems = [_p("other", "HIGH")]
    result = severities_for_class(problems, "missing")
    assert result == frozenset(), "Absent class -> frozenset(); got " + repr(result)


def test_only_severities_from_target_class() -> None:
    """Only severities from target_class, not from other classes.

    Kills impl returning all severities from all problems.
    """
    problems = [
        _p("alpha", "HIGH"),
        _p("beta", "CRITICAL"),
        _p("beta", "LOW"),
    ]
    result = severities_for_class(problems, "alpha")
    assert result == frozenset({"HIGH"}), "Only alpha's severities; got " + repr(result)
    assert "CRITICAL" not in result
    assert "LOW" not in result
