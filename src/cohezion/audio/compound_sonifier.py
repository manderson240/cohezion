"""Phase 1 — Coherence Adaptive Bed: make the compound loop AUDIBLE.

Reads the live tier-flow observer's coherence (the same signal today's JepaGate
consumes) and generates a matching music bed via AceStepClient. Coherence is
bucketed so a 5s generation is reused across micro-fluctuations; everything is
fail-open — music is an enhancement, never a dependency of the loop.
"""

from __future__ import annotations

import logging

from cohezion.audio.acestep_client import AceStepClient, coherence_to_prompt

logger = logging.getLogger(__name__)

_BUCKETS = 4  # sparse / mid / full / crystalline — matches the roadmap's 4 mood bands


def _coherence_bucket(coherence: float) -> int:
    c = max(0.0, min(1.0, coherence))
    return min(_BUCKETS - 1, int(c * _BUCKETS))


class CompoundSonifier:
    """Turn the tier-flow observer's coherence into a cached, fail-open music bed."""

    def __init__(self, observer=None, client: AceStepClient | None = None, state: str = "npu"):
        if observer is None:
            from cohezion.world_model.observer_world_model import get_default_observer_model

            observer = get_default_observer_model()
        self._observer = observer
        self._client = client or AceStepClient()
        self._state = state
        self._cache: dict[int, bytes] = {}

    def current_coherence(self) -> float:
        self._observer._state = self._state
        try:
            return float(self._observer.predict_next_state(None, None)[0])
        except Exception:  # noqa: BLE001 — sonification must never break the loop
            return 0.5

    def sonify_current(self) -> bytes | None:
        """Generate (or reuse) the music bed for the loop's current coherence.
        Returns raw audio bytes, or None on generation failure (fail-open)."""
        coherence = self.current_coherence()
        bucket = _coherence_bucket(coherence)
        if bucket in self._cache:
            return self._cache[bucket]
        clip = self._client.generate(coherence_to_prompt(coherence))
        if clip is not None:
            self._cache[bucket] = clip
        return clip
