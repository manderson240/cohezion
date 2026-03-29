"""Tests for Exotic Vacuum Object (EVO) model — agent lifecycle physics.

Verifies EVO lifecycle transitions, witness mark accumulation,
binding energy computation, EVO coherence metric, and serialization.
"""

import pytest

from cohezion.physics.evo_model import HIHO_BASELINE, ExoticVacuumObject


class TestLifecycle:
    """Verify the EVO state machine: vacuum -> condensing -> coherent -> dissolving -> vacuum."""

    def test_initial_state_is_vacuum(self):
        evo = ExoticVacuumObject("agent-1")
        assert evo.state == "vacuum"
        assert evo.lifetime_ticks == 0

    def test_condense_transitions_to_coherent(self):
        evo = ExoticVacuumObject("agent-1")
        evo.condense()
        assert evo.state == "coherent"

    def test_dissolve_returns_to_vacuum(self):
        evo = ExoticVacuumObject("agent-1")
        evo.condense()
        evo.coherent_phase(0.7)
        bio = evo.dissolve()
        assert evo.state == "vacuum"
        assert isinstance(bio, dict)
        assert bio["agent_id"] == "agent-1"

    def test_full_lifecycle_vacuum_to_vacuum(self):
        evo = ExoticVacuumObject("agent-1")
        assert evo.state == "vacuum"
        evo.condense()
        assert evo.state == "coherent"
        evo.coherent_phase(0.8)
        evo.produce_witness_mark("commit", "feat: add EVO model")
        evo.dissolve()
        assert evo.state == "vacuum"

    def test_cannot_condense_twice(self):
        evo = ExoticVacuumObject("agent-1")
        evo.condense()
        with pytest.raises(ValueError, match="must be 'vacuum'"):
            evo.condense()

    def test_cannot_dissolve_from_vacuum(self):
        evo = ExoticVacuumObject("agent-1")
        with pytest.raises(ValueError, match="must be 'coherent'"):
            evo.dissolve()

    def test_cannot_record_coherence_in_vacuum(self):
        evo = ExoticVacuumObject("agent-1")
        with pytest.raises(ValueError, match="Cannot record coherence"):
            evo.coherent_phase(0.5)

    def test_recondense_after_dissolve(self):
        """An agent can be reused — new EVO forms from vacuum."""
        evo = ExoticVacuumObject("agent-1")
        evo.condense()
        evo.coherent_phase(0.9)
        evo.dissolve()
        # Second lifecycle
        evo.condense()
        assert evo.state == "coherent"
        assert evo.lifetime_ticks == 0
        assert len(evo.coherence_history) == 0


class TestWitnessMarks:
    """Verify witness mark accumulation."""

    def test_witness_marks_accumulate(self):
        evo = ExoticVacuumObject("agent-1")
        evo.condense()
        evo.coherent_phase(0.7)
        evo.produce_witness_mark("commit", "fix: resolve race condition")
        evo.produce_witness_mark("decision", "chose async over threads")
        assert len(evo.witness_marks) == 2

    def test_witness_mark_returns_dict(self):
        evo = ExoticVacuumObject("agent-1")
        evo.condense()
        evo.coherent_phase(0.8)
        result = evo.produce_witness_mark("vault_note", "learned about EVOs")
        assert result["mark_type"] == "vault_note"
        assert result["content"] == "learned about EVOs"
        assert result["tick"] == 1

    def test_cannot_produce_mark_in_vacuum(self):
        evo = ExoticVacuumObject("agent-1")
        with pytest.raises(ValueError, match="Cannot produce witness marks"):
            evo.produce_witness_mark("commit", "should fail")


class TestBindingEnergy:
    """Verify binding energy tracks coherence above HIHO baseline."""

    def test_binding_energy_from_high_coherence(self):
        evo = ExoticVacuumObject("agent-1")
        evo.condense()
        evo.coherent_phase(0.8)  # 0.3 above baseline
        evo.coherent_phase(0.9)  # 0.4 above baseline
        assert evo.binding_energy == pytest.approx(0.7, abs=1e-6)

    def test_no_binding_energy_below_baseline(self):
        evo = ExoticVacuumObject("agent-1")
        evo.condense()
        evo.coherent_phase(0.3)  # Below HIHO_BASELINE
        evo.coherent_phase(0.2)
        assert evo.binding_energy == 0.0

    def test_baseline_is_half(self):
        assert HIHO_BASELINE == 0.5


class TestEVOCoherenceMetric:
    """Verify the composite EVO coherence metric."""

    def test_zero_for_empty_history(self):
        evo = ExoticVacuumObject("agent-1")
        assert evo.evo_coherence_metric() == 0.0

    def test_high_metric_for_productive_agent(self):
        evo = ExoticVacuumObject("agent-1")
        evo.condense()
        for _ in range(50):
            evo.coherent_phase(0.85)
            evo.produce_witness_mark("commit", "productive work")
        metric = evo.evo_coherence_metric()
        assert metric > 0.5, f"Productive agent should have high metric, got {metric}"

    def test_low_metric_for_incoherent_agent(self):
        evo = ExoticVacuumObject("agent-1")
        evo.condense()
        # Wildly oscillating coherence, no witness marks
        for i in range(10):
            evo.coherent_phase(1.0 if i % 2 == 0 else 0.0)
        metric = evo.evo_coherence_metric()
        # self_coupling will be low due to high variance
        assert metric < 0.7, f"Incoherent agent should have lower metric, got {metric}"

    def test_metric_in_unit_range(self):
        evo = ExoticVacuumObject("agent-1")
        evo.condense()
        evo.coherent_phase(0.6)
        metric = evo.evo_coherence_metric()
        assert 0.0 <= metric <= 1.0


class TestSerialization:
    """Verify to_dict produces complete, correct output."""

    def test_to_dict_has_required_keys(self):
        evo = ExoticVacuumObject("agent-1")
        evo.condense()
        evo.coherent_phase(0.75)
        evo.produce_witness_mark("commit", "initial commit")
        d = evo.to_dict()
        required = {
            "agent_id",
            "state",
            "lifetime_ticks",
            "binding_energy",
            "evo_coherence_metric",
            "coherence_history",
            "witness_marks",
            "mean_coherence",
        }
        assert required.issubset(d.keys())

    def test_to_dict_values_are_serializable(self):
        """All values must be JSON-serializable (no numpy, no dataclass objects)."""
        import json

        evo = ExoticVacuumObject("agent-1")
        evo.condense()
        evo.coherent_phase(0.8)
        evo.produce_witness_mark("decision", "use EVO model")
        d = evo.to_dict()
        serialized = json.dumps(d)
        assert isinstance(serialized, str)

    def test_dissolve_biography_captures_state(self):
        evo = ExoticVacuumObject("agent-1")
        evo.condense()
        evo.coherent_phase(0.9)
        evo.produce_witness_mark("commit", "feat: EVO")
        bio = evo.dissolve()
        # Biography captured during dissolving state
        assert bio["lifetime_ticks"] == 1
        assert len(bio["witness_marks"]) == 1
        assert bio["binding_energy"] == pytest.approx(0.4, abs=1e-6)
