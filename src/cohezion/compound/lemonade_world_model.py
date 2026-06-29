"""Lemonade-backed world model for the JepaGate pre-execution lookahead (GIC, 2026-06-29).

Wires the JepaGate k-step lookahead (JG2) LIVE by delegating the world-model inference to local
lemonade silicon via the GAIA SDK (router :13305) instead of a torch JEPAWorldModel. The gate's
world model only needs ``predict_next_state(state, action) -> ndarray`` and
``simulate_trajectory(...)``; we return a 12D state whose mean IS the LLM's next-step coherence
estimate. A local LLM models the tendency of multi-step executions to LOSE coherence — exactly
what the lookahead is meant to catch (Dyna-Think: world-model simulation guides planning).

Inference is delegated to GAIA's ``LemonadeClient`` (fast NPU model by default). Deterministic
fallback (persist current coherence) when the LLM is unreachable or returns an unparseable reply,
so the gate degrades gracefully rather than failing.
"""
from __future__ import annotations

import logging
import re
from typing import Any, Callable

import numpy as np

logger = logging.getLogger(__name__)

_DIM = 12
_DEFAULT_MODEL = "llama3.2-1b-FLM"  # fast NPU model — the gate runs per task, latency matters
_FLOAT_RE = re.compile(r"(\d?\.\d+|\d+\.?\d*)")


def _parse_coherence(text: str) -> float | None:
    """Extract the first 0..1 float from the LLM reply; None if absent/out of range."""
    if not text:
        return None
    m = _FLOAT_RE.search(text)
    if not m:
        return None
    try:
        v = float(m.group(1))
    except ValueError:
        return None
    return v if 0.0 <= v <= 1.0 else None


class LemonadeWorldModel:
    """World model whose next-step coherence is estimated by a local LLM via the GAIA SDK.

    Args:
        chat_fn: Optional ``prompt(text) -> str`` callable. Injected in tests; when None, a GAIA
            ``LemonadeClient`` shim is built lazily on first use (router :13305, fast NPU model).
        model_id: lemonade model id for the default GAIA path.
    """

    def __init__(self, chat_fn: Callable[[str], str] | None = None, model_id: str = _DEFAULT_MODEL) -> None:
        self._chat_fn = chat_fn
        self._model_id = model_id

    def _chat(self, prompt: str) -> str:
        if self._chat_fn is None:
            # lazy GAIA SDK shim — reuse the working LemonadeClient path (gaia_adapter)
            from gaia.llm.lemonade_client import LemonadeClient  # type: ignore[import-not-found]

            from cohezion.inference.gaia_adapter import _GaiaLLMClientShim

            client = LemonadeClient(
                base_url="http://localhost:13305/api/v1", model=self._model_id, verbose=False
            )
            self._chat_fn = _GaiaLLMClientShim(
                client, self._model_id, max_tokens=8, temperature=0.0
            ).prompt
        return self._chat_fn(prompt)

    _BASELINE = 0.7  # used when the input state is uninitialized (the gate's zero-vector default)

    def predict_next_state(self, state: np.ndarray, action: Any) -> np.ndarray:
        """Estimate the next-step coherence via the local LLM; return a 12D state with that mean."""
        cur = float(np.mean(np.clip(np.asarray(state, dtype=np.float32), 0.0, 1.0)))
        if cur < 0.05:  # uninitialized/default zero-state → a neutral baseline, not a false 0.0
            cur = self._BASELINE
        prompt = (
            f"A multi-step AI execution is at coherence {cur:.2f} (1.0 = fully coherent, 0.0 = "
            "incoherent). Multi-step executions tend to lose coherence. Estimate the coherence of "
            "the NEXT step as a number between 0.0 and 1.0. Reply with ONLY the number."
        )
        try:
            coh = _parse_coherence(self._chat(prompt))
        except Exception as exc:  # unreachable LLM, transport error, etc.
            logger.debug("LemonadeWorldModel chat failed (fallback): %s", exc)
            coh = None
        if coh is None:
            coh = cur  # deterministic fallback: persist current coherence (no spurious SKIP)
        return np.full(_DIM, float(np.clip(coh, 0.0, 1.0)), dtype=np.float32)

    def simulate_trajectory(self, initial_state: np.ndarray, actions: list) -> list[np.ndarray]:
        """Roll the LLM-estimated coherence forward N steps (the JepaGate lookahead path)."""
        trajectory = [np.asarray(initial_state, dtype=np.float32)]
        state = trajectory[0]
        for action in actions:
            state = self.predict_next_state(state, action)
            trajectory.append(state)
        return trajectory


def build_live_jepa_gate(lookahead_steps: int = 3):
    """JG2 live wiring (factory): a JepaGate with a lemonade-backed world model + k-step lookahead
    when local inference is reachable; else a fail-open gate (world_model=None). Probes lemonade
    ONCE at construction so the runtime path never blocks on a dead endpoint."""
    from cohezion.compound.jepa_gate import JepaGate

    try:
        from cohezion.compound.local_inference import lemonade_available

        if lemonade_available():
            return JepaGate(world_model=LemonadeWorldModel(), lookahead_steps=lookahead_steps)
    except Exception:
        pass
    return JepaGate(world_model=None)
