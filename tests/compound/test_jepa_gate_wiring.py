"""V-model tests for JW1: JepaGate.last_coherence attribute + CompoundExecutor wiring.

JW1 harness invariant:
  - JepaGate.last_coherence is set to the predicted coherence float after check()
  - Fail-open paths (None world_model, exception) leave last_coherence = 1.0
  - CompoundExecutor accepts jepa_gate kwarg and records jepa_coherence in metrics
  - SKIP verdict causes execute_task() to return early (no execute_fn call)

T1: structural — last_coherence attribute exists and initializes to 1.0
T2: discriminating behavioral — last_coherence updated correctly per verdict path
"""

from __future__ import annotations

import contextlib
import inspect
from unittest.mock import MagicMock, patch

import numpy as np

from cohezion.compound.jepa_gate import JepaGate, PreExecutionVerdict


# ---------------------------------------------------------------------------
# T1: Structural invariants
# ---------------------------------------------------------------------------


class TestJW1Structural:
    def test_last_coherence_attribute_exists(self):
        """JepaGate must have a last_coherence attribute (JW1)."""
        gate = JepaGate(world_model=None)
        assert hasattr(gate, "last_coherence"), "JepaGate must expose last_coherence"

    def test_last_coherence_initializes_to_one(self):
        """last_coherence must start at 1.0 (optimistic/fail-open default)."""
        gate = JepaGate(world_model=None)
        assert gate.last_coherence == 1.0

    def test_executor_accepts_jepa_gate_kwarg(self):
        """CompoundExecutor.__init__ must accept jepa_gate= kwarg."""
        from cohezion.compound.executor import CompoundExecutor

        sig = inspect.signature(CompoundExecutor.__init__)
        assert "jepa_gate" in sig.parameters, (
            "CompoundExecutor.__init__ must accept jepa_gate= parameter"
        )

    def test_executor_stores_jepa_gate(self):
        """CompoundExecutor must store _jepa_gate attribute."""
        from cohezion.compound.executor import CompoundExecutor

        src = inspect.getsource(CompoundExecutor.__init__)
        assert "_jepa_gate" in src


# ---------------------------------------------------------------------------
# T2: Discriminating behavioral tests for last_coherence
# ---------------------------------------------------------------------------


class TestJW1Behavioral:
    def _stub_world_model(self, coherence: float):
        class _Stub:
            def predict_next_state(self, state, action):
                return np.full(12, float(coherence))

        return _Stub()

    def test_fail_open_none_model_leaves_last_coherence_at_one(self):
        """Fail-open path (None model) must not change last_coherence from 1.0.

        Wrong impl: sets last_coherence to 0.0 by default on fail-open.
        Discriminating: only 1.0 is correct for the fail-open case.
        """
        gate = JepaGate(world_model=None)
        gate.check("some task")
        assert gate.last_coherence == 1.0, (
            f"Fail-open path must leave last_coherence=1.0, got {gate.last_coherence}"
        )

    def test_normal_check_updates_last_coherence(self):
        """After check() with a real world model, last_coherence == predicted value.

        Wrong impl: does not set last_coherence at all (stays 1.0 even with real model).
        Discriminating: only updates when world model returns different value.
        """
        gate = JepaGate(world_model=self._stub_world_model(0.4))
        gate.check("test task", current_state=np.zeros(12))
        assert abs(gate.last_coherence - 0.4) < 1e-6, (
            f"last_coherence should be 0.4 (the predicted value), got {gate.last_coherence}"
        )

    def test_last_coherence_differs_from_init_after_real_check(self):
        """After a low-coherence prediction, last_coherence must NOT equal 1.0.

        This is the key discriminating test: the attribute must actually change.
        Wrong impl: sets it to 1.0 unconditionally.
        """
        gate = JepaGate(world_model=self._stub_world_model(0.05))
        gate.check("test task")
        assert gate.last_coherence != 1.0, (
            "last_coherence should change from 1.0 after a low-coherence prediction"
        )
        assert gate.last_coherence < 0.1

    def test_exception_in_world_model_resets_to_one(self):
        """When world model raises, last_coherence must revert to 1.0 (fail-open).

        Wrong impl: leaves last_coherence at whatever it was before the exception.
        """

        class _BrokenJEPA:
            def predict_next_state(self, state, action):
                raise RuntimeError("simulated JEPA failure")

        gate = JepaGate(world_model=_BrokenJEPA())
        gate.check("broken task")
        assert gate.last_coherence == 1.0, (
            "Exception in world model should set last_coherence=1.0 (fail-open)"
        )

    def test_proceed_verdict_sets_high_coherence(self):
        """PROCEED verdict (coherence ≥ 0.6) must result in last_coherence ≥ 0.6."""
        gate = JepaGate(world_model=self._stub_world_model(0.8))
        verdict = gate.check("task")
        assert verdict == PreExecutionVerdict.PROCEED
        assert gate.last_coherence >= 0.6

    def test_skip_verdict_sets_very_low_coherence(self):
        """SKIP verdict (coherence < 0.1) must result in last_coherence < 0.1."""
        gate = JepaGate(world_model=self._stub_world_model(0.03))
        verdict = gate.check("task")
        assert verdict == PreExecutionVerdict.SKIP
        assert gate.last_coherence < 0.1

    def test_sequential_checks_update_last_coherence(self):
        """Each check() call must overwrite last_coherence with the latest prediction."""
        gate = JepaGate(world_model=self._stub_world_model(0.9))
        gate.check("first task")
        assert abs(gate.last_coherence - 0.9) < 1e-6

        # Swap to a low-coherence model and re-check
        gate._world_model = self._stub_world_model(0.2)
        gate.check("second task")
        assert abs(gate.last_coherence - 0.2) < 1e-6, (
            "last_coherence should update on every check() call"
        )


# ---------------------------------------------------------------------------
# T3: CompoundExecutor integration — jepa_coherence in metrics
# ---------------------------------------------------------------------------


class TestJW1ExecutorWiring:
    """Verify that jepa_coherence flows into degradation_metrics when gate is wired."""

    def _make_executor_with_gate(self, gate: JepaGate):
        """Build a minimal CompoundExecutor with a JepaGate and mock DegradationDetector."""
        from cohezion.compound.executor import CompoundExecutor

        mock_mcp = MagicMock()
        mock_degradation = MagicMock()
        mock_degradation.check_degradation.return_value = []

        executor = CompoundExecutor(
            mcp_client=mock_mcp,
            enable_guardrails=False,
            enable_skill_refinement=False,
            enable_alignment_analysis=False,
            degradation_detector=mock_degradation,
            jepa_gate=gate,
        )
        return executor, mock_degradation

    def _stub_world_model(self, coherence: float):
        class _Stub:
            def predict_next_state(self, state, action):
                return np.full(12, float(coherence))

        return _Stub()

    def test_jepa_coherence_in_degradation_metrics_when_gate_wired(self):
        """When jepa_gate is wired, degradation_detector receives jepa_coherence.

        Wrong impl: jepa_coherence never reaches the degradation_metrics dict.
        Discriminating: check_degradation must be called with a dict containing
        jepa_coherence when the gate returns a non-None verdict.
        """
        gate = JepaGate(world_model=self._stub_world_model(0.75))
        executor, mock_degradation = self._make_executor_with_gate(gate)

        # Patch the execute_fn to return a simple result
        def _dummy_execute(guidance):
            return ("done", {"coherence": 0.7})

        with (
            patch.object(executor.logger, "log_execution_start", return_value=""),
            patch.object(executor.logger, "log_execution_result"),
            contextlib.suppress(Exception),
        ):
            executor.execute_task(
                task_description="test task",
                skill_name="test_skill",
                operation_type="generate",
                execute_fn=_dummy_execute,
            )

        # Find the check_degradation call and verify jepa_coherence was included
        assert mock_degradation.check_degradation.called, (
            "check_degradation must be called when degradation_detector is wired"
        )
        call_args = mock_degradation.check_degradation.call_args
        if call_args is not None:
            passed_metrics = call_args[0][0] if call_args[0] else {}
            assert "jepa_coherence" in passed_metrics, (
                f"jepa_coherence must be in degradation_metrics, got keys: {list(passed_metrics.keys())}"
            )
            assert abs(passed_metrics["jepa_coherence"] - 0.75) < 1e-6

    def test_skip_verdict_prevents_execute_fn_from_running(self):
        """When JepaGate returns SKIP, execute_fn must NOT be called.

        Wrong impl: calls execute_fn even on SKIP verdict.
        Discriminating: execute_fn call count is 0 after SKIP.
        """
        gate = JepaGate(world_model=self._stub_world_model(0.02))
        executor, _ = self._make_executor_with_gate(gate)

        execute_fn_call_count = [0]

        def _tracked_execute(guidance):
            execute_fn_call_count[0] += 1
            return ("done", {})

        with (
            patch.object(executor.logger, "log_execution_start", return_value=""),
            patch.object(executor.logger, "log_execution_result"),
        ):
            result = executor.execute_task(
                task_description="hopeless task",
                skill_name="test_skill",
                operation_type="generate",
                execute_fn=_tracked_execute,
            )

        assert execute_fn_call_count[0] == 0, (
            f"execute_fn must not run on SKIP verdict, was called {execute_fn_call_count[0]} times"
        )
        assert not result.success
        assert "jepa_verdict" in result.metrics or "skip" in result.output.lower()
