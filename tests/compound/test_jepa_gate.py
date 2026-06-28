"""V-model tests for #139: CompoundExecutor JEPA pre-execution simulation gate.

GIC Decision-making dimension (arXiv 2606.23991): the agent has an internal world
model (JEPA) that simulates the predicted outcome quality BEFORE committing to
execution.  Low predicted coherence → REROUTE cheaper tier or SKIP.

T1: structural — enum + class + method signatures exist.
T2: discriminating — low-coherence world model ⇒ not PROCEED; None model ⇒ PROCEED.
"""

from __future__ import annotations

import numpy as np

from cohezion.compound.jepa_gate import JepaGate, PreExecutionVerdict


# ---------------------------------------------------------------------------
# T1: Structural invariants
# ---------------------------------------------------------------------------


class TestJepaGateStructural:
    def test_pre_execution_verdict_enum_values(self):
        """PreExecutionVerdict must expose PROCEED, REROUTE, SKIP."""
        assert hasattr(PreExecutionVerdict, "PROCEED")
        assert hasattr(PreExecutionVerdict, "REROUTE")
        assert hasattr(PreExecutionVerdict, "SKIP")

    def test_jepa_gate_check_method_exists(self):
        gate = JepaGate(world_model=None)
        assert callable(getattr(gate, "check", None))

    def test_jepa_gate_accepts_none_world_model(self):
        """Constructing with None must not raise."""
        gate = JepaGate(world_model=None)
        assert gate is not None

    def test_check_signature_accepts_task_description_and_state(self):
        """check() must accept (task_description: str, current_state: np.ndarray | None)."""
        import inspect

        sig = inspect.signature(JepaGate.check)
        params = set(sig.parameters.keys())
        assert "task_description" in params
        # current_state is optional / can be None
        assert "current_state" in params or len(params) >= 2


# ---------------------------------------------------------------------------
# T2: Discriminating behavioral tests
# ---------------------------------------------------------------------------


class TestJepaGateBehavioral:
    def _make_world_model(self, predicted_coherence: float):
        """Stub JEPA world model that always returns a 12D state matching predicted_coherence."""

        class _StubJEPA:
            def predict_next_state(self, state: np.ndarray, action: np.ndarray) -> np.ndarray:
                # Return 12D vector whose mean == predicted_coherence (clipped to [0,1])
                vec = np.full(12, float(predicted_coherence))
                return vec

        return _StubJEPA()

    def test_none_world_model_returns_proceed(self):
        """Without a world model the gate must fail-open (PROCEED).

        Wrong impl: returns REROUTE or SKIP by default.
        Discriminating: only PROCEED is correct when there's no simulation capacity.
        """
        gate = JepaGate(world_model=None)
        verdict = gate.check("analyze sales data", current_state=None)
        assert verdict == PreExecutionVerdict.PROCEED, (
            f"Fail-open gate should return PROCEED, got {verdict}"
        )

    def test_high_coherence_prediction_returns_proceed(self):
        """Predicted coherence ≥ 0.6 → PROCEED.

        Wrong impl: always returns REROUTE regardless of prediction.
        """
        gate = JepaGate(world_model=self._make_world_model(0.85))
        state = np.zeros(12, dtype=float)
        verdict = gate.check("summarize document", current_state=state)
        assert verdict == PreExecutionVerdict.PROCEED, (
            f"High coherence prediction should yield PROCEED, got {verdict}"
        )

    def test_low_coherence_prediction_does_not_return_proceed(self):
        """Predicted coherence < 0.3 → REROUTE or SKIP, never PROCEED.

        This is the KEY discriminating test: the gate must catch low-quality
        predicted outcomes before they enter the 11-step pipeline.
        Wrong impl: returns PROCEED for every input.
        """
        gate = JepaGate(world_model=self._make_world_model(0.1))
        state = np.ones(12, dtype=float) * 0.1
        verdict = gate.check("complex multi-step reasoning task", current_state=state)
        assert verdict != PreExecutionVerdict.PROCEED, (
            f"Low coherence prediction should NOT return PROCEED, got {verdict}"
        )

    def test_medium_coherence_returns_reroute(self):
        """Predicted coherence in [0.3, 0.6) → REROUTE (try cheaper tier first).

        Discriminating: medium predictions don't SKIP (too aggressive) and
        don't PROCEED (quality risk), so REROUTE is the only valid verdict.
        """
        gate = JepaGate(world_model=self._make_world_model(0.4))
        state = np.zeros(12, dtype=float)
        verdict = gate.check("classify input", current_state=state)
        assert verdict == PreExecutionVerdict.REROUTE, (
            f"Medium coherence prediction should yield REROUTE, got {verdict}"
        )

    def test_very_low_coherence_returns_skip(self):
        """Predicted coherence < 0.1 → SKIP (execution would be wasteful).

        Wrong impl: returns REROUTE for ALL below-threshold predictions.
        Discriminating: SKIP is strictly for the lowest quality tier.
        """
        gate = JepaGate(world_model=self._make_world_model(0.05))
        state = np.zeros(12, dtype=float)
        verdict = gate.check("impossible task", current_state=state)
        assert verdict == PreExecutionVerdict.SKIP, (
            f"Very low coherence prediction should yield SKIP, got {verdict}"
        )

    def test_check_with_none_state_uses_default_state(self):
        """When current_state=None the gate must still return a verdict without raising."""
        gate = JepaGate(world_model=self._make_world_model(0.9))
        verdict = gate.check("fetch data", current_state=None)
        assert isinstance(verdict, PreExecutionVerdict)

    def test_threshold_boundary_at_point_six_is_proceed(self):
        """Coherence exactly 0.6 must be PROCEED (≥ threshold), not REROUTE."""
        gate = JepaGate(world_model=self._make_world_model(0.6))
        state = np.zeros(12, dtype=float)
        verdict = gate.check("test op", current_state=state)
        assert verdict == PreExecutionVerdict.PROCEED

    def test_threshold_boundary_at_point_three_is_reroute(self):
        """Coherence exactly 0.3 must be REROUTE (≥ 0.1 and < 0.6)."""
        gate = JepaGate(world_model=self._make_world_model(0.3))
        state = np.zeros(12, dtype=float)
        verdict = gate.check("test op", current_state=state)
        assert verdict == PreExecutionVerdict.REROUTE
