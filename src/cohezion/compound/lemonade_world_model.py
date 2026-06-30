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

# F3 FIX (2026-06-30): the coherence prompt must elicit an estimate of TASK TRACTABILITY (does
# the next step succeed / stay on-track for THIS task?), NOT a generic "coherence of the next
# step" that the 1B model anchored to the embedded prior value + downward priming. The old prompt
# ("Multi-step executions tend to lose coherence. Estimate the coherence of the NEXT step …") pinned
# a TRIVIAL task at 0.20 and an INTRACTABLE one at 0.00 — both penalized, so at the real-task
# zero-state the gate REROUTE/SKIPed almost everything. The few-shot anchors below calibrate the
# scale (trivial HIGH, intractable LOW); verified LIVE on llama3.2-1b-FLM: "add two numbers" → 0.93,
# "derive a full theory of quantum gravity with proof" → 0.01 (and the intractable prompt is the
# LONGER one, so the estimate tracks tractability, not verbosity).
_COHERENCE_PROMPT_HEADER = (
    "Rate how likely an AI assistant's next step will SUCCEED and stay on-track for a task, "
    "as a calibrated probability from 0.00 (hopeless / intractable) to 1.00 (trivially solvable).\n"
    "Examples:\n"
    "Task: add two small numbers -> 0.97\n"
    "Task: reverse a short string -> 0.95\n"
    "Task: write a haiku about spring -> 0.90\n"
    "Task: prove the Riemann hypothesis from scratch in one step -> 0.05\n"
    "Task: derive a complete theory of quantum gravity with full proof -> 0.04\n"
    "Now rate this task. Reply with ONLY the number.\n"
)


def _parse_coherence(text: str) -> float | None:
    """Extract the first 0..1 float from the LLM reply; None if none in range.

    BUGHUNT FIX (2026-06-30): iterate ALL numeric matches and return the first one in [0, 1],
    rather than the first match overall. A reply like ``"step 2: 0.9"`` previously matched the
    leading integer ``2`` (→ 2.0, out of range → None) and silently discarded the real ``0.9``.
    """
    if not text:
        return None
    for m in _FLOAT_RE.finditer(text):
        try:
            v = float(m.group(1))
        except ValueError:
            continue
        if 0.0 <= v <= 1.0:
            return v
    return None


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
        # Current task description — injected by JepaGate.check() via set_task() before each
        # prediction so the coherence estimate depends on the ACTUAL task, not just the prior
        # coherence value (BUGHUNT 2026-06-30: the gate was task-blind → constant verdict).
        self._task: str = ""

    def set_task(self, task_description: str) -> None:
        """Inject the task description threaded into the next predict_next_state prompt.

        State-injection (not a signature change) keeps the world-model interface backward-compat:
        existing stubs/JEPAWorldModels without set_task are unaffected. Fail-open: any non-string
        input is coerced to an empty task, never raises.
        """
        try:
            self._task = str(task_description) if task_description else ""
        except Exception:  # pragma: no cover - defensive, str() rarely raises
            self._task = ""

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
        """Estimate next-step coherence as the TASK's success-likelihood via the local LLM.

        The estimate is driven by the task tractability (few-shot calibrated, F3 fix), NOT the
        prior coherence value: in production the gate calls ``check(task_description)`` with no
        ``current_state``, so ``state`` is always the zero-vector — the task IS the only real
        signal. ``cur`` is retained ONLY as the fail-open value (persist current coherence when the
        LLM is unreachable), never embedded in the prompt (embedding it caused the model to anchor
        near it and ignore the task — the root cause of the F3 garbage signal).
        """
        cur = float(np.mean(np.clip(np.asarray(state, dtype=np.float32), 0.0, 1.0)))
        if cur < 0.05:  # uninitialized/default zero-state → a neutral baseline, not a false 0.0
            cur = self._BASELINE
        task = self._task[:200] if self._task else "(unspecified task)"
        prompt = f"{_COHERENCE_PROMPT_HEADER}Task: {task} -> "
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


def build_live_jepa_gate(lookahead_steps: int = 1):
    """JG2 live wiring (factory): a JepaGate with a lemonade-backed world model when local inference
    is reachable; else a fail-open gate (world_model=None). Probes lemonade ONCE at construction so
    the runtime path never blocks on a dead endpoint.

    Default lookahead_steps=1 (the honest single-step read). After the F3 fix the world model returns
    the task's tractability estimate per step (independent of the zero-action state), so a k-step
    trajectory is constant at that value — k>1 no longer collapses to a task-blind ~0.15 anti-signal
    (the prior degrading-rollout bug). k>1 is retained for a future non-constant rollout but adds no
    signal today, so the factory default stays 1 to avoid spending extra NPU calls for no gain."""
    from cohezion.compound.jepa_gate import JepaGate

    try:
        from cohezion.compound.local_inference import lemonade_available

        # M3 fix: probe :13305 (the OmniRouter the world model actually infers on, per N1) — NOT the
        # default :13306, which is the redundant per-port server and is usually offline, so the gate
        # was silently fail-opening to world_model=None for the whole executor lifetime.
        if lemonade_available(npu_port=13305):
            return JepaGate(world_model=LemonadeWorldModel(), lookahead_steps=lookahead_steps)
    except Exception:
        pass
    return JepaGate(world_model=None)
