"""Item 113: Fleet-fairness guard — interactive bot starvation prevention.

A heavy local-inference background batch MUST NOT starve the Hermes interactive bot.
``should_yield_to_interactive`` is a report-only predicate that the batch driver
(``distill_tutorials.py`` and siblings) consults between items to decide whether to
pause or throttle.

Lesson learned 2026-06-06: a 431-tutorial distillation saturating :13305 caused
empty-response after retries for the live Hermes bot.  This guard is the engineering
response: measure interactive latency, check batch in-flight count, yield when needed.

Pure (injected ``FleetState``; no live :13305 probe under pytest).  Report-only predicate.
The behaviour-change (actually throttling) lands behind this predicate — the batch
driver checks it and sleeps/slows accordingly.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class FleetState:
    """Snapshot of the fleet's interactive + batch load (item 113).

    Attributes
    ----------
    interactive_latency_ms:
        Recent P50/P95 interactive request latency in milliseconds, or ``None``
        if no recent interactive requests have been observed (the bot is idle).
    batch_inflight_count:
        Number of background batch tasks currently being processed by the fleet.
        Zero means no background work is in-flight.
    """

    interactive_latency_ms: float | None
    batch_inflight_count: int


def should_yield_to_interactive(
    fleet_state: FleetState,
    *,
    latency_threshold_ms: float = 500.0,
) -> bool:
    """Return ``True`` when a background batch should throttle to protect the bot (item 113).

    Yield conditions — BOTH must be true simultaneously:
    1. ``interactive_latency_ms > latency_threshold_ms`` (latency is hurting the bot).
    2. ``batch_inflight_count > 0`` (there is a background job we could throttle).

    If either condition is false, returning ``False`` means "full speed ahead":
    - No batch → nothing to throttle.
    - Low latency → bot is unaffected, no need to yield.
    - ``interactive_latency_ms is None`` → no recent interactive requests → fail-soft
      (no data = assume OK, return False).

    Args:
        fleet_state:
            Injected snapshot of the fleet's current load.  No live :13305 probe.
        latency_threshold_ms:
            Interactive latency threshold in milliseconds above which the background
            job should yield.  Comparison is strict (``>``): latency exactly equal to
            the threshold does NOT trigger yielding.  Defaults to 500 ms.

    Returns:
        ``True`` when both yield conditions are met; ``False`` otherwise.

    Pure (injected state; no network calls, no clock).  Report-only predicate.
    """
    if fleet_state.batch_inflight_count <= 0:
        return False
    if fleet_state.interactive_latency_ms is None:
        return False  # fail-soft: no data → assume interactive is fine
    return fleet_state.interactive_latency_ms > latency_threshold_ms
