"""Item 434: class_severity_matrix() -- 2-D class × severity count matrix (2026-06-08).

``class_severity_matrix(problems) -> dict[str, dict[str, int]]``:
Returns {class: {severity: count}} for all distinct class/severity pairs.
Sparse: missing combinations are absent (not zero-filled).
Empty -> {}.  Pure; no I/O.

Discriminating tests -- each kills a plausible wrong implementation:

  1. PRIMARY DISC.: 2-D structure outer=class, inner=severity.
     Kills impl returning a flat dict[str, int] or 1-D histogram.
  2. Sparse matrix -- missing combinations absent, not zero-filled.
     Kills impl that fills all class × severity combos with 0.
  3. Inner counts correct -- multiple records of same class+sev counted.
     Validates the counting logic is not just presence check.
  4. Empty -> {} (not raise).
     Kills impl with unguarded access.
  5. Single problem -> {cls: {sev: 1}} (minimal non-empty case).
     Validates the structure for the degenerate case.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import (
    Problem,
    class_severity_matrix,
)


def _p(cls: str, fid: str, sev: str = "") -> Problem:
    return Problem(problem_class=cls, finding_id=fid, severity=sev)


def test_two_dimensional_structure() -> None:
    """PRIMARY DISC.: returns dict[str, dict[str, int]], not flat dict.

    Kills impl returning a flat histogram like severity_histogram.
    Outer key = class, inner key = severity.
    """
    problems = [
        _p("bug", "f1", "HIGH"),
        _p("bug", "f2", "LOW"),
        _p("perf", "f3", "HIGH"),
    ]
    result = class_severity_matrix(problems)
    assert isinstance(result, dict), "Must return dict; got " + repr(type(result))
    # Outer keys are classes
    assert set(result.keys()) == {"bug", "perf"}, "Outer keys = classes; got " + repr(
        set(result.keys())
    )
    # Inner values are dicts
    assert isinstance(result["bug"], dict), "Inner value must be dict; got " + repr(
        type(result["bug"])
    )
    # Correct inner key/value
    assert result["bug"]["HIGH"] == 1, "bug/HIGH=1; got " + repr(result["bug"].get("HIGH"))
    assert result["bug"]["LOW"] == 1, "bug/LOW=1; got " + repr(result["bug"].get("LOW"))
    assert result["perf"]["HIGH"] == 1, "perf/HIGH=1; got " + repr(result["perf"].get("HIGH"))


def test_sparse_missing_combinations_absent() -> None:
    """Sparse matrix: missing class+severity combos are absent (not 0-filled).

    'bug' has no 'LOW' problems, 'perf' has no 'HIGH' problems.
    Kills impl that zero-fills all combinations.
    """
    problems = [
        _p("bug", "f1", "HIGH"),
        _p("perf", "f2", "LOW"),
    ]
    result = class_severity_matrix(problems)
    assert "LOW" not in result.get("bug", {}), "bug/LOW absent (sparse); got " + repr(result)
    assert "HIGH" not in result.get("perf", {}), "perf/HIGH absent (sparse); got " + repr(result)


def test_counts_multiple_records_correctly() -> None:
    """Multiple records with same class+severity are counted (not just presence)."""
    problems = [
        _p("bug", "f1", "HIGH"),
        _p("bug", "f2", "HIGH"),
        _p("bug", "f3", "HIGH"),
    ]
    result = class_severity_matrix(problems)
    assert result["bug"]["HIGH"] == 3, "Three bug/HIGH records -> count=3; got " + repr(result)


def test_empty_returns_empty_dict() -> None:
    """Empty input returns {}, not raise."""
    result = class_severity_matrix([])
    assert result == {}, "Empty -> {}; got " + repr(result)
    assert isinstance(result, dict)


def test_single_problem_minimal_structure() -> None:
    """Single problem -> {cls: {sev: 1}}."""
    problems = [_p("bug", "f1", "CRITICAL")]
    result = class_severity_matrix(problems)
    assert result == {"bug": {"CRITICAL": 1}}, (
        "Single problem -> {bug: {CRITICAL: 1}}; got " + repr(result)
    )
