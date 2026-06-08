"""Item 552: fid_problem_count() -- count of problems per fid (2026-06-08).

``fid_problem_count(problems) -> dict[str, int]``:
Returns {fid: count} mapping; unweighted raw occurrence count.
Empty dict for empty input.  Pure; no I/O.

Discriminating tests -- each kills a plausible wrong implementation:

  1. PRIMARY DISC.: keyed on FID axis (not class axis).
     One class with 3 distinct fids -> class_problem_count = {"SameClass": 3},
     fid_problem_count = {"fid_a": 1, "fid_b": 1, "fid_c": 1}.
     Kills impl reusing class_problem_count (returns wrong key).
  2. Returns dict[str, int] not float.
     Kills impl returning a single float or float-valued dict.
  3. Multiple problems on same fid accumulate in count.
     Kills impl counting fids instead of problems.
  4. Empty -> empty dict (not 0.0).
     Kills impl without empty guard.
  5. Severity is ignored -- unweighted.
     Kills impl accidentally using weights.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import Problem, fid_problem_count


def _p(cls: str, fid: str, sev: str) -> Problem:
    return Problem(problem_class=cls, finding_id=fid, severity=sev)


def test_returns_fid_axis_counts_not_class_axis() -> None:
    """PRIMARY DISC.: keyed on fid axis, not class axis.

    One class, 3 distinct fids (each once):
      class_problem_count = {"SameClass": 3}
      fid_problem_count = {"fid_a": 1, "fid_b": 1, "fid_c": 1}
    Kills impl reusing class_problem_count (key="SameClass" not fid names).
    """
    problems = [
        _p("SameClass", "fid_a", "HIGH"),
        _p("SameClass", "fid_b", "MED"),
        _p("SameClass", "fid_c", "LOW"),
    ]
    result = fid_problem_count(problems)
    assert isinstance(result, dict), "Must return dict"
    assert result == {"fid_a": 1, "fid_b": 1, "fid_c": 1}, (
        f"Expected per-fid counts; got {result} ({{'SameClass': 3}} = class axis is wrong)"
    )


def test_returns_int_counts_not_float() -> None:
    """Returns dict[str, int], not dict[str, float].

    Kills impl returning weighted float scores.
    """
    problems = [_p("A", "f1", "HIGH"), _p("B", "f1", "LOW")]
    result = fid_problem_count(problems)
    assert result == {"f1": 2}, f"f1 has 2 problems; got {result}"
    assert isinstance(result.get("f1"), int), f"Count must be int; got {type(result.get('f1'))}"


def test_same_fid_different_classes_accumulates() -> None:
    """Same fid from different classes all count.

    fid_x appears in class A, B, C -> count = 3.
    Kills impl that only counts per-class occurrences.
    """
    problems = [
        _p("A", "fid_x", "HIGH"),
        _p("B", "fid_x", "MED"),
        _p("C", "fid_x", "LOW"),
        _p("D", "fid_y", "HIGH"),
    ]
    result = fid_problem_count(problems)
    assert result == {"fid_x": 3, "fid_y": 1}, f"fid_x=3, fid_y=1; got {result}"


def test_empty_returns_empty_dict() -> None:
    """Empty problems -> empty dict (not 0.0, not raise)."""
    result = fid_problem_count([])
    assert result == {}, f"Empty -> {{}}; got {result}"


def test_severity_ignored_unweighted() -> None:
    """Severity is ignored; count is unweighted.

    HIGH and LOW both count as 1.
    Kills impl that multiplies count by severity weight.
    """
    problems = [
        _p("A", "fid_high", "HIGH"),  # count = 1, not 5
        _p("A", "fid_low", "LOW"),  # count = 1, not 1
    ]
    result = fid_problem_count(problems)
    assert result == {"fid_high": 1, "fid_low": 1}, f"Unweighted counts [1,1]; got {result}"
