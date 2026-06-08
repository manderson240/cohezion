"""Item 299: severity_escalation_classes() — classes where severity count increased cross-scan (2026-06-08).

``severity_escalation_classes(scan_a, scan_b, severity) -> frozenset[str]``:
Returns frozenset of class names where count of problems labelled with the
target severity is STRICTLY GREATER in scan_b than in scan_a.
Classes where count decreased or stayed the same are excluded.
Empty inputs or absent severity -> frozenset(). Pure; no I/O.

Discriminating tests -- each kills a plausible wrong implementation:

  1. PRIMARY DISC.: only classes with count_b > count_a are returned.
     Kills impl returning all classes or using count_b >= count_a.
  2. Class with decreased count NOT in result.
     Kills impl using count_a > count_b (wrong direction).
  3. Class with unchanged count NOT in result.
     Kills impl using >= instead of >.
  4. Empty scans -> frozenset().
     Kills impl raising on empty.
  5. Return type is frozenset[str].
     Kills impl returning list or set.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import (
    Problem,
    severity_escalation_classes,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _ps(cls: str, idx: int, sev: str) -> Problem:
    return Problem(problem_class=cls, finding_id=f"{cls}:{idx}", severity=sev)


def _p(cls: str, idx: int) -> Problem:
    return Problem(problem_class=cls, finding_id=f"{cls}:{idx}")


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_only_increased_count_classes_returned() -> None:
    """Only classes with strictly more problems at severity in scan_b are returned.

    PRIMARY DISCRIMINATOR: kills impl returning all classes or using >=.
    scan_a: alpha has 1 HIGH, beta has 2 HIGH.
    scan_b: alpha has 3 HIGH (increased), beta has 1 HIGH (decreased).
    -> severity_escalation_classes(scan_a, scan_b, 'HIGH') = frozenset({'alpha'})
    """
    scan_a = [
        _ps("alpha", 0, "HIGH"),
        _ps("beta", 0, "HIGH"),
        _ps("beta", 1, "HIGH"),
    ]
    scan_b = [
        _ps("alpha", 0, "HIGH"),
        _ps("alpha", 1, "HIGH"),
        _ps("alpha", 2, "HIGH"),
        _ps("beta", 0, "HIGH"),
    ]
    result = severity_escalation_classes(scan_a, scan_b, "HIGH")
    assert "alpha" in result, (
        "alpha: 1->3 HIGH (increased) -> in result; got " + repr(result)
    )
    assert "beta" not in result, (
        "beta: 2->1 HIGH (decreased) -> NOT in result; got " + repr(result)
    )


def test_decreased_count_class_not_in_result() -> None:
    """Class where count decreased is NOT in result.

    Kills impl using count_a > count_b (wrong direction).
    """
    scan_a = [_ps("alpha", 0, "HIGH"), _ps("alpha", 1, "HIGH")]
    scan_b = [_ps("alpha", 0, "HIGH")]
    result = severity_escalation_classes(scan_a, scan_b, "HIGH")
    assert "alpha" not in result, (
        "alpha: 2->1 HIGH (decreased) -> NOT in result; got " + repr(result)
    )


def test_unchanged_count_class_not_in_result() -> None:
    """Class with unchanged count NOT in result (strictly greater required).

    Kills impl using >= instead of >.
    """
    scan_a = [_ps("alpha", 0, "HIGH"), _ps("alpha", 1, "HIGH")]
    scan_b = [_ps("alpha", 0, "HIGH"), _ps("alpha", 1, "HIGH")]
    result = severity_escalation_classes(scan_a, scan_b, "HIGH")
    assert "alpha" not in result, (
        "alpha: 2->2 HIGH (unchanged) -> NOT in result; got " + repr(result)
    )


def test_empty_scans_return_empty_frozenset() -> None:
    """Empty scans -> frozenset().

    Kills impl raising on empty inputs.
    """
    result = severity_escalation_classes([], [], "HIGH")
    assert result == frozenset(), "Empty scans -> frozenset(); got " + repr(result)


def test_return_type_is_frozenset() -> None:
    """Return type is frozenset[str], not list or plain set.

    Kills impl returning a mutable set or list.
    """
    scan_a = []
    scan_b = [_ps("alpha", 0, "HIGH")]
    result = severity_escalation_classes(scan_a, scan_b, "HIGH")
    assert isinstance(result, frozenset), (
        "Must return frozenset; got " + repr(type(result))
    )
    assert "alpha" in result, (
        "alpha: 0->1 HIGH (new class) -> in result; got " + repr(result)
    )
