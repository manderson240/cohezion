"""Item 522: normalized_class_scores() -- min-max normalized class scores (2026-06-08).

``normalized_class_scores(problems, weights) -> dict[str, float]``:
Returns {class: (score-min)/(max-min)} for each class; values in [0.0, 1.0].
Zero-spread (all classes tied or single class) -> all 0.0.  Empty -> {}.
Pure; no I/O.

Discriminating tests -- each kills a plausible wrong implementation:

  1. PRIMARY DISC.: max class maps to 1.0 and min class maps to 0.0.
     Kills impl returning raw weighted scores (not normalized).
  2. Intermediate class maps to a value strictly between 0.0 and 1.0.
     Kills impl that only normalizes min and max but clamps others.
  3. Zero-spread (all classes tied) -> all 0.0 (no ZeroDivisionError).
     Kills impl that divides (score-min) by zero when max==min.
  4. Single class -> {class: 0.0} (degenerate: no spread).
     Kills impl that raises on a single-element set.
  5. Empty input -> {} (not raise).
     Kills impl without empty guard.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import Problem, normalized_class_scores


def _p(cls: str, fid: str, sev: str) -> Problem:
    return Problem(problem_class=cls, finding_id=fid, severity=sev)


def test_max_maps_to_one_min_maps_to_zero() -> None:
    """PRIMARY DISC.: highest raw score -> 1.0, lowest -> 0.0.

    Kills impl returning raw scores (weighted_problem_count_by_class values).
    """
    problems = [
        _p("A", "f1", "HIGH"),  # 5.0
        _p("B", "f2", "LOW"),   # 1.0
    ]
    weights = {"HIGH": 5.0, "LOW": 1.0}
    result = normalized_class_scores(problems, weights)
    assert isinstance(result, dict), "Must return dict; got " + repr(type(result))
    assert abs(result["A"] - 1.0) < 1e-9, f"A (max) -> 1.0; got {result['A']}"
    assert abs(result["B"] - 0.0) < 1e-9, f"B (min) -> 0.0; got {result['B']}"


def test_intermediate_class_maps_between_zero_and_one() -> None:
    """Intermediate class maps to a value strictly between 0.0 and 1.0.

    Three classes: A=1.0 (min), B=3.0 (mid), C=5.0 (max).
    B should map to (3.0-1.0)/(5.0-1.0) = 0.5.
    Kills impl that only handles min/max but not intermediate values.
    """
    problems = [
        _p("A", "f1", "LOW"),   # 1.0
        _p("B", "f2", "MED"),   # 3.0
        _p("C", "f3", "HIGH"),  # 5.0
    ]
    weights = {"LOW": 1.0, "MED": 3.0, "HIGH": 5.0}
    result = normalized_class_scores(problems, weights)
    assert abs(result["A"] - 0.0) < 1e-9, f"A -> 0.0; got {result['A']}"
    assert abs(result["B"] - 0.5) < 1e-9, f"B -> 0.5; got {result['B']}"
    assert abs(result["C"] - 1.0) < 1e-9, f"C -> 1.0; got {result['C']}"


def test_zero_spread_returns_all_zero() -> None:
    """All classes tied -> all 0.0 (no ZeroDivisionError from max-min=0).

    Kills impl that computes (score-min)/(max-min) without guarding max==min.
    """
    problems = [
        _p("A", "f1", "MED"),
        _p("B", "f2", "MED"),
        _p("C", "f3", "MED"),
    ]
    result = normalized_class_scores(problems, {"MED": 2.0})
    assert result == {"A": 0.0, "B": 0.0, "C": 0.0}, (
        "Zero-spread -> all 0.0; got " + repr(result)
    )


def test_single_class_returns_zero() -> None:
    """Single class -> {class: 0.0} (degenerate zero-spread).

    Kills impl raising ZeroDivisionError or returning non-zero for one class.
    """
    problems = [_p("A", "f1", "HIGH"), _p("A", "f2", "HIGH")]
    result = normalized_class_scores(problems, {"HIGH": 5.0})
    assert result == {"A": 0.0}, f"Single class -> {{'A': 0.0}}; got {result}"


def test_empty_input_returns_empty_dict() -> None:
    """Empty input -> {} (not raise)."""
    result = normalized_class_scores([], {"HIGH": 5.0})
    assert result == {}, f"Empty -> {{}}; got {result}"
