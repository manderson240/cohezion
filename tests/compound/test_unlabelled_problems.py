"""Item 345: unlabelled_problems() -- filter to problems with empty severity (2026-06-08).

``unlabelled_problems(problems) -> list[Problem]``:
Complement of labelled_problems. Returns Problem objects with severity == ''.
labelled_problems + unlabelled_problems partition all problems.
Empty input -> [].  All-labelled -> [].  Pure; no I/O.

Discriminating tests:

  1. PRIMARY DISC.: returns Problem objects not strings.
  2. Only unlabelled (severity == '') returned.
  3. labelled + unlabelled partition is disjoint and complete.
  4. Empty input returns [].
  5. All-labelled input returns [].
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import (
    Problem,
    labelled_problems,
    unlabelled_problems,
)


def _ps(cls, idx, sev):
    return Problem(problem_class=cls, finding_id=f"{cls}:{idx}", severity=sev)


def _p(cls, idx):
    return Problem(problem_class=cls, finding_id=f"{cls}:{idx}")


def test_returns_problem_objects_not_strings():
    """Returns Problem instances not severity strings."""
    problems = [_p("alpha", 0), _ps("beta", 0, "HIGH")]
    result = unlabelled_problems(problems)
    assert len(result) == 1
    assert isinstance(result[0], Problem)
    assert result[0].finding_id == "alpha:0"


def test_only_unlabelled_returned():
    """Only problems with severity='' are returned."""
    problems = [_p("a", 0), _ps("b", 0, "HIGH"), _p("c", 0)]
    result = unlabelled_problems(problems)
    assert len(result) == 2
    assert all(p.severity == "" for p in result)


def test_labelled_and_unlabelled_partition():
    """labelled + unlabelled == all problems (disjoint partition)."""
    problems = [_p("a", 0), _ps("b", 0, "HIGH"), _p("c", 0), _ps("d", 0, "LOW")]
    lab = labelled_problems(problems)
    unlab = unlabelled_problems(problems)
    lab_ids = {p.finding_id for p in lab}
    unlab_ids = {p.finding_id for p in unlab}
    all_ids = {p.finding_id for p in problems}
    assert lab_ids & unlab_ids == set(), "Disjoint"
    assert lab_ids | unlab_ids == all_ids, "Complete partition"


def test_empty_input_returns_empty_list():
    """Empty input returns []."""
    assert unlabelled_problems([]) == []


def test_all_labelled_returns_empty_list():
    """All-labelled input returns []."""
    problems = [_ps("a", i, "HIGH") for i in range(5)]
    assert unlabelled_problems(problems) == []
