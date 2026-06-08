"""Item 556: class_max_severity_weight() -- heaviest single severity weight per class (2026-06-08).

``class_max_severity_weight(problems, weights) -> dict[str, float]``:
Returns {class: max single problem weight} for each class.
NOT the class total score -- the heaviest single problem in that class.
0.0 for unknown severity weights.  Empty -> {}.  Pure; no I/O.

Discriminating tests -- each kills a plausible wrong implementation:

  1. PRIMARY DISC.: max single weight (not class total).
     Class A: [HIGH=5, HIGH=5, LOW=1] -> max=5, total=11.
     Kills impl reusing class_total_severity_score (returns 11 not 5).
  2. Returns dict[str, float] (not float).
     Kills impl returning a scalar like class_score_max (returns single float).
  3. Different classes have independent maxima.
     Kills impl returning the global max for all classes.
  4. 0.0 for unknown severity (not KeyError).
     Kills impl using weights[p.severity] directly.
  5. Empty -> {} (not raise).
     Kills impl without empty guard.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import Problem, class_max_severity_weight


def _p(cls: str, fid: str, sev: str) -> Problem:
    return Problem(problem_class=cls, finding_id=fid, severity=sev)


def test_returns_max_not_class_total() -> None:
    """PRIMARY DISC.: max single weight, not class total.

    Class A: 2x HIGH(5.0) + 1x LOW(1.0) -> total=11.0, max=5.0.
    Kills impl reusing class_total_severity_score.
    """
    problems = [
        _p("A", "f1", "HIGH"),  # +5.0
        _p("A", "f2", "HIGH"),  # +5.0
        _p("A", "f3", "LOW"),  # +1.0  -- A total=11.0, max=5.0
    ]
    weights = {"HIGH": 5.0, "LOW": 1.0}
    result = class_max_severity_weight(problems, weights)
    assert isinstance(result, dict), "Must return dict; got " + repr(type(result))
    assert abs(result["A"] - 5.0) < 1e-9, (
        f"Class A max={5.0}, got {result['A']} (11.0 = total is wrong)"
    )


def test_returns_dict_not_float() -> None:
    """Returns dict[str, float], not a single float scalar.

    Kills impl reusing class_score_max (returns float not dict).
    """
    problems = [
        _p("X", "f1", "MED"),  # X max = 3.0
        _p("Y", "f2", "MED"),  # Y max = 3.0
    ]
    weights = {"MED": 3.0}
    result = class_max_severity_weight(problems, weights)
    assert isinstance(result, dict), "Must return dict; got " + repr(type(result))
    assert set(result.keys()) == {"X", "Y"}, f"Expected keys {{X,Y}}, got {set(result.keys())}"


def test_different_classes_have_independent_maxima() -> None:
    """Each class's max is independent (not the global max).

    Class A: HIGH=10.0 only; Class B: LOW=1.0 only.
    B's max must be 1.0, not 10.0 (the global max).
    Kills impl returning the global max for all classes.
    """
    problems = [
        _p("A", "f1", "HIGH"),  # A max = 10.0
        _p("B", "f2", "LOW"),  # B max = 1.0  (NOT 10.0 = global max)
    ]
    weights = {"HIGH": 10.0, "LOW": 1.0}
    result = class_max_severity_weight(problems, weights)
    assert abs(result["A"] - 10.0) < 1e-9, f"Class A max=10.0; got {result['A']}"
    assert abs(result["B"] - 1.0) < 1e-9, (
        f"Class B max=1.0; got {result['B']} (10.0 = global max is wrong)"
    )


def test_unknown_severity_defaults_to_zero() -> None:
    """Problems with unknown severity weight -> 0.0 (not KeyError).

    Kills impl using weights[p.severity] without .get().
    """
    problems = [
        _p("A", "f1", "UNKNOWN"),  # not in weights -> 0.0
        _p("A", "f2", "LOW"),  # 2.0 -> A max = 2.0
    ]
    weights = {"LOW": 2.0}
    result = class_max_severity_weight(problems, weights)
    assert abs(result["A"] - 2.0) < 1e-9, f"Class A max=2.0 (UNKNOWN=0.0); got {result['A']}"


def test_empty_returns_empty_dict() -> None:
    """Empty problems -> {} (not raise, not {class: 0.0})."""
    result = class_max_severity_weight([], {"HIGH": 5.0})
    assert result == {}, f"Empty -> {{}}; got {result}"
