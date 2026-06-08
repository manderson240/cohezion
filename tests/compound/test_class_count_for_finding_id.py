"""Item 403: class_count_for_finding_id() — distinct class count for a finding_id (2026-06-08).

``class_count_for_finding_id(problems, target_fid) -> int``:
Returns the count of distinct problem_class values that have at least one
record with finding_id == target_fid.
0 if fid is absent or problems is empty.  Pure; no I/O.

Discriminating tests — each kills a plausible wrong implementation:

  1. PRIMARY DISC.: counts DISTINCT CLASSES, not total records.
     Kills impl returning problem_count_for_class or total record count.
  2. Same class appearing twice with same fid counts as 1, not 2.
     Kills impl counting records instead of distinct classes.
  3. Returns 0 when fid is absent (not KeyError or None).
     Kills impl raising on absent fid.
  4. Empty problems -> 0.
     Kills impl raising on empty.
  5. Only counts classes containing target_fid, not all classes.
     Kills impl returning total distinct class count.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import (
    Problem,
    class_count_for_finding_id,
)


def _p(cls: str, fid: str, sev: str = "") -> Problem:
    return Problem(problem_class=cls, finding_id=fid, severity=sev)


def test_counts_distinct_classes_not_records() -> None:
    """Counts distinct classes, not total record count.

    PRIMARY DISCRIMINATOR: kills impl returning total record count.
    shared-fid in alpha and beta -> 2 distinct classes, not 3 records.
    """
    problems = [
        _p("alpha", "shared"),
        _p("beta", "shared"),
        _p("alpha", "shared"),  # alpha again — still 1 distinct class
    ]
    result = class_count_for_finding_id(problems, "shared")
    assert isinstance(result, int), "Must return int; got " + repr(type(result))
    assert result == 2, "shared spans 2 distinct classes (alpha, beta); got " + repr(result)


def test_same_class_twice_counts_as_one() -> None:
    """Same class with same fid appearing twice counts as 1.

    Kills impl counting records instead of distinct classes.
    """
    problems = [_p("alpha", "fid"), _p("alpha", "fid"), _p("alpha", "fid")]
    result = class_count_for_finding_id(problems, "fid")
    assert result == 1, "Only 1 distinct class (alpha); got " + repr(result)


def test_returns_zero_when_fid_absent() -> None:
    """Returns 0 when fid is absent, not KeyError or None."""
    problems = [_p("alpha", "other-fid")]
    result = class_count_for_finding_id(problems, "missing-fid")
    assert result == 0, "fid absent -> 0; got " + repr(result)
    assert isinstance(result, int)


def test_empty_problems_returns_zero() -> None:
    """Empty problems list returns 0."""
    assert class_count_for_finding_id([], "any") == 0


def test_only_classes_containing_target_fid() -> None:
    """Counts only classes containing the target fid, not all classes.

    Kills impl returning total distinct class count in the dataset.
    """
    problems = [
        _p("alpha", "target-fid"),
        _p("beta", "other-fid"),
        _p("gamma", "other-fid"),
    ]
    result = class_count_for_finding_id(problems, "target-fid")
    assert result == 1, "Only alpha has target-fid; got " + repr(result)
