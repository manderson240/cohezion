"""V-model tests for the lemonade-backed JepaGate world model (JG2 live wiring, 2026-06-29).

The GIC's k-step lookahead delegates world-model inference to local lemonade silicon via the
GAIA SDK. These tests mock the LLM call (no network) and exercise the EXACT production path:
a LemonadeWorldModel inside a JepaGate, plus the factory wiring guard.
"""
from __future__ import annotations

import numpy as np

from cohezion.compound.jepa_gate import JepaGate, PreExecutionVerdict
from cohezion.compound.lemonade_world_model import (
    LemonadeWorldModel,
    _parse_coherence,
    build_live_jepa_gate,
)


class TestLemonadeWorldModelStructural:
    def test_implements_world_model_interface(self):
        assert hasattr(LemonadeWorldModel, "predict_next_state")
        assert hasattr(LemonadeWorldModel, "simulate_trajectory")

    def test_parse_coherence_extracts_valid_floats_only(self):
        assert _parse_coherence("0.85") == 0.85
        assert _parse_coherence("The coherence is 0.3 roughly") == 0.3
        assert _parse_coherence("1.5") is None  # out of [0,1] range
        assert _parse_coherence("no number here") is None
        assert _parse_coherence("") is None

    def test_parse_coherence_leading_integer_does_not_mask_valid_float(self):
        """BUGHUNT 2026-06-30: a leading out-of-range integer (e.g. a step index) must NOT shadow
        the real [0,1] value. The old `.search()` impl returned the FIRST match (2.0 → None)."""
        assert _parse_coherence("step 2: 0.9") == 0.9
        assert _parse_coherence("2.0 then 0.4") == 0.4
        assert _parse_coherence("42") is None  # only out-of-range numbers → None


class TestLemonadeWorldModelBehavioral:
    def test_predict_uses_llm_estimate(self):
        wm = LemonadeWorldModel(chat_fn=lambda _p: "0.42")
        s = wm.predict_next_state(np.full(12, 0.5, dtype=np.float32), None)
        assert abs(float(np.mean(s)) - 0.42) < 1e-6

    def test_fallback_when_llm_raises_does_not_force_skip(self):
        """Discriminating: an LLM failure on the default zero-state must NOT collapse to 0.0
        (which would SKIP everything). It falls back to the neutral baseline → safe."""

        def boom(_p):
            raise RuntimeError("lemonade down")

        wm = LemonadeWorldModel(chat_fn=boom)
        s = wm.predict_next_state(np.zeros(12, dtype=np.float32), None)
        assert float(np.mean(s)) >= 0.6  # baseline, not a false 0.0 → would not spuriously SKIP

    def test_simulate_trajectory_rolls_k_steps(self):
        wm = LemonadeWorldModel(chat_fn=lambda _p: "0.5")
        traj = wm.simulate_trajectory(np.full(12, 0.5, dtype=np.float32), [None, None, None])
        assert len(traj) == 4  # initial + 3 predicted


class TestTaskAwareness:
    """BUGHUNT 2026-06-30: the world model must read the TASK, not just the prior coherence."""

    def test_different_task_yields_different_coherence(self):
        """Discriminating: two different tasks (same prior state) must yield DIFFERENT coherence
        via the production gate path. A task-blind impl (ignoring set_task) returns identical
        coherence for both → both asserts fail."""

        def task_aware_chat(prompt: str) -> str:
            # The task is threaded into the prompt; coherence depends on it.
            return "0.9" if "easy" in prompt.lower() else "0.1"

        wm = LemonadeWorldModel(chat_fn=task_aware_chat)
        gate = JepaGate(world_model=wm)  # default single-step; set_task threaded by check()
        state = np.full(12, 0.5, dtype=np.float32)

        gate.check("an easy lookup", current_state=state)
        coh_easy = gate.last_coherence
        gate.check("a hard multi-step reasoning chain", current_state=state)
        coh_hard = gate.last_coherence

        assert coh_easy != coh_hard, "coherence must depend on the task (gate was task-blind)"
        assert coh_easy > coh_hard

    def test_set_task_threads_into_predict_prompt(self):
        """The injected task text appears in the prompt the world model sends to the LLM."""
        seen: dict[str, str] = {}

        def capture(prompt: str) -> str:
            seen["prompt"] = prompt
            return "0.5"

        wm = LemonadeWorldModel(chat_fn=capture)
        wm.set_task("translate the contract clause")
        wm.predict_next_state(np.full(12, 0.5, dtype=np.float32), None)
        assert "translate the contract clause" in seen["prompt"]


class TestLemonadeGateIntegration:
    """The EXACT production path: a JepaGate whose world model delegates to lemonade."""

    def test_low_coherence_llm_makes_gate_skip(self):
        """Discriminating: the LLM's LOW coherence estimate must drive the gate to SKIP. A wrong
        impl that ignores the world model (fail-open) would PROCEED."""
        wm = LemonadeWorldModel(chat_fn=lambda _p: "0.05")
        gate = JepaGate(world_model=wm, lookahead_steps=3)
        verdict = gate.check("risky task", current_state=np.full(12, 0.5, dtype=np.float32))
        assert verdict == PreExecutionVerdict.SKIP

    def test_high_coherence_llm_makes_gate_proceed(self):
        wm = LemonadeWorldModel(chat_fn=lambda _p: "0.9")
        gate = JepaGate(world_model=wm, lookahead_steps=3)
        verdict = gate.check("safe task", current_state=np.full(12, 0.5, dtype=np.float32))
        assert verdict == PreExecutionVerdict.PROCEED


class TestLiveWiring:
    def test_wires_lemonade_world_model_when_available(self, monkeypatch):
        import cohezion.compound.local_inference as li

        monkeypatch.setattr(li, "lemonade_available", lambda *a, **k: True)
        gate = build_live_jepa_gate(lookahead_steps=3)
        assert isinstance(gate._world_model, LemonadeWorldModel)
        assert gate._lookahead_steps == 3

    def test_fail_open_when_lemonade_unavailable(self, monkeypatch):
        import cohezion.compound.local_inference as li

        monkeypatch.setattr(li, "lemonade_available", lambda *a, **k: False)
        gate = build_live_jepa_gate()
        assert gate._world_model is None  # fail-open gate, no network at runtime
