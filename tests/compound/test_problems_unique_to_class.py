"""Item 354: problems_unique_to_class() -- problems exclusive to one class (2026-06-08).

``problems_unique_to_class(problems, class_name) -> list[Problem]``:
Returns all Problem objects for class_name whose finding_id does NOT appear
in any other class.  Finding_ids shared across classes are excluded.
Finding_ids appearing multiple times within class_name (but no other class)
ARE included.  Preserves original order.  Empty -> [].  Unknown -> [].
Pure; no I/O.

Discriminating tests:

  1. PRIMARY DISC.: cross-class shared finding_id is EXCLUDED.
     Kills impl returning all problems for the class.
  2. Within-class duplicate finding_id (not shared cross-class) IS included.
     Kills impl that drops within-class duplicates.
  3. Empty input returns [].
     Kills impl raising on empty.
  4. Unknown class_name returns [].
     Kills impl raising KeyError.
  5. Original insertion order preserved.
     Kills impl that reorders.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import (
    Problem,
    problems_unique_to_class,
)


def _p(cls: str, fid: str) -> Problem:
    return Problem(problem_class=cls, finding_id=fid)


def test_cross_class_shared_finding_id_excluded() -> None:
    """Finding_id shared with another class is excluded.

    PRIMARY DISCRIMINATOR: kills impl returning all alpha problems.
    alpha has F001(unique) + F002(shared with beta); only F001 problem returned.
    """
    problems = [_p("alpha", "F001"), _p("alpha", "F002"), _p("beta", "F002")]
    result = problems_unique_to_class(problems, "alpha")
    fids = {p.finding_id for p in result}
    assert "F001" in fids, "F001 (unique) must be included; got " + repr(fids)
    assert "F002" not in fids, "F002 (shared) must be excluded; got " + repr(fids)
    assert all(isinstance(p, Problem) for p in result), "Must return Problem objects"


def test_within_class_duplicate_not_cross_shared_is_included() -> None:
    """Finding_id appearing multiple times in class_name (not elsewhere) IS included.

    Kills impl that drops within-class duplicates or treats multi-occurrence as shared.
    alpha has F001 x3 (no other class has F001) -> all 3 returned.
    """
    problems = [
        _p("alpha", "F001"), _p("alpha", "F001"), _p("alpha", "F001"),
        _p("beta", "F999"),
    ]
    result = problems_unique_to_class(problems, "alpha")
    assert len(result) == 3, "All 3 within-class duplicates included; got " + repr(len(result))
    assert all(p.finding_id == "F001" for p in result)


def test_empty_input_returns_empty_list() -> None:
    """Empty problems returns []."""
    assert problems_unique_to_class([], "alpha") == []


def test_unknown_class_returns_empty_list() -> None:
    """Unknown class_name returns [] without raising."""
    problems = [_p("alpha", "F001")]
    assert problems_unique_to_class(problems, "UNKNOWN") == []


def test_original_insertion_order_preserved() -> None:
    """Returned problems maintain original insertion order.

    Kills impl that reorders by finding_id.
    """
    fids = ["F005", "F001", "F003"]
    problems = [_p("alpha", fid) for fid in fids] + [_p("beta", "F999")]
    result = problems_unique_to_class(problems, "alpha")
    assert [p.finding_id for p in result] == fids, (
        "Insertion order preserved; got " + repr([p.finding_id for p in result])
    )
