"""Item 306: severity_delta_per_class() — per-class severity count delta (2026-06-08).

``severity_delta_per_class(scan_a, scan_b) -> dict[str, dict[str, int]]``:
For every (class, severity) pair with a non-zero delta between scan_a and scan_b,
returns count_b - count_a nested as {class: {severity: delta}}.
Zero-delta pairs are omitted.  Classes with only zero-delta severity pairs
are omitted entirely.  Empty both -> {}.  Pure; no I/O.

Discriminating tests — each kills a plausible wrong implementation:

  1. PRIMARY DISC.: only (class, severity) pairs with non-zero delta included.
     Kills impl including zero-delta pairs in result.
  2. delta > 0 means severity COUNT increased in scan_b (positive = more in b).
     Kills impl with flipped sign (count_a - count_b).
  3. delta < 0 means count decreased in scan_b.
     Kills impl returning absolute values.
  4. Class with ONLY zero-delta severity pairs is omitted entirely.
     Kills impl that includes a class with an empty inner dict.
  5. Empty both scans -> {}.
     Kills impl that crashes or returns non-empty on empty input.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import (
    Problem,
    severity_delta_per_class,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _p(cls: str, sev: str, idx: int) -> Problem:
    return Problem(problem_class=cls, finding_id=f"{cls}:{sev}:{idx}", severity=sev)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_only_nonzero_severity_pairs_included() -> None:
    """Only (class, severity) pairs with non-zero delta appear in result.

    PRIMARY DISCRIMINATOR: kills impl including all pairs regardless of delta.
    alpha/HIGH: 2->2 (delta=0) -> OMITTED.
    alpha/CRITICAL: 0->1 (delta=+1) -> included.
    """
    scan_a = [_p("alpha", "HIGH", 0), _p("alpha", "HIGH", 1)]
    scan_b = [
        _p("alpha", "HIGH", 0), _p("alpha", "HIGH", 1),  # HIGH unchanged
        _p("alpha", "CRITICAL", 0),                        # CRITICAL new
    ]
    result = severity_delta_per_class(scan_a, scan_b)
    assert "alpha" in result, "alpha has CRITICAL delta -> in result; got " + repr(result)
    assert "CRITICAL" in result["alpha"], (
        "alpha/CRITICAL: 0->1 -> included; got " + repr(result.get("alpha"))
    )
    assert "HIGH" not in result.get("alpha", {}), (
        "alpha/HIGH: delta=0 -> OMITTED; got " + repr(result.get("alpha"))
    )


def test_positive_delta_means_more_in_scan_b() -> None:
    """delta > 0 means severity count increased (count_b - count_a > 0).

    Kills impl computing count_a - count_b (flipped sign).
    beta/MEDIUM: 1->3 -> delta=+2.
    """
    scan_a = [_p("beta", "MEDIUM", 0)]
    scan_b = [_p("beta", "MEDIUM", 0), _p("beta", "MEDIUM", 1), _p("beta", "MEDIUM", 2)]
    result = severity_delta_per_class(scan_a, scan_b)
    assert result.get("beta", {}).get("MEDIUM") == 2, (
        "beta/MEDIUM: 1->3, delta=+2; got " + repr(result.get("beta"))
    )


def test_negative_delta_means_fewer_in_scan_b() -> None:
    """delta < 0 means severity count decreased (count_b - count_a < 0).

    Kills impl returning absolute values.
    gamma/LOW: 3->1 -> delta=-2.
    """
    scan_a = [_p("gamma", "LOW", 0), _p("gamma", "LOW", 1), _p("gamma", "LOW", 2)]
    scan_b = [_p("gamma", "LOW", 0)]
    result = severity_delta_per_class(scan_a, scan_b)
    assert result.get("gamma", {}).get("LOW") == -2, (
        "gamma/LOW: 3->1, delta=-2 (negative); got " + repr(result.get("gamma"))
    )


def test_class_with_only_zero_delta_severities_omitted_entirely() -> None:
    """Class where ALL severity deltas are 0 is omitted from result.

    Kills impl that includes the class with an empty inner dict.
    delta_cls: 2 HIGH in both scans -> zero delta everywhere -> omit.
    epsilon_cls: 1 CRITICAL -> 2 CRITICAL -> include.
    """
    scan_a = [
        _p("delta_cls", "HIGH", 0), _p("delta_cls", "HIGH", 1),
        _p("epsilon_cls", "CRITICAL", 0),
    ]
    scan_b = [
        _p("delta_cls", "HIGH", 0), _p("delta_cls", "HIGH", 1),  # unchanged
        _p("epsilon_cls", "CRITICAL", 0), _p("epsilon_cls", "CRITICAL", 1),  # grew
    ]
    result = severity_delta_per_class(scan_a, scan_b)
    assert "delta_cls" not in result, (
        "delta_cls all-zero deltas -> omitted; got keys: " + repr(list(result.keys()))
    )
    assert "epsilon_cls" in result, (
        "epsilon_cls has CRITICAL delta -> included; got keys: " + repr(list(result.keys()))
    )


def test_empty_both_scans_returns_empty_dict() -> None:
    """Empty both scans -> {}.

    Kills impl that crashes or returns non-empty.
    """
    result = severity_delta_per_class([], [])
    assert result == {}, "empty both -> {}; got " + repr(result)
