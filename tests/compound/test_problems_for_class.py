"""Item 340: problems_for_class() — all Problem records belonging to a class (2026-06-08).

``problems_for_class(problems, class_name) -> list[Problem]``:
Returns all Problem objects whose problem_class equals class_name (exact match).
Closes the bidirectional-index quadrant with finding_ids_for_class, classes_for_finding_id,
problems_for_finding_id.  Unknown class -> [].  Empty input -> [].  Pure; no I/O.

Discriminating tests — each kills a plausible wrong implementation:

  1. PRIMARY DISC.: returns Problem objects not strings.
     Kills impl returning class_name or finding_ids.
  2. Returns ONLY problems from the requested class, not other classes.
     Kills impl returning all problems.
  3. Unknown class_name returns [] not an error.
     Kills impl raising KeyError.
  4. Empty input returns [].
     Kills impl raising on empty.
  5. Preserves original insertion order.
     Kills impl that sorts or reorders.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import (
    Problem,
    problems_for_class,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _p(cls: str, fid: str) -> Problem:
    return Problem(problem_class=cls, finding_id=fid)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_returns_problem_objects_not_strings() -> None:
    """Returns Problem instances, not class names or finding_ids.

    PRIMARY DISCRIMINATOR: kills impl returning class_name or finding_id strings.
    """
    problems = [_p("alpha", "F001"), _p("beta", "F002")]
    result = problems_for_class(problems, "alpha")
    assert len(result) == 1, "1 alpha problem; got " + repr(len(result))
    assert isinstance(result[0], Problem), "Must return Problem objects; got " + repr(
        type(result[0])
    )
    assert result[0].problem_class == "alpha"


def test_only_requested_class_returned() -> None:
    """Only problems from the requested class are returned.

    Kills impl returning all problems.
    alpha: 2 problems, beta: 1 problem; request alpha -> only alpha's 2 returned.
    """
    problems = [
        _p("alpha", "F001"),
        _p("beta", "F002"),
        _p("alpha", "F003"),
    ]
    result = problems_for_class(problems, "alpha")
    assert all(p.problem_class == "alpha" for p in result), (
        "All returned problems must be alpha; got " + repr([p.problem_class for p in result])
    )
    assert len(result) == 2, "2 alpha problems; got " + repr(len(result))


def test_unknown_class_returns_empty_list() -> None:
    """Unknown class_name returns [] without raising.

    Kills impl raising KeyError.
    """
    problems = [_p("alpha", "F001")]
    result = problems_for_class(problems, "UNKNOWN_CLASS")
    assert result == [], "unknown class -> []; got " + repr(result)


def test_empty_input_returns_empty_list() -> None:
    """Empty input returns [] without raising."""
    result = problems_for_class([], "alpha")
    assert result == [], "empty -> []; got " + repr(result)


def test_original_insertion_order_preserved() -> None:
    """Returned problems maintain original insertion order.

    Kills impl that sorts or reorders.
    5 alpha problems in F005, F001, F003, F002, F004 order -> same order returned.
    """
    fids = ["F005", "F001", "F003", "F002", "F004"]
    problems = [_p("alpha", fid) for fid in fids] + [_p("beta", "F999")]
    result = problems_for_class(problems, "alpha")
    assert [p.finding_id for p in result] == fids, "Must preserve insertion order; got " + repr(
        [p.finding_id for p in result]
    )
