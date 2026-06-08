"""Item 493: regressing_classes() -- classes whose score worsened between snapshots (2026-06-08).

``regressing_classes(before, after, weights) -> frozenset[str]``:
Returns frozenset of class names where score INCREASED (delta > 0) between
before and after.  Improving (delta < 0) and stable (delta == 0) classes
are absent.  Empty both -> frozenset().  Pure; no I/O.

Discriminating tests -- each kills a plausible wrong implementation:

  1. PRIMARY DISC.: returns only WORSENING classes (delta > 0).
     ClassA worsens, ClassB improves, ClassC stable -> only {'ClassA'}.
     Kills impl returning all-changed classes (includes improving/stable).
  2. Stable class (delta==0) is absent.
     Kills impl using >= (which would include stable classes).
  3. Improving class (delta<0) is absent.
     Kills impl returning abs(delta) > 0 (confusing worsening with improving).
  4. Empty both -> frozenset() (not raise).
     Kills impl without empty guard.
  5. New class appearing in after only -> in result (score went from 0 -> positive).
     Kills impl treating absent-in-before as already-counted-as-stable.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import (
    Problem,
    regressing_classes,
)


def _p(cls: str, fid: str, sev: str) -> Problem:
    return Problem(problem_class=cls, finding_id=fid, severity=sev)


WEIGHTS = {"HIGH": 3.0, "LOW": 1.0}


def test_returns_only_worsening_classes() -> None:
    """PRIMARY DISC.: only classes with score increase (delta > 0) are returned.

    ClassA worsens (1.0->6.0), ClassB improves (6.0->1.0), ClassC stable (3.0->3.0).
    -> frozenset({'ClassA'}).
    Kills impl returning all-changed or including improving/stable.
    """
    before = [
        _p("ClassA", "f1", "LOW"),           # ClassA before = 1.0
        _p("ClassB", "f2", "HIGH"),           # ClassB before = 6.0
        _p("ClassB", "f3", "HIGH"),
        _p("ClassC", "f4", "HIGH"),           # ClassC before = 3.0
    ]
    after = [
        _p("ClassA", "f5", "HIGH"),           # ClassA after = 6.0 (worsened)
        _p("ClassA", "f6", "HIGH"),
        _p("ClassB", "f7", "LOW"),            # ClassB after = 1.0 (improved)
        _p("ClassC", "f8", "HIGH"),           # ClassC after = 3.0 (stable)
    ]
    result = regressing_classes(before, after, WEIGHTS)
    assert isinstance(result, frozenset), "Must return frozenset; got " + repr(type(result))
    assert result == frozenset({"ClassA"}), (
        "Only ClassA worsened; got " + repr(result)
    )


def test_stable_class_absent() -> None:
    """Class with delta==0 is not in result (strict > 0 only)."""
    before = [_p("Stable", "f1", "HIGH")]   # score=3.0
    after  = [_p("Stable", "f2", "HIGH")]   # score=3.0
    result = regressing_classes(before, after, WEIGHTS)
    assert "Stable" not in result, "Stable class (delta=0) must be absent; got " + repr(result)


def test_improving_class_absent() -> None:
    """Improving class (delta < 0) is not in result."""
    before = [_p("Good", "f1", "HIGH"), _p("Good", "f2", "HIGH")]  # score=6.0
    after  = [_p("Good", "f3", "LOW")]  # score=1.0
    result = regressing_classes(before, after, WEIGHTS)
    assert "Good" not in result, "Improving class must be absent; got " + repr(result)


def test_empty_both_returns_empty_frozenset() -> None:
    """Empty before + empty after -> frozenset() (not raise)."""
    result = regressing_classes([], [], WEIGHTS)
    assert result == frozenset(), "Empty -> frozenset(); got " + repr(result)


def test_new_class_in_after_only_is_regressing() -> None:
    """New class that appears only in after is regressing (0.0 -> positive score)."""
    before = [_p("OldClass", "f1", "HIGH")]
    after  = [_p("OldClass", "f1", "HIGH"), _p("NewBad", "f2", "HIGH")]
    result = regressing_classes(before, after, WEIGHTS)
    assert "NewBad" in result, "New class with positive score is regressing; got " + repr(result)
