"""Item 565: fid_score_fractions() -- weighted score fraction per fid (2026-06-08).

``fid_score_fractions(problems, weights) -> dict[str, float]``:
Returns {fid: fid_total / grand_total}.
FID-axis complement of class_score_fractions.
Values sum to 1.0.  Empty -> {}.  Zero-total -> all zeros.  Pure; no I/O.

Discriminating tests -- each kills a plausible wrong implementation:

  1. PRIMARY DISC.: weighted fraction (not problem count fraction).
     1 class, 3 fids [HIGH=5, MED=3, LOW=1]: total=9; fid fractions [5/9, 3/9, 1/9].
     Count fractions would be [1/3, 1/3, 1/3] (equal problems).
     Kills impl reusing fid_problem_fractions.
  2. FID axis (not class axis).
     1 class, 3 fids: class fraction = 1.0; fid fractions sum to 1.0 across 3 keys.
     Kills impl reusing class_score_fractions.
  3. Values sum to 1.0.
     Kills impl normalizing by number of fids instead of grand_total.
  4. Returns dict (not float).
     Kills impl returning a single fraction scalar.
  5. Empty -> {} (not raise).
     Kills impl without empty guard.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import Problem, fid_score_fractions


def _p(cls: str, fid: str, sev: str) -> Problem:
    return Problem(problem_class=cls, finding_id=fid, severity=sev)


def test_weighted_fraction_not_count_fraction() -> None:
    """PRIMARY DISC.: fractions weighted by severity, not by problem count.

    3 fids each with 1 problem but different severities [HIGH=5, MED=3, LOW=1]:
    weighted fractions: [5/9, 3/9, 1/9].
    Count fractions: [1/3, 1/3, 1/3] (uniform count).
    Kills impl reusing fid_problem_fractions.
    """
    problems = [
        _p("A", "fid_h", "HIGH"),  # fid_h total = 5.0 -> fraction = 5/9
        _p("A", "fid_m", "MED"),  # fid_m total = 3.0 -> fraction = 3/9
        _p("A", "fid_l", "LOW"),  # fid_l total = 1.0 -> fraction = 1/9
    ]
    weights = {"HIGH": 5.0, "MED": 3.0, "LOW": 1.0}
    result = fid_score_fractions(problems, weights)
    assert isinstance(result, dict), "Must return dict"
    assert abs(result["fid_h"] - 5 / 9) < 1e-9, (
        f"fid_h: 5/9={5 / 9:.4f}; got {result['fid_h']} (1/3 = count fraction is wrong)"
    )
    assert abs(result["fid_m"] - 3 / 9) < 1e-9, f"fid_m: 3/9; got {result['fid_m']}"
    assert abs(result["fid_l"] - 1 / 9) < 1e-9, f"fid_l: 1/9; got {result['fid_l']}"


def test_fid_axis_not_class_axis() -> None:
    """FID axis (not class axis).

    1 class, 2 fids: class fraction = 1.0; fid fractions split the score.
    Kills impl reusing class_score_fractions.
    """
    problems = [
        _p("SameClass", "fid_a", "HIGH"),  # fid_a = 5.0
        _p("SameClass", "fid_b", "LOW"),  # fid_b = 1.0, grand_total = 6.0
    ]
    weights = {"HIGH": 5.0, "LOW": 1.0}
    result = fid_score_fractions(problems, weights)
    assert set(result.keys()) == {"fid_a", "fid_b"}, (
        f"Expected keys fid_a, fid_b; got {set(result.keys())} (SameClass = class axis is wrong)"
    )
    assert abs(result["fid_a"] - 5 / 6) < 1e-9, f"fid_a: 5/6; got {result['fid_a']}"
    assert abs(result["fid_b"] - 1 / 6) < 1e-9, f"fid_b: 1/6; got {result['fid_b']}"


def test_values_sum_to_one() -> None:
    """Values sum to 1.0 (proper normalization by grand_total).

    Kills impl normalizing by number of fids.
    """
    problems = [
        _p("A", "f1", "HIGH"),  # 4.0
        _p("B", "f2", "MED"),  # 2.0
        _p("C", "f3", "LOW"),  # 1.0  grand_total=7.0
    ]
    weights = {"HIGH": 4.0, "MED": 2.0, "LOW": 1.0}
    result = fid_score_fractions(problems, weights)
    total = sum(result.values())
    assert abs(total - 1.0) < 1e-9, f"Fractions must sum to 1.0; got {total}"


def test_returns_dict_not_float() -> None:
    """Returns dict[str, float] (not a single float scalar).

    Kills impl returning class_score_fractions as a single value.
    """
    problems = [_p("A", "f1", "HIGH"), _p("B", "f2", "LOW")]
    weights = {"HIGH": 3.0, "LOW": 1.0}
    result = fid_score_fractions(problems, weights)
    assert isinstance(result, dict), "Must return dict; got " + repr(type(result))
    assert len(result) == 2, f"2 fids -> 2 keys; got {len(result)}"


def test_empty_returns_empty_dict() -> None:
    """Empty problems -> {} (not raise, not ZeroDivisionError)."""
    result = fid_score_fractions([], {"HIGH": 5.0})
    assert result == {}, f"Empty -> {{}}; got {result}"
