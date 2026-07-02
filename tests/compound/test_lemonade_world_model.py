"""V-model tests for the lemonade-backed JepaGate world model (JG2 live wiring, 2026-06-29).

The GIC's k-step lookahead delegates world-model inference to local lemonade silicon via the
GAIA SDK. These tests mock the LLM call (no network) and exercise the EXACT production path:
a LemonadeWorldModel inside a JepaGate, plus the factory wiring guard.
"""

from __future__ import annotations

import re

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
        # Beta(2,2) prior (2026-07-02): (2*0.7 + 0.42)/3 = 0.6067, not raw 0.42.
        wm = LemonadeWorldModel(chat_fn=lambda _p: "0.42")
        s = wm.predict_next_state(np.full(12, 0.5, dtype=np.float32), None)
        expected = (2.0 * LemonadeWorldModel._BASELINE + 0.42) / 3.0
        assert abs(float(np.mean(s)) - expected) < 1e-4

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

    def test_low_coherence_llm_makes_gate_reroute_not_proceed(self):
        """Discriminating: a LOW LLM coherence (0.05) must drive the gate to REROUTE, NOT PROCEED.
        A wrong impl that ignores the world model (fail-open) returns PROCEED → assertion fails.
        After the Beta(2,2) prior (2026-07-02), 0.05 → (2*0.7+0.05)/3=0.483 → REROUTE, not SKIP:
        the prior prevents abort while still penalizing low-confidence readings."""
        wm = LemonadeWorldModel(chat_fn=lambda _p: "0.05")
        gate = JepaGate(world_model=wm, lookahead_steps=3)
        verdict = gate.check("risky task", current_state=np.full(12, 0.5, dtype=np.float32))
        assert verdict != PreExecutionVerdict.PROCEED  # world model IS used (not fail-open)
        assert verdict == PreExecutionVerdict.REROUTE  # escalates, does not abort

    def test_high_coherence_llm_makes_gate_proceed(self):
        wm = LemonadeWorldModel(chat_fn=lambda _p: "0.9")
        gate = JepaGate(world_model=wm, lookahead_steps=3)
        verdict = gate.check("safe task", current_state=np.full(12, 0.5, dtype=np.float32))
        assert verdict == PreExecutionVerdict.PROCEED


class TestF3CoherenceCalibratedToTractability:
    """F3 (re-eval review, CONFIRMED MED): the coherence estimate must correlate with TASK
    TRACTABILITY, not prompt framing/length. The old prompt ("multi-step executions tend to lose
    coherence. Estimate the coherence of the NEXT step") pinned a TRIVIAL task at ~0.20 and an
    INTRACTABLE one at ~0.00 → at the real-task zero-state the gate REROUTE/SKIPed almost everything.
    The fix reframes the prompt to ask the few-shot-anchored SUCCESS-likelihood of THIS task.
    """

    @staticmethod
    def _calibration_sensitive_chat(prompt: str) -> str:
        """Simulate the 1B model's dependence on prompt framing.

        Under the OLD downward-priming framing (no success/tractability anchors) the model pins a
        pathological constant ~0.2 regardless of task → over-routing. Under the FIXED calibrated
        framing it reads the actual (last, incomplete) ``Task: ... ->`` line and rates tractability.
        A wrong impl that kept the old prompt elicits 0.2 for BOTH tasks → the PROCEED assertion fails.
        """
        p = prompt.lower()
        if "succeed" not in p or "trivially solvable" not in p:
            return "0.2"  # old framing → constant low, no task separation
        matches = re.findall(r"task:\s*(.*?)\s*->", p)
        actual = matches[-1] if matches else p  # the final incomplete few-shot line = the real task
        return "0.95" if "add two" in actual else "0.05"

    def test_tractable_task_not_lower_than_intractable_via_gate(self):
        """Falsification: a TRACTABLE task must NOT score lower than (and must PROCEED where) an
        INTRACTABLE one. Against the unfixed prompt both land at 0.2 → tractable REROUTEs → FAIL."""
        chat = self._calibration_sensitive_chat
        state = np.full(12, 0.5, dtype=np.float32)

        gate_t = JepaGate(world_model=LemonadeWorldModel(chat_fn=chat))
        v_t = gate_t.check("add two small numbers together", current_state=state)
        coh_t = gate_t.last_coherence

        gate_i = JepaGate(world_model=LemonadeWorldModel(chat_fn=chat))
        v_i = gate_i.check(
            "prove an intractable open conjecture in a single step", current_state=state
        )
        coh_i = gate_i.last_coherence

        # The inversion the review found: tractable must be >= intractable.
        assert coh_t >= coh_i
        # And the calibrated signal must let a trivial task PROCEED (no spurious REROUTE),
        # while the intractable one does not.
        assert v_t == PreExecutionVerdict.PROCEED
        assert v_i != PreExecutionVerdict.PROCEED

    def test_prompt_asks_tractability_not_coherence_loss(self):
        """The fix's root cause: the prompt must ask SUCCESS-likelihood with anchors and must NOT
        carry the downward-priming bias. The old prompt fails all three assertions."""
        seen: dict[str, str] = {}

        def capture(prompt: str) -> str:
            seen["p"] = prompt
            return "0.5"

        wm = LemonadeWorldModel(chat_fn=capture)
        wm.set_task("summarize a short paragraph")
        wm.predict_next_state(np.full(12, 0.5, dtype=np.float32), None)
        p = seen["p"].lower()
        assert "succeed" in p  # asks about success, not generic "coherence"
        assert "trivially solvable" in p  # calibration anchor present
        assert "tend to lose coherence" not in p  # downward-priming bias removed


class TestF3RerouteOnlySafety:
    """F3 PRODUCTION HAZARD (QA 2026-06-30): the 1B world model is BINARY — routine TRACTABLE tasks
    ('reverse a linked list', 'summarize an article') collapse to ~0.01, the LOW few-shot anchor.
    Below the reroute threshold the verdict is SKIP, which early-returns ExecutionResult(success=False)
    at executor.py:721 → the task is ABORTED. The live gate must therefore be REROUTE-ONLY: a noisy
    low reading escalates ONE tier, never aborts. PROCEED and REROUTE semantics are preserved.
    """

    def test_routine_tractable_low_reading_does_not_skip_on_live_gate(self):
        """Falsification: a routine tractable task that the binary 1B rates 0.01 must NOT yield a
        SKIP on the live (reroute_only) gate. A wrong impl (no reroute_only cap) returns SKIP →
        the executor aborts the task → assertion fails."""
        wm = LemonadeWorldModel(chat_fn=lambda _p: "0.01")  # the binary LOW anchor collapse
        gate = JepaGate(world_model=wm, reroute_only=True)
        verdict = gate.check(
            "reverse a linked list in Python", current_state=np.full(12, 0.5, dtype=np.float32)
        )
        assert verdict != PreExecutionVerdict.SKIP
        assert verdict == PreExecutionVerdict.REROUTE  # escalate one tier, never abort

    def test_beta_prior_prevents_skip_even_without_reroute_only_discriminating(self):
        """Discriminating: after the Beta(2,2) prior (2026-07-02), the MINIMUM LLM output (0.0)
        is smoothed to (2*0.7+0.0)/3=0.467 > SKIP threshold 0.1 — so SKIP is structurally
        impossible for any in-range LemonadeWorldModel reading even with reroute_only=False.
        The Beta prior itself is the abort-safety; reroute_only is now a redundant belt. A wrong
        impl (no Beta prior, raw 0.0 passed to gate) would return SKIP → assertion fails."""
        wm = LemonadeWorldModel(chat_fn=lambda _p: "0.0")  # absolute minimum LLM output
        gate = JepaGate(world_model=wm)  # reroute_only=False — the prior, not the flag, saves us
        verdict = gate.check("some task", current_state=np.full(12, 0.5, dtype=np.float32))
        assert verdict != PreExecutionVerdict.SKIP  # Beta prior prevents abort
        assert verdict == PreExecutionVerdict.REROUTE

    def test_reroute_only_still_proceeds_on_high_coherence(self):
        """The safety cap must not suppress a legitimate PROCEED for a tractable high reading."""
        wm = LemonadeWorldModel(chat_fn=lambda _p: "0.95")
        gate = JepaGate(world_model=wm, reroute_only=True)
        verdict = gate.check("add two numbers", current_state=np.full(12, 0.5, dtype=np.float32))
        assert verdict == PreExecutionVerdict.PROCEED


class TestAdaJEPA:
    """AdaJEPA adaptive baseline (arXiv:2606.32026): per-instance _baseline drifts toward the
    empirical mean of actual execution quality after ≥5 observe() calls accumulate.
    """

    def test_baseline_starts_at_class_prior(self):
        """Instance baseline must shadow the class prior at construction."""
        wm = LemonadeWorldModel()
        assert wm._baseline == LemonadeWorldModel._BASELINE

    def test_no_drift_before_five_observations(self):
        """Discriminating: fewer than 5 calls must NOT move _baseline.

        A wrong impl (updating on every call) would show drift after 3 → FAIL.
        """
        wm = LemonadeWorldModel()
        prior = wm._baseline
        for _ in range(4):
            wm.observe("t", 0.7, 0.9)  # positive error = actual > predicted
        assert wm._baseline == prior, "_baseline must not change before 5 observations"

    def test_baseline_increases_after_positive_errors(self):
        """Discriminating: systematic positive errors (actual > predicted) must raise _baseline.

        A wrong impl that ignores EMA or drifts in the wrong direction would leave _baseline
        at _BASELINE or below → FAIL.
        """
        wm = LemonadeWorldModel()
        for _ in range(10):
            wm.observe("t", 0.5, 0.9)  # actual=0.9, predicted=0.5 → error=+0.4 each time
        assert wm._baseline > LemonadeWorldModel._BASELINE, (
            f"_baseline ({wm._baseline:.4f}) must exceed class prior "
            f"({LemonadeWorldModel._BASELINE}) after 10 positive-error observations"
        )

    def test_baseline_decreases_after_negative_errors(self):
        """Discriminating: systematic negative errors (actual < predicted) must lower _baseline.

        A wrong impl with wrong sign convention would raise _baseline instead → FAIL.
        """
        wm = LemonadeWorldModel()
        for _ in range(10):
            wm.observe("t", 0.9, 0.3)  # actual=0.3, predicted=0.9 → error=-0.6 each time
        assert wm._baseline < LemonadeWorldModel._BASELINE, (
            f"_baseline ({wm._baseline:.4f}) must fall below class prior "
            f"({LemonadeWorldModel._BASELINE}) after 10 negative-error observations"
        )

    def test_baseline_clamped_to_floor(self):
        """Fail-safe: extreme negative errors must not drive _baseline below 0.3."""
        wm = LemonadeWorldModel()
        for _ in range(50):
            wm.observe("t", 1.0, 0.0)  # error = -1.0 every call
        assert wm._baseline >= 0.3

    def test_baseline_clamped_to_ceiling(self):
        """Fail-safe: extreme positive errors must not drive _baseline above 0.9."""
        wm = LemonadeWorldModel()
        for _ in range(50):
            wm.observe("t", 0.0, 1.0)  # error = +1.0 every call
        assert wm._baseline <= 0.9

    def test_adapted_baseline_influences_beta_prior_shrinkage(self):
        """Discriminating: predict_next_state must use _baseline, not _BASELINE.

        We drive _baseline below _BASELINE with negative errors, then confirm that
        the Beta(2,2) shrinkage output is lower than it would be with the class prior.
        A wrong impl that still uses self._BASELINE inside predict_next_state would
        return the pre-adaptation value → both assertions below would FAIL.
        """
        wm_adapted = LemonadeWorldModel(chat_fn=lambda _p: "0.5")
        for _ in range(10):
            wm_adapted.observe("t", 0.9, 0.1)  # drive _baseline DOWN

        wm_naive = LemonadeWorldModel(chat_fn=lambda _p: "0.5")

        s = np.full(12, 0.01, dtype=np.float32)  # near-zero → triggers the cur=_baseline branch
        pred_adapted = float(np.mean(wm_adapted.predict_next_state(s, None)))
        pred_naive = float(np.mean(wm_naive.predict_next_state(s, None)))

        assert wm_adapted._baseline < wm_naive._baseline, "adapted baseline must be lower"
        assert pred_adapted < pred_naive, (
            f"adapted prediction ({pred_adapted:.4f}) must be lower than naive "
            f"({pred_naive:.4f}) because _baseline influences both the cur fallback "
            f"and the Beta(2,2) shrinkage term"
        )


class TestLiveWiring:
    def test_wires_lemonade_world_model_when_available(self, monkeypatch):
        import cohezion.compound.local_inference as li

        monkeypatch.setattr(li, "lemonade_available", lambda *a, **k: True)
        gate = build_live_jepa_gate(lookahead_steps=3)
        assert isinstance(gate._world_model, LemonadeWorldModel)
        assert gate._lookahead_steps == 3
        assert gate._reroute_only is True  # live binary signal must never SKIP-abort

    def test_fail_open_when_lemonade_unavailable(self, monkeypatch):
        import cohezion.compound.local_inference as li

        monkeypatch.setattr(li, "lemonade_available", lambda *a, **k: False)
        gate = build_live_jepa_gate()
        assert gate._world_model is None  # fail-open gate, no network at runtime
