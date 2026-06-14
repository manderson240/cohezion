"""Item 584: class_severity_histogram() — raw severity count histogram per class (2026-06-08).

``class_severity_histogram(problems) -> dict[str, dict[str, int]]``:
Returns the raw count of each severity label for every problem class.
{class: {severity: count}}.  Classes absent from problems are absent from result.
Empty problems -> {}.  Pure; no I/O.

Discriminating tests -- each kills a plausible wrong implementation:

  1. PRIMARY DISC.: inner dict keyed by SEVERITY labels (not class names).
     Class A with [HIGH, HIGH, LOW] -> {'A': {'HIGH': 2, 'LOW': 1}}.
     Kills impl accidentally keying inner dict by problem_class or finding_id.
  2. Count values are int (not float).
     Kills impl returning float counts (would break == comparisons).
  3. Class absent from problems is absent from result (not a KeyError on lookup).
     Kills impl pre-populating all classes or raising on missing class.
  4. Empty problems -> {} (not raise).
     Kills impl without empty guard.
  5. Multiple classes have independent histograms.
     Class A and B with disjoint severities: result[A] does not contain B's labels.
     Kills impl computing a flat aggregate dict across all classes.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import Problem, class_severity_histogram


def _p(cls: str, fid: str, sev: str) -> Problem:
    return Problem(problem_class=cls, finding_id=fid, severity=sev)


def test_inner_dict_keyed_by_severity_primary_discriminator() -> None:
    """PRIMARY DISC.: inner dict keyed by SEVERITY labels (not class or fid names).

    Class A has 2 HIGH + 1 LOW -> {'A': {'HIGH': 2, 'LOW': 1}}.
    Wrong impl keying by problem_class: {'A': {'A': 3}}.
    Wrong impl keying by finding_id: {'A': {'f1': 1, 'f2': 1, 'f3': 1}}.
    """
    problems = [
        _p("A", "f1", "HIGH"),
        _p("A", "f2", "HIGH"),
        _p("A", "f3", "LOW"),
    ]
    result = class_severity_histogram(problems)
    assert isinstance(result, dict), "Must return dict; got " + repr(type(result))
    assert "A" in result, f"Class 'A' must be in result; got {result}"
    inner = result["A"]
    assert isinstance(inner, dict), f"Inner value must be dict; got {type(inner)}"
    assert "HIGH" in inner, (
        f"Inner dict must be keyed by severity 'HIGH'; got {inner} (class-name key would show 'A')"
    )
    assert "LOW" in inner, f"Inner dict must contain 'LOW'; got {inner}"
    assert "A" not in inner, f"Inner dict must NOT be keyed by class name; got {inner}"
    assert inner["HIGH"] == 2, f"2 HIGH problems -> count=2; got {inner['HIGH']}"
    assert inner["LOW"] == 1, f"1 LOW problem -> count=1; got {inner['LOW']}"


def test_count_values_are_int() -> None:
    """Count values are int (not float).

    Kills impl returning float counts.
    """
    problems = [_p("A", "f1", "HIGH"), _p("A", "f2", "HIGH")]
    result = class_severity_histogram(problems)
    count = result["A"]["HIGH"]
    assert isinstance(count, int), f"Count must be int; got {type(count).__name__}"
    assert count == 2, f"2 HIGH -> count=2; got {count}"


def test_absent_class_not_in_result() -> None:
    """Class absent from problems is absent from result (not KeyError on lookup).

    Kills impl that pre-populates all possible classes.
    """
    problems = [_p("A", "f1", "HIGH")]
    result = class_severity_histogram(problems)
    assert "Z" not in result, (
        f"Class 'Z' absent from problems must not appear in result; got keys={list(result)}"
    )


def test_empty_returns_empty_dict() -> None:
    """Empty problems -> {} (not raise).

    Kills impl without empty guard.
    """
    result = class_severity_histogram([])
    assert result == {}, f"Empty -> {{}}; got {result}"


def test_multiple_classes_independent_histograms() -> None:
    """Multiple classes have independent histograms.

    A: [HIGH, LOW] -> {'HIGH': 1, 'LOW': 1}.
    B: [CRITICAL, CRITICAL] -> {'CRITICAL': 2}.
    result['A'] must not contain 'CRITICAL'; result['B'] must not contain 'LOW'.
    Kills impl computing a flat aggregate across all classes.
    """
    problems = [
        _p("A", "f1", "HIGH"),
        _p("A", "f2", "LOW"),
        _p("B", "f3", "CRITICAL"),
        _p("B", "f4", "CRITICAL"),
    ]
    result = class_severity_histogram(problems)
    assert result.get("A") == {"HIGH": 1, "LOW": 1}, f"A: {{HIGH:1, LOW:1}}; got {result.get('A')}"
    assert result.get("B") == {"CRITICAL": 2}, f"B: {{CRITICAL:2}}; got {result.get('B')}"
    assert "CRITICAL" not in result["A"], "A must not contain B's severity labels"
    assert "LOW" not in result["B"], "B must not contain A's severity labels"
