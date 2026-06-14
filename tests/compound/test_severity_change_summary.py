"""Item 284: severity_change_summary() — human-readable cross-scan change summary (2026-06-08).

``severity_change_summary(scan_a, scan_b) -> dict[str, object]``:
Returns {"improved": list[str], "worsened": list[str], "unchanged": list[str],
"net_delta": int} where "improved" = severities with negative delta (fewer in scan_b),
"worsened" = positive delta (more in scan_b), "unchanged" = zero delta, and
net_delta = sum of all individual deltas. Pure; no I/O.

Discriminating tests -- each kills a plausible wrong implementation:

  1. PRIMARY DISC.: "improved" = FEWER problems in scan_b (negative delta).
     Kills impl that treats "more HIGH" as improved (flipped interpretation).
  2. "worsened" = MORE problems in scan_b (positive delta).
     Kills impl with wrong categorization direction.
  3. net_delta = sum of all individual deltas (len(scan_b_labelled) - len(scan_a_labelled)).
     Kills impl computing sum of absolute values or something else.
  4. Return type is dict with exactly four keys.
     Kills impl missing a key or returning a list.
  5. "unchanged" contains severities with delta = 0.
     Kills impl omitting unchanged severities.
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import (
    Problem,
    severity_change_summary,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _ps(cls: str, idx: int, sev: str) -> Problem:
    return Problem(problem_class=cls, finding_id=f"{cls}:{idx}", severity=sev)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_improved_means_fewer_in_scan_b() -> None:
    """improved = severities with FEWER problems in scan_b (negative delta).

    PRIMARY DISCRIMINATOR: kills impl with flipped improved/worsened.
    scan_a: 3 HIGH, scan_b: 1 HIGH -> HIGH has negative delta -> improved.
    """
    scan_a = [_ps("alpha", i, "HIGH") for i in range(3)]
    scan_b = [_ps("alpha", 0, "HIGH")]
    result = severity_change_summary(scan_a, scan_b)
    assert "HIGH" in result["improved"], (
        "HIGH went from 3 to 1 (fewer in b) -> improved; got " + repr(result)
    )
    assert "HIGH" not in result["worsened"], "HIGH should not be in worsened; got " + repr(result)


def test_worsened_means_more_in_scan_b() -> None:
    """worsened = severities with MORE problems in scan_b (positive delta).

    Kills impl with wrong worsened direction.
    scan_a: 1 CRITICAL, scan_b: 4 CRITICAL -> CRITICAL delta = +3 -> worsened.
    """
    scan_a = [_ps("alpha", 0, "CRITICAL")]
    scan_b = [_ps("alpha", i, "CRITICAL") for i in range(4)]
    result = severity_change_summary(scan_a, scan_b)
    assert "CRITICAL" in result["worsened"], "CRITICAL grew from 1 to 4 -> worsened; got " + repr(
        result
    )


def test_net_delta_equals_sum_of_deltas() -> None:
    """net_delta = sum of all individual severity deltas.

    Kills impl computing something else (absolute values, count-based, etc.).
    scan_a: 2 HIGH + 3 LOW (5 total labelled).
    scan_b: 4 HIGH + 1 LOW (5 total labelled).
    HIGH delta = +2, LOW delta = -2. net_delta = 0.
    """
    scan_a = [_ps("alpha", i, "HIGH") for i in range(2)] + [_ps("beta", i, "LOW") for i in range(3)]
    scan_b = [_ps("alpha", i, "HIGH") for i in range(4)] + [_ps("beta", 0, "LOW")]
    result = severity_change_summary(scan_a, scan_b)
    assert result["net_delta"] == 0, "+2 HIGH - 2 LOW -> net_delta=0; got " + repr(
        result["net_delta"]
    )


def test_return_type_has_exactly_four_keys() -> None:
    """Return type is dict with exactly four keys: improved/worsened/unchanged/net_delta.

    Kills impl missing a key.
    """
    result = severity_change_summary([], [])
    assert isinstance(result, dict), "Must return dict"
    assert set(result.keys()) == {"improved", "worsened", "unchanged", "net_delta"}, (
        "Must have exactly four keys; got " + repr(set(result.keys()))
    )


def test_unchanged_contains_zero_delta_severities() -> None:
    """unchanged contains severities with delta = 0.

    Kills impl omitting unchanged severities.
    scan_a: 2 HIGH + 1 LOW, scan_b: 2 HIGH + 3 LOW.
    HIGH delta=0 -> unchanged. LOW delta=+2 -> worsened.
    """
    scan_a = [_ps("alpha", i, "HIGH") for i in range(2)] + [_ps("alpha", 10, "LOW")]
    scan_b = [_ps("alpha", i, "HIGH") for i in range(2)] + [
        _ps("alpha", i, "LOW") for i in range(3)
    ]
    result = severity_change_summary(scan_a, scan_b)
    assert "HIGH" in result["unchanged"], "HIGH delta=0 -> unchanged; got " + repr(result)
    assert "LOW" in result["worsened"], "LOW delta=+2 -> worsened"
