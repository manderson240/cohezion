"""Item 494: improving_classes() -- classes whose score decreased between snapshots (2026-06-08).

``improving_classes(before, after, weights) -> frozenset[str]``:
Returns frozenset of class names where score DECREASED (delta < 0) between
before and after.  Worsening (delta > 0) and stable (delta == 0) classes
are absent.  Empty both -> frozenset().  Pure; no I/O.

Discriminating tests -- each kills a plausible wrong implementation:

  1. PRIMARY DISC.: returns only IMPROVING classes (delta < 0).
     ClassA worsens, ClassB improves, ClassC stable -> only {'ClassB'}.
     Kills impl returning all-changed or confusing improving with regressing.
  2. Stable class (delta==0) is absent.
     Kills impl using <= (which would include stable classes).
  3. Worsening class (delta>0) is absent.
     Kills impl returning union of changed classes (both directions).
  4. Empty both -> frozenset() (not raise).
     Kills impl without empty guard.
  5. Class that disappears entirely from after is improving (score 0 < before score).
     Kills impl treating absent-in-after as missing (KeyError or stable).
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import (
    Problem,
    improving_classes,
)


def _p(cls: str, fid: str, sev: str) -> Problem:
    return Problem(problem_class=cls, finding_id=fid, severity=sev)


WEIGHTS = {"HIGH": 3.0, "LOW": 1.0}


def test_returns_only_improving_classes() -> None:
    """PRIMARY DISC.: only classes with score decrease (delta < 0) returned.

    ClassA worsens (1.0->6.0), ClassB improves (6.0->1.0), ClassC stable (3.0->3.0).
    -> frozenset({'ClassB'}).
    Kills impl returning all-changed or confusing improving with regressing.
    """
    before = [
        _p("ClassA", "f1", "LOW"),
        _p("ClassB", "f2", "HIGH"), _p("ClassB", "f3", "HIGH"),
        _p("ClassC", "f4", "HIGH"),
    ]
    after = [
        _p("ClassA", "f5", "HIGH"), _p("ClassA", "f6", "HIGH"),
        _p("ClassB", "f7", "LOW"),
        _p("ClassC", "f8", "HIGH"),
    ]
    result = improving_classes(before, after, WEIGHTS)
    assert isinstance(result, frozenset), "Must return frozenset; got " + repr(type(result))
    assert result == frozenset({"ClassB"}), (
        "Only ClassB improved; got " + repr(result)
    )


def test_stable_class_absent() -> None:
    """Class with delta==0 is not in result (strict < 0 only)."""
    before = [_p("Stable", "f1", "HIGH")]  # 3.0
    after  = [_p("Stable", "f2", "HIGH")]  # 3.0
    result = improving_classes(before, after, WEIGHTS)
    assert "Stable" not in result, "Stable (delta=0) absent; got " + repr(result)


def test_worsening_class_absent() -> None:
    """Worsening class (delta > 0) is not in result."""
    before = [_p("Bad", "f1", "LOW")]          # 1.0
    after  = [_p("Bad", "f2", "HIGH")]         # 3.0
    result = improving_classes(before, after, WEIGHTS)
    assert "Bad" not in result, "Worsening class absent; got " + repr(result)


def test_empty_both_returns_empty_frozenset() -> None:
    """Empty before + empty after -> frozenset() (not raise)."""
    result = improving_classes([], [], WEIGHTS)
    assert result == frozenset(), "Empty -> frozenset(); got " + repr(result)


def test_class_disappearing_from_after_is_improving() -> None:
    """Class that vanishes from after (score goes to 0) is improving."""
    before = [_p("Fixed", "f1", "HIGH"), _p("Fixed", "f2", "HIGH")]  # 6.0
    after  = [_p("Other", "f3", "LOW")]  # Fixed absent -> 0.0
    result = improving_classes(before, after, WEIGHTS)
    assert "Fixed" in result, "Fixed vanished from after: 6.0->0.0 = improving; got " + repr(result)
