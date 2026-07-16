"""FLUME world model — extends Cohezion's latent-space backbone for JepaGate lookahead (GIC, 2026-06-29).

:class:`FlumeWorldModel` is a FLUME (Fluid Latent Understanding through Manifold Encoding) component
that maps task descriptions into the 12D manifold's coherence dimension via local AMD silicon.  It
wires the JepaGate k-step lookahead (JG2) LIVE by delegating coherence inference to the GAIA SDK
(router :13305, fast NPU model) rather than a heavyweight torch JEPAWorldModel.

Why FLUME? FLUME is the latent-space backbone — not just the VAE, but any component that translates
between surface representations (task text, env observations) and the 12D manifold.  This world
model does exactly that: it converts a task description into a tractability estimate that lives in
the manifold's quality dimension.  The inference provider is Lemonade, but the semantics are FLUME.

Deterministic fallback (persist current coherence) when the LLM is unreachable, so the gate
degrades gracefully rather than failing.

:class:`LemonadeWorldModel` is a backward-compatible alias retained for existing importers.
"""

from __future__ import annotations

import logging
import re
from collections.abc import Callable
from typing import Any

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


class FlumeWorldModel:
    """FLUME world model — maps task descriptions to 12D manifold coherence via local LLM inference.

    Extends the FLUME latent-space backbone: instead of encoding via the VAE, this component
    uses a fast local language model (llama3.2-1b-FLM on the XDNA2 NPU via :13305 OmniRouter)
    as a tractability probe in the manifold's quality dimension.  The protocol is:
    task description → tractability prompt → scalar coherence → 12D state vector.

    Args:
        chat_fn: Optional ``prompt(text) -> str`` callable. Injected in tests; when None, a GAIA
            ``LemonadeClient`` shim is built lazily on first use (router :13305, fast NPU model).
        model_id: lemonade model id for the default GAIA path.
    """

    def __init__(
        self, chat_fn: Callable[[str], str] | None = None, model_id: str = _DEFAULT_MODEL
    ) -> None:
        self._chat_fn = chat_fn
        self._model_id = model_id
        # Current task description — injected by JepaGate.check() via set_task() before each
        # prediction so the coherence estimate depends on the ACTUAL task, not just the prior
        # coherence value (BUGHUNT 2026-06-30: the gate was task-blind → constant verdict).
        self._task: str = ""
        # AdaJEPA adaptive baseline (2606.32026): per-instance baseline that drifts toward
        # the empirical mean of actual execution quality after observe() calls accumulate.
        # Starts at the class prior _BASELINE (0.7); clamp [0.3, 0.9] prevents collapse.
        self._baseline: float = self._BASELINE
        self._ema_bias: float = 0.0  # EMA of (actual_quality - predicted_coherence)
        self._obs_count: int = 0

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

    _BASELINE = 0.7  # class prior — per-instance _baseline adapts away from this after observe()

    def observe(self, _task: str, predicted_coherence: float, actual_quality: float) -> None:
        """AdaJEPA feedback (2606.32026): recalibrate the per-instance baseline from actual outcomes.

        Records the signed error (actual − predicted) via EMA. After ≥5 observations the instance
        baseline drifts toward the empirical bias so future coherence estimates converge to reality.
        Example: if the 1B model consistently over-predicts tractability (predicted=0.7, actual=0.4),
        the baseline drops, tightening gate thresholds for this compound loop instance.
        Fail-open: clamps to [0.3, 0.9] so the gate never collapse-disables via runaway drift.
        """
        error = float(actual_quality) - float(predicted_coherence)
        alpha = 0.2
        self._ema_bias = (1.0 - alpha) * self._ema_bias + alpha * error
        self._obs_count += 1
        if self._obs_count >= 5:
            self._baseline = float(np.clip(self._baseline + 0.1 * self._ema_bias, 0.3, 0.9))

    def predict_next_state(self, state: np.ndarray, _action: Any) -> np.ndarray:
        """Estimate next-step coherence as the TASK's success-likelihood via the local LLM.

        The estimate is driven by the task tractability (few-shot calibrated, F3 fix), NOT the
        prior coherence value: in production the gate calls ``check(task_description)`` with no
        ``current_state``, so ``state`` is always the zero-vector — the task IS the only real
        signal. ``cur`` is retained ONLY as the fail-open value (persist current coherence when the
        LLM is unreachable), never embedded in the prompt (embedding it caused the model to anchor
        near it and ignore the task — the root cause of the F3 garbage signal).
        """
        cur = float(np.mean(np.clip(np.asarray(state, dtype=np.float32), 0.0, 1.0)))
        if cur < 0.05:  # uninitialized/default zero-state → neutral baseline, not a false 0.0
            cur = self._baseline  # use adaptive instance baseline (starts at class _BASELINE=0.7)
        task = self._task[:200] if self._task else "(unspecified task)"
        prompt = f"{_COHERENCE_PROMPT_HEADER}Task: {task} -> "
        try:
            coh = _parse_coherence(self._chat(prompt))
        except Exception as exc:  # unreachable LLM, transport error, etc.
            logger.debug("LemonadeWorldModel chat failed (fallback): %s", exc)
            coh = None
        if coh is None:
            coh = cur  # deterministic fallback: persist current coherence (no spurious SKIP)
        else:
            # Beta(2,2) shrinkage toward adaptive _baseline (AdaJEPA: baseline drifts from actual
            # quality observations). Cold-start: coh=0.010 → 0.470 (REROUTE, not SKIP).
            # After calibration: _baseline converges toward empirical execution quality mean.
            coh = (2.0 * self._baseline + coh) / 3.0
        return np.full(_DIM, float(np.clip(coh, 0.0, 1.0)), dtype=np.float32)

    def simulate_trajectory(self, initial_state: np.ndarray, actions: list) -> list[np.ndarray]:
        """Roll the LLM-estimated coherence forward N steps (the JepaGate lookahead path)."""
        trajectory = [np.asarray(initial_state, dtype=np.float32)]
        state = trajectory[0]
        for action in actions:
            state = self.predict_next_state(state, action)
            trajectory.append(state)
        return trajectory


#: Backward-compatible alias — existing importers work unchanged.
LemonadeWorldModel = FlumeWorldModel


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
            try:
                # TRACE wiring (2026-07-15): once the tier-flow observer has real transition
                # data, prefer coherence from OBSERVED tier statistics (ObserverWorldModel)
                # over the LLM estimate — the LLM signal tracks prompt length, not
                # tractability (QA 2026-06-30). Cold observer -> fall through to FLUME/LLM.
                from cohezion.world_model.observer_world_model import get_default_observer_model

                _owm = get_default_observer_model()
                if sum(_owm.n_transitions(t) for t in ("npu", "igpu", "cpu")) >= 10:
                    return JepaGate(
                        world_model=_owm,
                        lookahead_steps=lookahead_steps,
                        reroute_only=True,
                    )
            except Exception:  # noqa: BLE001 — gate construction must stay fail-open
                pass
            # reroute_only=True: the 1B world model is a NOISY BINARY signal (QA 2026-06-30 — routine
            # tractable tasks collapse to ~0.01, the LOW few-shot anchor). A spurious low must escalate
            # ONE tier, NEVER SKIP-abort a legitimate task (executor.py:721). PROCEED/REROUTE kept.
            return JepaGate(
                world_model=FlumeWorldModel(),
                lookahead_steps=lookahead_steps,
                reroute_only=True,
            )
    except Exception:
        pass
    return JepaGate(world_model=None)
