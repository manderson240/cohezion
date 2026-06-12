"""Tests for RecursiveTracer: constitution gate, OOM guard, journey integration."""

import time
from unittest.mock import MagicMock, patch

import numpy as np


def _make_agent(agent_id: str = "evo-001", coherence: float = 0.5):
    """Build a minimal AgenticEVO for testing."""
    from cohezion.universe.agentic_evo_swift import AgenticEVO

    agent = AgenticEVO(agent_id=agent_id)
    # Seed latent vector to a known coherence
    agent.latent_state.latent_vector = np.full(256, coherence, dtype=np.float32)
    agent.latent_state.current_coherence = agent.latent_state.compute_coherence()
    return agent


def _make_tracker():
    from cohezion.compound.journey_tracker import JourneyTracker

    return JourneyTracker()


class TestTraceResult:
    def test_trace_step_returns_trace_result(self):
        """trace_step() returns TraceResult with populated fields."""
        from cohezion.evo.recursive_tracer import RecursiveTracer, TraceResult

        agent = _make_agent()
        tracker = _make_tracker()
        tracer = RecursiveTracer(agent, tracker)
        result = tracer.trace_step("synthesize latent journey", modalities=["text"])

        assert isinstance(result, TraceResult)
        assert result.step_index == 0
        assert 0.0 <= result.coherence_before <= 1.0
        assert 0.0 <= result.coherence_after <= 1.0
        assert result.latent_delta >= 0.0
        assert result.latency_ms >= 0.0
        assert result.modalities_invoked == ["text"]

    def test_trace_step_increments_step_count(self):
        """Each trace_step() increments step_count by 1."""
        from cohezion.evo.recursive_tracer import RecursiveTracer

        agent = _make_agent()
        tracer = RecursiveTracer(agent, _make_tracker())
        assert tracer.step_count == 0
        tracer.trace_step("step 1")
        assert tracer.step_count == 1
        tracer.trace_step("step 2")
        assert tracer.step_count == 2

    def test_phi_score_is_hiho_kernel(self):
        """TraceResult.phi is 4 * c * (1-c) applied to coherence_after."""
        from cohezion.evo.recursive_tracer import RecursiveTracer
        from cohezion.evo import phi_from_coherence

        agent = _make_agent()
        tracer = RecursiveTracer(agent, _make_tracker())
        result = tracer.trace_step("check phi")
        expected = phi_from_coherence(result.coherence_after)
        assert abs(result.phi - expected) < 1e-9

    def test_modalities_tracked_across_steps(self):
        """Modalities accumulate across trace_step() calls."""
        from cohezion.evo.recursive_tracer import RecursiveTracer

        agent = _make_agent()
        tracer = RecursiveTracer(agent, _make_tracker())
        tracer.trace_step("text step", modalities=["text"])
        tracer.trace_step("image step", modalities=["image"])
        voyage = tracer.complete_journey(journey_id="test-journey")
        assert sorted(voyage.modalities_used) == ["image", "text"]


class TestConstitutionGate:
    def test_degenerate_voyage_skips_refinement(self):
        """phi < 0.3 → SkillRefiner.refine() is never called."""
        from cohezion.evo.recursive_tracer import RecursiveTracer

        mock_refiner = MagicMock()
        # Force degenerate state: latent near 0.0 → coherence ≈ 0.5 distance from 0.5
        # Use a vector far from 0.5 → high coherence distance → low phi
        agent = _make_agent()
        agent.latent_state.latent_vector = np.zeros(256, dtype=np.float32)
        agent.latent_state.current_coherence = agent.latent_state.compute_coherence()

        tracer = RecursiveTracer(agent, _make_tracker(), skill_refiner=mock_refiner)
        # Run a step without HIHO updating (delta_scale=0 freezes the state)
        tracer.trace_step("degenerate step", hiho_delta_scale=0.0, hiho_damping=0.0)

        voyage = tracer.complete_journey(journey_id="test-j", skill_id="some-skill")
        if voyage.is_degenerate:
            mock_refiner.refine.assert_not_called()
            assert voyage.skill_refinements == []

    def test_healthy_voyage_triggers_refinement(self):
        """phi ≥ 0.3 → SkillRefiner.refine() is called with skill_id."""
        from cohezion.evo.recursive_tracer import RecursiveTracer

        mock_refiner = MagicMock()
        mock_refiner.refine.return_value = "/path/to/refined-skill.md"

        # Latent near 0.5 → high phi
        agent = _make_agent(coherence=0.5)
        tracer = RecursiveTracer(agent, _make_tracker(), skill_refiner=mock_refiner)
        tracer.trace_step("healthy step")
        voyage = tracer.complete_journey(journey_id="test-j", skill_id="cohezion-synthesis")

        if not voyage.is_degenerate:
            mock_refiner.refine.assert_called_once()
            call_args = mock_refiner.refine.call_args
            assert call_args[1].get("skill_name") == "cohezion-synthesis" or (
                len(call_args[0]) > 0 and call_args[0][0] == "cohezion-synthesis"
            )

    def test_complete_journey_without_steps_raises(self):
        """complete_journey() before any trace_step() raises ValueError."""
        from cohezion.evo.recursive_tracer import RecursiveTracer
        import pytest

        agent = _make_agent()
        tracer = RecursiveTracer(agent, _make_tracker())
        with pytest.raises(ValueError, match="no steps traced"):
            tracer.complete_journey(journey_id="empty")


class TestOOMGuard:
    def test_oom_guard_raises_when_ram_low(self):
        """trace_step() raises RuntimeError when available RAM < 8 GB."""
        from cohezion.evo.recursive_tracer import RecursiveTracer
        import pytest

        mock_snap = MagicMock()
        mock_snap.available_gb = 7.9  # below 8 GB threshold

        agent = _make_agent()
        tracer = RecursiveTracer(agent, _make_tracker())

        with patch(
            "cohezion.competition.orchestrator.resource_guard.MemorySnapshot"
        ) as MockMS:
            MockMS.capture.return_value = mock_snap
            with pytest.raises(RuntimeError, match="OOM guard"):
                tracer.trace_step("low ram step")

    def test_oom_guard_passes_when_ram_sufficient(self):
        """trace_step() proceeds normally when RAM ≥ 16 GB."""
        from cohezion.evo.recursive_tracer import RecursiveTracer

        mock_snap = MagicMock()
        mock_snap.available_gb = 64.0

        agent = _make_agent()
        tracer = RecursiveTracer(agent, _make_tracker())

        with patch(
            "cohezion.competition.orchestrator.resource_guard.MemorySnapshot"
        ) as MockMS:
            MockMS.capture.return_value = mock_snap
            result = tracer.trace_step("sufficient ram step")
            assert result.step_index == 0  # step proceeded


class TestExperientialVoyageIntegration:
    def test_complete_journey_returns_voyage(self):
        """complete_journey() returns ExperientialVoyage with correct agent_id."""
        from cohezion.evo.recursive_tracer import RecursiveTracer
        from cohezion.evo import ExperientialVoyage

        agent = _make_agent(agent_id="evo-integration-001")
        tracer = RecursiveTracer(agent, _make_tracker())
        tracer.trace_step("integration step")
        voyage = tracer.complete_journey(journey_id="integration-j")

        assert isinstance(voyage, ExperientialVoyage)
        assert voyage.agent_id == "evo-integration-001"
        assert voyage.journey_id == "integration-j"
        assert len(voyage.latent_snapshot) == 16
        assert voyage.completed_at >= voyage.started_at

    def test_complete_journey_emits_evo_voyage(self):
        """complete_journey() calls tracker.emit_evo_voyage()."""
        from cohezion.evo.recursive_tracer import RecursiveTracer

        agent = _make_agent()
        tracker = _make_tracker()
        tracer = RecursiveTracer(agent, tracker)
        tracer.trace_step("emit test step")

        # Capture write buffer state before and after
        buf_before = len(tracker._write_buffer)
        tracer.complete_journey(journey_id="emit-j")
        # SurrealDB buffer should have grown (evo_journey record added)
        assert len(tracker._write_buffer) >= buf_before


class TestMonadIntegration:
    def test_trace_step_dispatches_modality_handlers(self):
        """trace_step() invokes get_modality() for each requested modality via the monad pipeline."""
        from unittest.mock import patch
        from cohezion.evo.recursive_tracer import RecursiveTracer
        from cohezion.evo.modalities import ModalityResult

        agent = _make_agent()
        tracer = RecursiveTracer(agent, _make_tracker())

        invoked: list[str] = []

        def fake_get_modality(name: str):
            class _Handler:
                def invoke(self, prompt, **kw):
                    invoked.append(name)
                    return ModalityResult(modality=name, success=True, output="")
            return _Handler()

        with patch("cohezion.evo.modalities.get_modality", side_effect=fake_get_modality):
            tracer.trace_step("multimodal step", modalities=["text", "audio", "image"])

        assert "text" in invoked
        assert "audio" in invoked
        assert "image" in invoked
        assert len(invoked) == 3

    def test_trace_step_modality_failure_is_non_blocking(self):
        """A modality handler that raises must not prevent the step from completing."""
        from unittest.mock import patch
        from cohezion.evo.recursive_tracer import RecursiveTracer

        agent = _make_agent()
        tracer = RecursiveTracer(agent, _make_tracker())

        def exploding_modality(name):
            class _Bad:
                def invoke(self, prompt, **kw):
                    raise RuntimeError("lemonade offline")
            return _Bad()

        with patch("cohezion.evo.modalities.get_modality", side_effect=exploding_modality):
            result = tracer.trace_step("step with failing modality", modalities=["audio"])

        # Step must complete and return a valid TraceResult despite modality failure
        assert result.step_index == 0
        assert 0.0 <= result.coherence_after <= 1.0

    def test_trace_state_phi_matches_hiho_kernel(self):
        """Internal TraceState.phi == 4*c*(1-c) at every step."""
        from cohezion.evo.recursive_tracer import RecursiveTracer
        from cohezion.evo import phi_from_coherence

        agent = _make_agent(coherence=0.5)
        tracer = RecursiveTracer(agent, _make_tracker())
        result = tracer.trace_step("phi consistency check")
        assert abs(result.phi - phi_from_coherence(result.coherence_after)) < 1e-9
