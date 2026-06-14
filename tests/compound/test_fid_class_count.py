"""Item 559: fid_class_count() -- count of distinct classes per fid (2026-06-08).

``fid_class_count(problems) -> dict[str, int]``:
Returns {fid: count_of_distinct_classes_for_that_fid}.
Spread indicator: cross-cutting fids appear in many classes.
FID-axis complement of class_fid_count.
Unweighted.  Empty -> {}.  Pure; no I/O.

Discriminating tests -- each kills a plausible wrong implementation:

  1. PRIMARY DISC.: returns FID->class_count (not class->fid_count).
     fid_a in [ClassA, ClassA, ClassB]: fid_class_count={"fid_a":2}.
     class_fid_count would give {"ClassA":1,"ClassB":1}.
     Kills impl reusing class_fid_count (wrong axis).
  2. Counts DISTINCT classes (not total occurrences).
     fid_x in ClassA 3 times -> {fid_x: 1}, not 3.
     Kills impl counting total problems instead of distinct classes.
  3. Cross-cutting fid appears in many classes -> high count.
     fid_z in [ClassA, ClassB, ClassC] -> {fid_z: 3}.
     Kills impl with off-by-one or wrong dedup.
  4. Each fid's class count is independent.
     fid_wide in [A,B,C], fid_narrow in [X] -> distinct values 3 and 1.
     Kills impl returning global class count for all fids.
  5. Empty -> {} (not raise).
     Kills impl without empty guard.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import Problem, fid_class_count


def _p(cls: str, fid: str, sev: str = "MED") -> Problem:
    return Problem(problem_class=cls, finding_id=fid, severity=sev)


def test_returns_fid_axis_class_count_not_class_axis() -> None:
    """PRIMARY DISC.: returns {fid: distinct_class_count} not {class: distinct_fid_count}.

    fid_a appears in ClassA (twice) and ClassB (once).
    fid_class_count = {"fid_a": 2} (2 distinct classes).
    class_fid_count would give {"ClassA": 1, "ClassB": 1}.
    Kills impl reusing class_fid_count (wrong axis).
    """
    problems = [
        _p("ClassA", "fid_a"),
        _p("ClassA", "fid_a"),  # same class twice
        _p("ClassB", "fid_a"),  # adds a second distinct class
    ]
    result = fid_class_count(problems)
    assert isinstance(result, dict), "Must return dict; got " + repr(type(result))
    assert set(result.keys()) == {"fid_a"}, f"Expected key fid_a only; got {set(result.keys())}"
    assert result["fid_a"] == 2, (
        f"fid_a in 2 distinct classes; got {result['fid_a']} "
        f"(class_fid_count would give {{ClassA:1,ClassB:1}} = wrong axis)"
    )


def test_counts_distinct_classes_not_occurrences() -> None:
    """Counts DISTINCT classes, not total problem occurrences.

    fid_x appears in ClassA 3 times -> distinct classes = 1.
    Kills impl counting total occurrences (returns 3).
    """
    problems = [
        _p("ClassA", "fid_x"),
        _p("ClassA", "fid_x"),
        _p("ClassA", "fid_x"),
    ]
    result = fid_class_count(problems)
    assert result["fid_x"] == 1, (
        f"fid_x in 1 distinct class (3 occurrences); got {result['fid_x']} "
        f"(3 = counting occurrences not distinct classes)"
    )


def test_cross_cutting_fid_shows_high_count() -> None:
    """Cross-cutting fid in many classes -> correct high count.

    fid_z in ClassA, ClassB, ClassC -> distinct classes = 3.
    Kills impl with off-by-one or wrong set dedup.
    """
    problems = [
        _p("ClassA", "fid_z"),
        _p("ClassB", "fid_z"),
        _p("ClassC", "fid_z"),
    ]
    result = fid_class_count(problems)
    assert result["fid_z"] == 3, f"fid_z in 3 distinct classes; got {result['fid_z']}"


def test_each_fid_has_independent_class_count() -> None:
    """Each fid's count is independent (not the global class count).

    fid_wide in [ClassA, ClassB, ClassC] -> 3; fid_narrow in [ClassX] -> 1.
    Kills impl returning global class count (4) for every fid.
    """
    problems = [
        _p("ClassA", "fid_wide"),
        _p("ClassB", "fid_wide"),
        _p("ClassC", "fid_wide"),
        _p("ClassX", "fid_narrow"),
    ]
    result = fid_class_count(problems)
    assert result["fid_wide"] == 3, f"fid_wide in 3 classes; got {result['fid_wide']}"
    assert result["fid_narrow"] == 1, (
        f"fid_narrow in 1 class; got {result['fid_narrow']} (3 = global class count is wrong)"
    )


def test_empty_returns_empty_dict() -> None:
    """Empty problems -> {} (not raise)."""
    result = fid_class_count([])
    assert result == {}, f"Empty -> {{}}; got {result}"
