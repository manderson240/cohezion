"""Item 300: severity_improvement_classes() — classes where severity improved between scans (2026-06-08).

``severity_improvement_classes(scan_a, scan_b, severity) -> frozenset[str]``:
Returns frozenset of class names where count_b(cls, severity) < count_a(cls, severity).
Class disappearing entirely (count_b=0, count_a>0) IS included.
Empty scans -> frozenset().  Pure; no I/O.

Discriminating tests — each kills a plausible wrong implementation:

  1. PRIMARY DISC.: only classes where count STRICTLY DECREASED are included.
     Kills impl using <= (unchanged classes incorrectly included).
  2. Class where count increased is NOT in result.
     Kills impl returning all classes with nonzero count in scan_a.
  3. Class disappearing completely (count_b=0, count_a>0) IS in result.
     Kills impl requiring count_b > 0 (strict positive condition on b-side).
  4. Empty scans -> frozenset().
     Kills impl raising on empty.
  5. Return type is frozenset[str].
     Kills impl returning list or set.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import (
    Problem,
    severity_improvement_classes,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _ps(cls: str, idx: int, sev: str) -> Problem:
    return Problem(problem_class=cls, finding_id=f"{cls}:{idx}", severity=sev)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_only_decreased_classes_included() -> None:
    """Only classes with STRICTLY decreased count are in result.

    PRIMARY DISCRIMINATOR: kills impl using <= (including unchanged classes).
    scan_a: alpha=2 CRITICAL, beta=1 CRITICAL, gamma=1 CRITICAL.
    scan_b: alpha=1 CRITICAL (decreased), beta=1 CRITICAL (unchanged), gamma=2 CRITICAL (increased).
    Only alpha improved -> result = {'alpha'}.
    """
    scan_a = [
        _ps("alpha", 0, "CRITICAL"),
        _ps("alpha", 1, "CRITICAL"),
        _ps("beta", 2, "CRITICAL"),
        _ps("gamma", 3, "CRITICAL"),
    ]
    scan_b = [
        _ps("alpha", 0, "CRITICAL"),  # alpha: 1 (decreased from 2)
        _ps("beta", 2, "CRITICAL"),  # beta: 1 (unchanged)
        _ps("gamma", 3, "CRITICAL"),
        _ps("gamma", 4, "CRITICAL"),  # gamma: 2 (increased from 1)
    ]
    result = severity_improvement_classes(scan_a, scan_b, "CRITICAL")
    assert result == frozenset({"alpha"}), "Only alpha improved (2->1 CRITICAL); got " + repr(
        result
    )


def test_increased_class_not_in_result() -> None:
    """Class where count increased is NOT in result.

    Kills impl returning all classes with nonzero count in scan_a.
    alpha goes from 1 to 2 CRITICAL -> NOT an improvement.
    """
    scan_a = [_ps("alpha", 0, "CRITICAL")]
    scan_b = [_ps("alpha", 0, "CRITICAL"), _ps("alpha", 1, "CRITICAL")]
    result = severity_improvement_classes(scan_a, scan_b, "CRITICAL")
    assert "alpha" not in result, "alpha increased -> NOT in result; got " + repr(result)
    assert result == frozenset(), "No classes improved; got " + repr(result)


def test_disappearing_class_is_improvement() -> None:
    """Class dropping from count>0 to 0 at given severity IS in result.

    Kills impl requiring count_b > 0 (strict positive condition on b-side).
    alpha has 2 CRITICAL in scan_a; 0 in scan_b -> count_b < count_a -> improvement.
    """
    scan_a = [_ps("alpha", 0, "CRITICAL"), _ps("alpha", 1, "CRITICAL")]
    scan_b = []  # alpha has 0 CRITICAL in scan_b
    result = severity_improvement_classes(scan_a, scan_b, "CRITICAL")
    assert "alpha" in result, "alpha went from 2 to 0 CRITICAL -> improvement; got " + repr(result)


def test_empty_scans_return_empty_frozenset() -> None:
    """Empty scans -> frozenset() without raising.

    Kills impl raising on empty lists.
    """
    assert severity_improvement_classes([], [], "CRITICAL") == frozenset(), (
        "Both empty -> frozenset()"
    )
    assert (
        severity_improvement_classes([], [_ps("alpha", 0, "CRITICAL")], "CRITICAL") == frozenset()
    ), "Empty scan_a -> no improvement possible"


def test_return_type_is_frozenset() -> None:
    """Return type is frozenset[str].

    Kills impl returning mutable set or list.
    """
    scan_a = [_ps("alpha", 0, "HIGH"), _ps("alpha", 1, "HIGH")]
    scan_b = [_ps("alpha", 0, "HIGH")]
    result = severity_improvement_classes(scan_a, scan_b, "HIGH")
    assert isinstance(result, frozenset), "Must return frozenset; got " + repr(type(result))
    assert "alpha" in result, "alpha improved (2->1 HIGH); got " + repr(result)
