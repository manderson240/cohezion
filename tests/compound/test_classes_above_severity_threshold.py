"""Item 310: classes_above_severity_threshold() — classes with n+ problems at/above threshold (2026-06-08).

``classes_above_severity_threshold(problems, severity_order, threshold, n=1) -> frozenset[str]``:
Returns the frozenset of class names with at least n problems at or above the
threshold severity in severity_order.  "At or above" means the threshold rank
and all MORE-severe ranks (lower index in severity_order).
n=0 -> frozenset of ALL classes.  Empty -> frozenset().  Pure; no I/O.

Discriminating tests — each kills a plausible wrong implementation:

  1. PRIMARY DISC.: "at or above" includes threshold AND all more-severe ranks.
     Kills impl counting only the exact threshold severity.
  2. n=0 -> frozenset of ALL classes (even if they have 0 qualifying problems).
     Kills impl treating n=0 like n=1.
  3. Class with fewer than n qualifying problems NOT in result.
     Kills impl ignoring the minimum count requirement.
  4. Class absent from problems -> NOT in result.
     Kills impl fabricating classes not in the input.
  5. Return type is frozenset[str].
     Kills impl returning list or set instead of frozenset.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import (
    Problem,
    classes_above_severity_threshold,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _p(cls: str, sev: str, idx: int) -> Problem:
    return Problem(problem_class=cls, finding_id=f"{cls}:{sev}:{idx}", severity=sev)


def _pu(cls: str, idx: int) -> Problem:
    """Unlabelled problem."""
    return Problem(problem_class=cls, finding_id=f"{cls}:u:{idx}")


SEV_ORDER = ["CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO"]


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_at_or_above_includes_threshold_and_more_severe() -> None:
    """'At or above' threshold includes threshold rank AND all more severe.

    PRIMARY DISCRIMINATOR: kills impl counting only the exact threshold.
    threshold=HIGH (rank=1): includes CRITICAL (rank=0) AND HIGH (rank=1).
    alpha: 1 CRITICAL (above HIGH) -> counts.
    beta: 1 HIGH (at threshold) -> counts.
    gamma: 1 MEDIUM (below threshold) -> does NOT count.
    """
    problems = [
        _p("alpha", "CRITICAL", 0),  # above HIGH threshold
        _p("beta", "HIGH", 0),       # at HIGH threshold
        _p("gamma", "MEDIUM", 0),    # below HIGH threshold
    ]
    result = classes_above_severity_threshold(problems, SEV_ORDER, "HIGH")
    assert "alpha" in result, "alpha CRITICAL (above HIGH) -> included; got " + repr(result)
    assert "beta" in result, "beta HIGH (at threshold) -> included; got " + repr(result)
    assert "gamma" not in result, "gamma MEDIUM (below HIGH) -> excluded; got " + repr(result)


def test_n_zero_returns_all_classes() -> None:
    """n=0 -> frozenset of ALL classes regardless of qualifying problem count.

    Kills impl treating n=0 like n=1 (requiring at least 1 qualifying problem).
    delta_cls has only LOW problems (below HIGH threshold).
    With n=0, still included because minimum is 0.
    """
    problems = [
        _p("delta_cls", "LOW", 0),  # below HIGH threshold; n=0 still includes
        _p("epsilon_cls", "HIGH", 0),
    ]
    result = classes_above_severity_threshold(problems, SEV_ORDER, "HIGH", n=0)
    assert "delta_cls" in result, (
        "n=0 -> all classes included; delta_cls should be in result; got " + repr(result)
    )
    assert "epsilon_cls" in result, "epsilon_cls in result with n=0; got " + repr(result)


def test_class_with_fewer_than_n_qualifying_problems_excluded() -> None:
    """Class with fewer than n qualifying problems is NOT in result.

    Kills impl ignoring the minimum count requirement.
    zeta: 1 CRITICAL, threshold=HIGH, n=2 -> only 1 qualifies -> excluded.
    eta: 2 CRITICAL, threshold=HIGH, n=2 -> 2 qualify -> included.
    """
    problems = [
        _p("zeta", "CRITICAL", 0),           # only 1 qualifying
        _p("eta", "CRITICAL", 0), _p("eta", "CRITICAL", 1),  # 2 qualifying
    ]
    result = classes_above_severity_threshold(problems, SEV_ORDER, "HIGH", n=2)
    assert "zeta" not in result, "zeta: 1 qualifying < n=2 -> excluded; got " + repr(result)
    assert "eta" in result, "eta: 2 qualifying >= n=2 -> included; got " + repr(result)


def test_empty_input_returns_empty_frozenset() -> None:
    """Empty problems -> frozenset().

    Kills impl that crashes or returns non-empty.
    """
    result = classes_above_severity_threshold([], SEV_ORDER, "HIGH")
    assert result == frozenset(), "empty -> frozenset(); got " + repr(result)


def test_return_type_is_frozenset() -> None:
    """Return type is frozenset[str], not list or set.

    Kills impl returning the wrong collection type.
    """
    problems = [_p("theta", "CRITICAL", 0)]
    result = classes_above_severity_threshold(problems, SEV_ORDER, "CRITICAL")
    assert isinstance(result, frozenset), (
        "Must return frozenset; got " + repr(type(result))
    )
    assert "theta" in result, "theta CRITICAL at threshold=CRITICAL -> included"
