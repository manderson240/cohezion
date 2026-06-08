"""Item 394: problems_by_class() — group Problem records by class name (2026-06-08).

``problems_by_class(problems) -> dict[str, list[Problem]]``:
Returns {class_name: [Problem, ...]} for every distinct class.
Preserves input order within each list.
Empty -> {}.  Pure; no I/O.

Discriminating tests — each kills a plausible wrong implementation:

  1. PRIMARY DISC.: values are LIST[Problem] objects, not counts or frozensets.
     Kills impl returning problem_class_histogram or class_to_finding_ids.
  2. Input order preserved within each class list.
     Kills impl that reorders records (e.g. by sorting finding_id).
  3. Every distinct class present as a key.
     Kills impl that drops a class.
  4. Empty input returns {}.
     Kills impl raising on empty.
  5. Problem objects in each list are the exact same objects, not copies.
     Kills impl that reconstructs Problem objects instead of referencing originals.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import (
    Problem,
    problems_by_class,
)


def _p(cls: str, fid: str, sev: str = "") -> Problem:
    return Problem(problem_class=cls, finding_id=fid, severity=sev)


def test_values_are_lists_of_problem_objects() -> None:
    """Values are list[Problem], not counts or frozensets.

    PRIMARY DISCRIMINATOR: kills impl returning histogram or frozensets.
    """
    p0 = _p("alpha", "f:0")
    p1 = _p("alpha", "f:1")
    p2 = _p("beta", "f:2")
    result = problems_by_class([p0, p1, p2])
    assert isinstance(result, dict), "Must return dict"
    assert isinstance(result["alpha"], list), "Value must be list; got " + repr(type(result["alpha"]))
    assert all(isinstance(p, Problem) for p in result["alpha"]), "List must contain Problem objects"
    assert len(result["alpha"]) == 2, "alpha has 2 records; got " + repr(len(result["alpha"]))
    assert len(result["beta"]) == 1


def test_input_order_preserved_within_class() -> None:
    """Records within each class list preserve the original input order.

    Kills impl that reorders by finding_id or severity.
    """
    p0 = _p("cls", "z-first")
    p1 = _p("cls", "a-second")
    p2 = _p("cls", "m-third")
    result = problems_by_class([p0, p1, p2])
    assert result["cls"][0].finding_id == "z-first", "First record must be z-first"
    assert result["cls"][1].finding_id == "a-second"
    assert result["cls"][2].finding_id == "m-third"


def test_every_distinct_class_is_a_key() -> None:
    """Every distinct class appears exactly once as a key.

    Kills impl that drops some classes.
    """
    problems = [_p("a", "f:0"), _p("b", "f:1"), _p("c", "f:2"), _p("a", "f:3")]
    result = problems_by_class(problems)
    assert set(result.keys()) == {"a", "b", "c"}, "Keys: " + repr(set(result.keys()))
    assert len(result["a"]) == 2
    assert len(result["b"]) == 1


def test_empty_returns_empty_dict() -> None:
    """Empty input returns {}."""
    assert problems_by_class([]) == {}


def test_problem_objects_are_same_identity() -> None:
    """Problem objects in each list are the exact originals (identity preserved).

    Kills impl reconstructing new Problem objects from fields.
    """
    p0 = _p("alpha", "f:0")
    p1 = _p("alpha", "f:1")
    result = problems_by_class([p0, p1])
    assert result["alpha"][0] is p0, "First object must be identical to p0"
    assert result["alpha"][1] is p1, "Second object must be identical to p1"
