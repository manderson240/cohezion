"""Item 513: classes_tied_at_score() -- frozenset of classes at exact target score (2026-06-08).

``classes_tied_at_score(problems, weights, target_score) -> frozenset[str]``:
Returns a frozenset of class names whose total weighted severity score equals
exactly ``target_score`` (float equality).  Empty input -> frozenset().
Pure; no I/O.

Discriminating tests -- each kills a plausible wrong implementation:

  1. PRIMARY DISC.: returns FROZENSET (not list, not set, not dict).
     Kills impl returning a sorted list or dict.
  2. Empty input -> frozenset() (not raise, not None).
     Kills impl calling min/max on empty.
  3. No class at target -> frozenset() (not raise, not None).
     Kills impl returning all classes when nothing matches.
  4. Multiple classes tied at target -> all of them in frozenset.
     Kills impl returning only the first match.
  5. Only exact-match classes included (not nearby scores).
     Kills impl using range [target-eps, target+eps] instead of equality.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import (
    Problem,
    classes_tied_at_score,
)


def _p(cls: str, fid: str, sev: str) -> Problem:
    return Problem(problem_class=cls, finding_id=fid, severity=sev)


def test_returns_frozenset_type() -> None:
    """PRIMARY DISC.: returns frozenset, not list or set.

    Kills impl returning sorted(matched_classes) (list).
    """
    problems = [_p("A", "f1", "HIGH")]
    result = classes_tied_at_score(problems, {"HIGH": 5.0}, 5.0)
    assert isinstance(result, frozenset), "Must return frozenset; got " + repr(type(result))
    assert result == frozenset({"A"}), "A scored 5.0 == target 5.0; got " + repr(result)


def test_empty_input_returns_frozenset() -> None:
    """Empty input -> frozenset() (not raise, not None).

    Kills impl calling any aggregation on empty sequence without guard.
    """
    result = classes_tied_at_score([], {"HIGH": 3.0}, 3.0)
    assert isinstance(result, frozenset), "Empty -> frozenset; got " + repr(type(result))
    assert result == frozenset(), "Empty input -> empty frozenset; got " + repr(result)


def test_no_match_returns_empty_frozenset() -> None:
    """No class at target score -> frozenset() (not raise, not None).

    ClassA=5.0, ClassB=1.0; target=3.0 -> frozenset().
    Kills impl returning all classes or the closest class.
    """
    problems = [
        _p("ClassA", "f1", "HIGH"),   # 5.0
        _p("ClassB", "f2", "LOW"),    # 1.0
    ]
    result = classes_tied_at_score(problems, {"HIGH": 5.0, "LOW": 1.0}, 3.0)
    assert result == frozenset(), "No class at 3.0 -> frozenset(); got " + repr(result)


def test_multiple_tied_classes_all_returned() -> None:
    """Multiple classes at same target score -> all included.

    ClassA=3.0, ClassB=3.0, ClassC=5.0; target=3.0 -> {ClassA, ClassB}.
    Kills impl returning only first-seen match.
    """
    problems = [
        _p("ClassA", "f1", "MED"),    # 3.0
        _p("ClassB", "f2", "MED"),    # 3.0
        _p("ClassC", "f3", "HIGH"),   # 5.0
    ]
    result = classes_tied_at_score(problems, {"HIGH": 5.0, "MED": 3.0}, 3.0)
    assert result == frozenset({"ClassA", "ClassB"}), (
        "ClassA and ClassB both at 3.0; got " + repr(result)
    )
    assert "ClassC" not in result, "ClassC=5.0 must not appear"


def test_only_exact_match_no_nearby() -> None:
    """Exact float equality only; nearby-but-not-equal scores excluded.

    ClassA: LOW(1.0)+LOW(1.0)=2.0; ClassB: MED(2.0)=2.0; ClassC: HIGH(3.0)=3.0.
    target=2.0 -> {ClassA, ClassB}. ClassC (3.0) must be excluded.
    Also verifies multi-record accumulation.
    Kills impl using approximate equality or range query.
    """
    problems = [
        _p("ClassA", "f1", "LOW"),    # +1.0
        _p("ClassA", "f2", "LOW"),    # +1.0 -> total 2.0
        _p("ClassB", "f3", "MED"),    # 2.0
        _p("ClassC", "f4", "HIGH"),   # 3.0
    ]
    result = classes_tied_at_score(problems, {"HIGH": 3.0, "MED": 2.0, "LOW": 1.0}, 2.0)
    assert result == frozenset({"ClassA", "ClassB"}), (
        "ClassA=2.0 and ClassB=2.0 match; ClassC=3.0 excluded; got " + repr(result)
    )
    assert "ClassC" not in result, "ClassC=3.0 != 2.0; must not appear"
