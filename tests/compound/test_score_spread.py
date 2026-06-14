"""Item 509: score_spread() -- max minus min total class score (2026-06-08).

``score_spread(problems, weights) -> float``:
Returns max(class_totals) - min(class_totals).
0.0 for empty input.  0.0 for single class.  0.0 when all classes tie.
Pure; no I/O.

Discriminating tests -- each kills a plausible wrong implementation:

  1. PRIMARY DISC.: returns FLOAT spread, not a frozenset or dict.
     Kills impl returning classes_in_score_band or weighted_problem_count_by_class.
  2. 0.0 for empty (not raise).
     Kills impl calling max/min on empty sequence without guard.
  3. 0.0 for single class (not raise, not None).
     Kills impl requiring >= 2 classes.
  4. 0.0 when all classes tie (max == min -> spread == 0.0).
     Kills impl returning non-zero when all scores equal.
  5. Correct spread: max - min (not max alone, not min alone).
     Kills impl returning max or min of the total-score dict.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import (
    Problem,
    score_spread,
)


def _p(cls: str, fid: str, sev: str) -> Problem:
    return Problem(problem_class=cls, finding_id=fid, severity=sev)


def test_returns_float_spread() -> None:
    """PRIMARY DISC.: returns float spread (max - min), not frozenset or dict.

    ClassA=5.0, ClassB=1.0 -> spread = 4.0.
    Kills impl returning weighted_problem_count_by_class (dict) or a set.
    """
    problems = [
        _p("ClassA", "f1", "HIGH"),  # 5.0
        _p("ClassB", "f2", "LOW"),  # 1.0
    ]
    result = score_spread(problems, {"HIGH": 5.0, "LOW": 1.0})
    assert isinstance(result, float), "Must return float; got " + repr(type(result))
    assert result == 4.0, "5.0 - 1.0 = 4.0; got " + repr(result)


def test_empty_input_returns_zero() -> None:
    """Empty input -> 0.0 (not raise).

    Kills impl calling max([]) which raises ValueError.
    """
    result = score_spread([], {"HIGH": 3.0})
    assert result == 0.0, "Empty -> 0.0; got " + repr(result)
    assert isinstance(result, float), "Must be float; got " + repr(type(result))


def test_single_class_returns_zero() -> None:
    """Single class -> 0.0 (not raise, not None).

    Kills impl requiring >= 2 classes before computing.
    """
    problems = [_p("Only", "f1", "HIGH"), _p("Only", "f2", "LOW")]
    result = score_spread(problems, {"HIGH": 5.0, "LOW": 1.0})
    assert result == 0.0, "Single class -> spread=0.0; got " + repr(result)


def test_all_classes_tie_returns_zero() -> None:
    """All classes at same total score -> 0.0.

    Kills impl that returns max total instead of max - min.
    """
    problems = [
        _p("A", "f1", "HIGH"),  # 3.0
        _p("B", "f2", "HIGH"),  # 3.0
        _p("C", "f3", "HIGH"),  # 3.0
    ]
    result = score_spread(problems, {"HIGH": 3.0})
    assert result == 0.0, "All tied -> spread=0.0; got " + repr(result)


def test_correct_spread_max_minus_min() -> None:
    """Spread = max total - min total (not max alone, not sum).

    ClassA=6.0, ClassB=4.0, ClassC=1.0 -> spread = 6.0 - 1.0 = 5.0.
    Kills impl returning max (6.0) or min (1.0) alone.
    """
    problems = [
        _p("A", "f1", "HIGH"),  # 6.0
        _p("A", "f2", "MED"),  # accumulates: 6+2=8? No — different records, same class
        _p("B", "f3", "HIGH"),  # class B = 4.0
        _p("C", "f4", "LOW"),  # class C = 1.0
    ]
    # ClassA: HIGH(6.0) + MED(2.0) = 8.0; ClassB = 4.0; ClassC = 1.0
    # spread = 8.0 - 1.0 = 7.0
    result = score_spread(problems, {"HIGH": 6.0, "MED": 2.0, "LOW": 1.0})
    assert result == 7.0, "8.0 - 1.0 = 7.0; got " + repr(result)
