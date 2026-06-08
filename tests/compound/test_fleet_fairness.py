"""Item 113: should_yield_to_interactive(fleet_state) — TDD red→green.

A background batch must throttle when interactive request latency is high AND
a batch is in-flight, to avoid starving the interactive bot (Hermes).

Discriminating tests — each kills a plausible wrong implementation:
  - high latency + batch in-flight → yield=True (MAIN DISC.) → test_high_latency_batch_yields
  - idle interactive + batch running → yield=False            → test_idle_interactive_no_yield
  - no batch in-flight → yield=False always                  → test_no_batch_no_yield
  - interactive latency at threshold → yield=False (not above)→ test_latency_at_threshold_no_yield
  - interactive latency above threshold → yield=True         → test_latency_above_threshold_yields
  - batch_inflight_count=0 → yield=False                     → test_zero_batch_no_yield
  - empty/no latency data → yield=False (fail-soft)          → test_no_latency_no_yield
"""

from __future__ import annotations

from cohezion.compound.fleet_fairness import FleetState, should_yield_to_interactive

# Default threshold used in tests (matching the default in the function)
_THRESHOLD_MS = 500.0  # ms above which we throttle


def _state(
    interactive_latency_ms: float | None = None,
    batch_inflight: int = 0,
) -> FleetState:
    return FleetState(
        interactive_latency_ms=interactive_latency_ms,
        batch_inflight_count=batch_inflight,
    )


# ---------------------------------------------------------------------------
# Core correctness
# ---------------------------------------------------------------------------


def test_high_latency_batch_yields() -> None:
    """Interactive latency above threshold + batch in-flight → yield=True.

    PRIMARY DISCRIMINATOR: models the real Hermes-starvation incident (2026-06-06).
    Kills an impl that always returns False or ignores latency.
    """
    state = _state(interactive_latency_ms=1000.0, batch_inflight=3)
    assert should_yield_to_interactive(state, latency_threshold_ms=_THRESHOLD_MS) is True, (
        "High latency (1000ms > 500ms) + batch=3 must yield=True"
    )


def test_idle_interactive_no_yield() -> None:
    """Low interactive latency + batch running → yield=False (full speed ok).

    Kills an impl that always yields when a batch is running.
    """
    state = _state(interactive_latency_ms=50.0, batch_inflight=5)
    assert should_yield_to_interactive(state, latency_threshold_ms=_THRESHOLD_MS) is False, (
        "Low latency (50ms << 500ms) + batch running must NOT yield"
    )


def test_no_batch_no_yield() -> None:
    """No batch in-flight → yield=False regardless of latency.

    Kills an impl that throttles based on latency alone (ignores batch state).
    """
    state = _state(interactive_latency_ms=9999.0, batch_inflight=0)
    assert should_yield_to_interactive(state, latency_threshold_ms=_THRESHOLD_MS) is False, (
        "No batch in-flight → never yield (nothing to throttle)"
    )


def test_zero_batch_no_yield() -> None:
    """batch_inflight_count=0 with high latency → yield=False.

    Reinforces that BOTH conditions (latency AND batch) must be true.
    """
    state = _state(interactive_latency_ms=2000.0, batch_inflight=0)
    assert should_yield_to_interactive(state, latency_threshold_ms=_THRESHOLD_MS) is False


def test_latency_at_threshold_no_yield() -> None:
    """Latency exactly at threshold → yield=False (strict 'above' not 'at or above').

    Kills an impl that uses >= instead of >.
    """
    state = _state(interactive_latency_ms=_THRESHOLD_MS, batch_inflight=2)
    assert should_yield_to_interactive(state, latency_threshold_ms=_THRESHOLD_MS) is False, (
        f"Latency exactly at threshold ({_THRESHOLD_MS}ms) must NOT yield (strict >)"
    )


def test_latency_above_threshold_yields() -> None:
    """Latency just above threshold → yield=True.

    Confirms boundary is strict > not >=.
    """
    state = _state(interactive_latency_ms=_THRESHOLD_MS + 0.001, batch_inflight=1)
    assert should_yield_to_interactive(state, latency_threshold_ms=_THRESHOLD_MS) is True


def test_no_latency_no_yield() -> None:
    """interactive_latency_ms=None (no recent requests) → yield=False (fail-soft).

    Kills an impl that crashes on None latency or returns True conservatively.
    """
    state = _state(interactive_latency_ms=None, batch_inflight=5)
    assert should_yield_to_interactive(state, latency_threshold_ms=_THRESHOLD_MS) is False, (
        "No recent interactive requests → latency unknown → fail-soft → yield=False"
    )
