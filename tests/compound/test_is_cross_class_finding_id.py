"""Item 404: is_cross_class_finding_id() — boolean cross-class test (2026-06-08).

``is_cross_class_finding_id(problems, target_fid) -> bool``:
Returns True if target_fid appears in >= 2 distinct classes.
Returns False if it spans only 1 class, is absent, or problems is empty.
Pure; no I/O.

Discriminating tests — each kills a plausible wrong implementation:

  1. PRIMARY DISC.: True only when >= 2 DISTINCT CLASSES (not >= 2 records).
     Kills impl that counts records instead of classes.
  2. Returns BOOL (type(result) is bool), not int.
     Kills impl returning class_count_for_finding_id.
  3. Absent fid -> False not raise.
     Kills impl raising on absent fid.
  4. Empty problems -> False.
     Kills impl raising on empty.
  5. Single-class fid -> False even with many records.
     Kills impl triggering on record count >= 2.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import (
    Problem,
    is_cross_class_finding_id,
)


def _p(cls: str, fid: str) -> Problem:
    return Problem(problem_class=cls, finding_id=fid)


def test_true_only_when_two_or_more_distinct_classes() -> None:
    """True only when target_fid spans >= 2 distinct classes.

    PRIMARY DISCRIMINATOR: kills impl counting records.
    """
    problems = [_p("alpha", "shared"), _p("beta", "shared"), _p("alpha", "shared")]
    result = is_cross_class_finding_id(problems, "shared")
    assert type(result) is bool, "Must return bool; got " + repr(type(result))
    assert result is True, "shared in alpha+beta (2 classes) -> True; got " + repr(result)


def test_returns_bool_not_int() -> None:
    """Returns bool, not integer class count.

    Kills impl returning class_count_for_finding_id.
    """
    problems = [_p("alpha", "fid"), _p("beta", "fid")]
    result = is_cross_class_finding_id(problems, "fid")
    assert type(result) is bool, "Must return bool; got " + repr(type(result))


def test_absent_fid_returns_false() -> None:
    """Absent fid returns False, not raise or None."""
    result = is_cross_class_finding_id([_p("alpha", "other")], "missing")
    assert type(result) is bool
    assert result is False


def test_empty_problems_returns_false() -> None:
    """Empty problems list returns False."""
    assert is_cross_class_finding_id([], "any") is False


def test_single_class_fid_returns_false_even_with_many_records() -> None:
    """Single class fid returns False even with many records.

    Kills impl that triggers on record count >= 2.
    """
    problems = [_p("alpha", "fid") for _ in range(5)]
    result = is_cross_class_finding_id(problems, "fid")
    assert result is False, "Only 1 distinct class -> False; got " + repr(result)
