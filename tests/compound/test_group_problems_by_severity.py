"""Item 363: group_problems_by_severity() -- group problems by severity (2026-06-08).

group_problems_by_severity(problems) -> dict[str, list[Problem]]:
Returns dict mapping each distinct severity to its Problem records.
Unlabelled problems appear under key ''.
All problems covered.  Empty -> {}.  Pure; no I/O.

Discriminating tests:

  1. PRIMARY DISC.: unlabelled problems appear under key '' (not dropped).
     Kills impl dropping unlabelled problems.
  2. Values are lists of Problem objects, not finding_ids or counts.
     Kills impl building {severity: [finding_id]} or {severity: count}.
  3. All problems covered (sum of all lists == len(problems)).
     Kills impl covering only a subset.
  4. Empty input returns {}.
  5. Original order preserved within each severity group.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import (
    Problem,
    group_problems_by_severity,
)


def _ps(cls: str, idx: int, sev: str) -> Problem:
    return Problem(problem_class=cls, finding_id=f"{cls}:{idx}", severity=sev)


def _p(cls: str, idx: int) -> Problem:
    return Problem(problem_class=cls, finding_id=f"{cls}:{idx}")


def test_unlabelled_appear_under_empty_string_key() -> None:
    problems = [_ps("a", 0, "HIGH"), _p("b", 0)]
    result = group_problems_by_severity(problems)
    assert "" in result, f"Unlabelled under key ''; keys: {set(result.keys())}"
    assert result[""][0].finding_id == "b:0"


def test_values_are_problem_lists_not_ids() -> None:
    problems = [_ps("a", 0, "HIGH"), _ps("b", 0, "HIGH")]
    result = group_problems_by_severity(problems)
    assert isinstance(result["HIGH"][0], Problem), "Values must be Problem instances"


def test_all_problems_covered() -> None:
    problems = [_ps("a", 0, "HIGH"), _p("b", 0), _ps("c", 0, "LOW")]
    result = group_problems_by_severity(problems)
    total = sum(len(v) for v in result.values())
    assert total == len(problems), f"All {len(problems)} covered; got {total}"


def test_empty_returns_empty_dict() -> None:
    assert group_problems_by_severity([]) == {}


def test_order_preserved_within_group() -> None:
    problems = [
        _ps("a", 0, "HIGH"),
        _ps("b", 0, "LOW"),
        _ps("c", 0, "HIGH"),
        _ps("d", 0, "HIGH"),
    ]
    result = group_problems_by_severity(problems)
    high_ids = [p.finding_id for p in result["HIGH"]]
    assert high_ids == ["a:0", "c:0", "d:0"], f"Order preserved; got {high_ids}"
