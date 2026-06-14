"""Item 586: classes_by_severity() -- group class names by dominant severity (2026-06-08).

``classes_by_severity(problems) -> dict[str, set[str]]``:
For each severity label that is the DOMINANT severity for at least one class,
returns the set of class names where that severity has the highest count.
Ties: a class with equal-count severities appears in ALL tied groups.
Empty -> {}.  Pure; no I/O.

Discriminating tests -- each kills a plausible wrong implementation:

  1. PRIMARY DISC.: keyed by SEVERITY (outer), values are sets of CLASS names.
     class A: HIGH x3, LOW x1 -> A is dominated by HIGH -> result['HIGH'] contains 'A'.
     Kills impl transposing inner/outer axes (returning {class: severity}).
  2. Dominance is by COUNT (most frequent severity for that class).
     A: HIGH x3, LOW x1 -> A in result['HIGH'] not result['LOW'].
     Kills impl grouping by first-seen or alphabetical severity.
  3. Ties: class in ALL tied severity groups.
     A: HIGH x2, LOW x2 -> A in result['HIGH'] AND result['LOW'].
     Kills impl picking only the first tied severity.
  4. Empty -> {} (not raise).
     Kills impl without empty guard.
  5. Returns dict[str, set[str]] (set of class names per severity, not list or count).
     Kills impl returning dict[str, list] or dict[str, int].
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import Problem, classes_by_severity


def _p(cls: str, fid: str, sev: str) -> Problem:
    return Problem(problem_class=cls, finding_id=fid, severity=sev)


def test_keyed_by_severity_primary_discriminator() -> None:
    """PRIMARY DISC.: outer keys are severity labels; values are sets of class names.

    Class A dominated by HIGH (3x vs LOW 1x) -> result['HIGH'] contains 'A'.
    Wrong impl would return {'A': 'HIGH'} (class as outer key).
    Kills impl with transposed axes.
    """
    problems = [
        _p("A", "f1", "HIGH"),  # A: HIGH x3
        _p("A", "f2", "HIGH"),
        _p("A", "f3", "HIGH"),
        _p("A", "f4", "LOW"),  # A: LOW x1
    ]
    result = classes_by_severity(problems)
    assert isinstance(result, dict), "Must return dict; got " + repr(type(result))
    assert "HIGH" in result, (
        f"Outer key must be severity 'HIGH'; got keys={list(result)} ('A' as key = axes transposed)"
    )
    assert "A" in result.get("HIGH", set()), (
        f"Class 'A' dominated by HIGH must be in result['HIGH']; got {result}"
    )
    assert "A" not in result.get("LOW", set()), (
        f"Class 'A' dominated by HIGH must NOT be in result['LOW']; got {result}"
    )


def test_dominance_by_count() -> None:
    """Dominance is by highest count per class.

    A: HIGH x3, LOW x1 -> HIGH dominates, A in result['HIGH'].
    B: LOW x5, HIGH x1 -> LOW dominates, B in result['LOW'].
    Kills impl using alphabetical or first-seen severity.
    """
    problems = [
        _p("A", "f1", "HIGH"),
        _p("A", "f2", "HIGH"),
        _p("A", "f3", "HIGH"),
        _p("A", "f4", "LOW"),
        _p("B", "g1", "LOW"),
        _p("B", "g2", "LOW"),
        _p("B", "g3", "LOW"),
        _p("B", "g4", "LOW"),
        _p("B", "g5", "LOW"),
        _p("B", "g6", "HIGH"),
    ]
    result = classes_by_severity(problems)
    assert "A" in result.get("HIGH", set()), f"A dominated by HIGH; got {result}"
    assert "A" not in result.get("LOW", set()), f"A not in LOW bucket; got {result}"
    assert "B" in result.get("LOW", set()), f"B dominated by LOW; got {result}"
    assert "B" not in result.get("HIGH", set()), f"B not in HIGH bucket; got {result}"


def test_tie_class_appears_in_all_tied_groups() -> None:
    """Tied severities: class appears in ALL tied severity groups.

    Class A: HIGH x2, LOW x2 -> tie -> A in result['HIGH'] AND result['LOW'].
    Kills impl that picks only the first or only one of the tied severities.
    """
    problems = [
        _p("A", "f1", "HIGH"),
        _p("A", "f2", "HIGH"),
        _p("A", "f3", "LOW"),
        _p("A", "f4", "LOW"),
    ]
    result = classes_by_severity(problems)
    assert "A" in result.get("HIGH", set()), f"Tied A must appear in result['HIGH']; got {result}"
    assert "A" in result.get("LOW", set()), f"Tied A must appear in result['LOW']; got {result}"


def test_empty_returns_empty_dict() -> None:
    """Empty problems -> {} (not raise).

    Kills impl without empty guard.
    """
    result = classes_by_severity([])
    assert result == {}, f"Empty -> {{}}; got {result}"


def test_values_are_sets_not_lists() -> None:
    """Values are set[str] (not list or count).

    Kills impl returning list or int instead of set.
    """
    problems = [
        _p("A", "f1", "HIGH"),
        _p("A", "f2", "HIGH"),
        _p("B", "f3", "HIGH"),
    ]
    result = classes_by_severity(problems)
    assert isinstance(result.get("HIGH"), set), (
        f"Values must be set; got {type(result.get('HIGH')).__name__}"
    )
    assert "A" in result["HIGH"] and "B" in result["HIGH"], (
        f"Both A and B dominated by HIGH; got {result['HIGH']}"
    )
