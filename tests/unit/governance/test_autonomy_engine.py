"""Unit tests for the AutonomyEngine governance tier system."""

import pytest

from cohezion.governance.autonomy_engine import (
    DEMOTION_WINDOW,
    PROMOTION_WINDOW,
    TIER_THRESHOLDS,
    AgentAutonomyState,
    AutonomyEngine,
    AutonomyTier,
    get_autonomy_engine,
)


# ---------------------------------------------------------------------------
# AutonomyTier enum
# ---------------------------------------------------------------------------


class TestAutonomyTier:
    def test_tier_levels_are_ordered(self):
        tiers = list(AutonomyTier)
        assert tiers[0].level == 0
        assert tiers[-1].level == len(tiers) - 1

    def test_void_is_level_zero(self):
        assert AutonomyTier.VOID.level == 0

    def test_hiho_is_highest_level(self):
        assert AutonomyTier.HIHO.level == 5

    def test_level_comparison_works(self):
        assert AutonomyTier.SO12.level > AutonomyTier.VOID.level
        assert AutonomyTier.HIHO.level > AutonomyTier.Z2_4.level


# ---------------------------------------------------------------------------
# AgentAutonomyState
# ---------------------------------------------------------------------------


class TestAgentAutonomyState:
    def test_default_tier_is_void(self):
        state = AgentAutonomyState(agent_id="test")
        assert state.current_tier == AutonomyTier.VOID

    def test_recent_coherence_returns_last_window(self):
        state = AgentAutonomyState(agent_id="test")
        state.coherence_history = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7]
        recent = state.recent_coherence
        assert len(recent) == PROMOTION_WINDOW
        assert recent[-1] == 0.7

    def test_average_coherence_empty_returns_zero(self):
        state = AgentAutonomyState(agent_id="test")
        assert state.average_coherence == 0.0

    def test_average_coherence_computes_mean(self):
        state = AgentAutonomyState(agent_id="test")
        state.coherence_history = [0.4, 0.5, 0.6]
        assert abs(state.average_coherence - 0.5) < 1e-9


# ---------------------------------------------------------------------------
# AutonomyEngine — registration and basic getters
# ---------------------------------------------------------------------------


class TestAutonomyEngineRegistration:
    def test_register_agent_starts_at_void(self):
        engine = AutonomyEngine()
        state = engine.register_agent("agent-1")
        assert state.current_tier == AutonomyTier.VOID

    def test_get_state_auto_registers_unknown_agent(self):
        engine = AutonomyEngine()
        state = engine.get_state("new-agent")
        assert state.agent_id == "new-agent"
        assert state.current_tier == AutonomyTier.VOID

    def test_get_tier_returns_current_tier(self):
        engine = AutonomyEngine()
        engine.register_agent("agent-x")
        assert engine.get_tier("agent-x") == AutonomyTier.VOID


# ---------------------------------------------------------------------------
# AutonomyEngine — promotion
# ---------------------------------------------------------------------------


class TestAutonomyEnginePromotion:
    def test_promote_void_to_so12_after_window(self):
        engine = AutonomyEngine()
        threshold = TIER_THRESHOLDS[AutonomyTier.SO12]
        for _ in range(PROMOTION_WINDOW):
            engine.record_coherence("a", threshold + 0.01)
        assert engine.get_tier("a") == AutonomyTier.SO12

    def test_no_promotion_below_threshold(self):
        engine = AutonomyEngine()
        threshold = TIER_THRESHOLDS[AutonomyTier.SO12]
        for _ in range(PROMOTION_WINDOW):
            engine.record_coherence("a", threshold - 0.01)
        assert engine.get_tier("a") == AutonomyTier.VOID

    def test_partial_window_does_not_promote(self):
        engine = AutonomyEngine()
        threshold = TIER_THRESHOLDS[AutonomyTier.SO12]
        for _ in range(PROMOTION_WINDOW - 1):
            engine.record_coherence("a", threshold + 0.05)
        assert engine.get_tier("a") == AutonomyTier.VOID

    def test_promote_through_multiple_tiers(self):
        engine = AutonomyEngine()
        # Feed values just above HIHO threshold to climb all tiers
        for _ in range(PROMOTION_WINDOW * 6):
            engine.record_coherence("climber", 0.55)
        assert engine.get_tier("climber") == AutonomyTier.HIHO

    def test_transition_recorded_on_promotion(self):
        engine = AutonomyEngine()
        threshold = TIER_THRESHOLDS[AutonomyTier.SO12]
        for _ in range(PROMOTION_WINDOW):
            engine.record_coherence("a", threshold + 0.05)
        state = engine.get_state("a")
        assert len(state.tier_transitions) >= 1
        assert state.tier_transitions[-1]["reason"] == "promotion"


# ---------------------------------------------------------------------------
# AutonomyEngine — demotion
# ---------------------------------------------------------------------------


class TestAutonomyEngineDemotion:
    def _promote_to(self, engine: AutonomyEngine, agent: str, tier: AutonomyTier) -> None:
        """Helper: push agent up to target tier via high coherence."""
        for _ in range(PROMOTION_WINDOW * tier.level):
            engine.record_coherence(agent, 0.55)

    def test_demotion_on_sustained_low_coherence(self):
        engine = AutonomyEngine()
        self._promote_to(engine, "b", AutonomyTier.SO12)
        assert engine.get_tier("b") == AutonomyTier.SO12
        # Feed very low coherence to trigger demotion
        for _ in range(DEMOTION_WINDOW):
            engine.record_coherence("b", 0.0)
        assert engine.get_tier("b") == AutonomyTier.VOID

    def test_no_demotion_at_void(self):
        engine = AutonomyEngine()
        for _ in range(DEMOTION_WINDOW):
            engine.record_coherence("c", 0.0)
        assert engine.get_tier("c") == AutonomyTier.VOID

    def test_demotion_transition_recorded(self):
        engine = AutonomyEngine()
        self._promote_to(engine, "d", AutonomyTier.SO12)
        for _ in range(DEMOTION_WINDOW):
            engine.record_coherence("d", 0.0)
        state = engine.get_state("d")
        reasons = [t["reason"] for t in state.tier_transitions]
        assert "demotion" in reasons


# ---------------------------------------------------------------------------
# AutonomyEngine — violation handling
# ---------------------------------------------------------------------------


class TestAutonomyEngineViolation:
    def test_minor_violation_injects_one_penalty(self):
        engine = AutonomyEngine()
        before = len(engine.get_state("e").coherence_history)
        engine.record_violation("e", severity=0.1)
        after = len(engine.get_state("e").coherence_history)
        assert after == before + 1

    def test_major_violation_injects_full_window_penalty(self):
        engine = AutonomyEngine()
        before = len(engine.get_state("f").coherence_history)
        engine.record_violation("f", severity=1.0)
        after = len(engine.get_state("f").coherence_history)
        assert after == before + PROMOTION_WINDOW

    def test_violation_demotes_elevated_agent(self):
        engine = AutonomyEngine()
        # Promote to SO12
        threshold = TIER_THRESHOLDS[AutonomyTier.SO12]
        for _ in range(PROMOTION_WINDOW):
            engine.record_coherence("g", threshold + 0.05)
        assert engine.get_tier("g") == AutonomyTier.SO12
        # Critical violation should demote
        engine.record_violation("g", severity=1.0)
        assert engine.get_tier("g") == AutonomyTier.VOID

    def test_violation_returns_current_tier(self):
        engine = AutonomyEngine()
        result = engine.record_violation("h", severity=0.1)
        assert isinstance(result, AutonomyTier)


# ---------------------------------------------------------------------------
# AutonomyEngine — physics coherence bridge (Stealthskater invariant S3)
# ---------------------------------------------------------------------------


class TestAutonomyEnginePhysicsBridge:
    def test_lenr_bridge_promotes_agent(self):
        engine = AutonomyEngine()
        threshold = TIER_THRESHOLDS[AutonomyTier.SO12]
        for _ in range(PROMOTION_WINDOW):
            engine.record_physics_coherence("lenr-agent", "lenr", threshold + 0.05)
        assert engine.get_tier("lenr-agent") == AutonomyTier.SO12

    def test_evo_bridge_routes_coherence(self):
        engine = AutonomyEngine()
        tier = engine.record_physics_coherence("evo-agent", "evo", 0.3)
        assert isinstance(tier, AutonomyTier)
        state = engine.get_state("evo-agent")
        assert len(state.coherence_history) == 1

    def test_diaelectric_bridge_routes_coherence(self):
        engine = AutonomyEngine()
        tier = engine.record_physics_coherence("dia-agent", "diaelectric", 0.25)
        assert isinstance(tier, AutonomyTier)

    def test_ionic_cluster_bridge_routes_coherence(self):
        engine = AutonomyEngine()
        tier = engine.record_physics_coherence("ionic-agent", "ionic_cluster", 0.35)
        assert isinstance(tier, AutonomyTier)

    def test_hiho_threshold_is_same_across_substrates(self):
        """S3: nuclear-scale LENR threshold == bioelectric HIHO threshold."""
        from cohezion.physics.lenr import LENRHamiltonian

        lenr = LENRHamiltonian()
        assert lenr.reaction_threshold == TIER_THRESHOLDS[AutonomyTier.HIHO]
        assert lenr.reaction_threshold == 0.5

    def test_coherence_clamped_to_unit_interval(self):
        engine = AutonomyEngine()
        engine.record_physics_coherence("clamp-agent", "lenr", 2.5)
        state = engine.get_state("clamp-agent")
        assert state.coherence_history[-1] == 1.0

        engine.record_physics_coherence("clamp-agent", "lenr", -0.5)
        assert state.coherence_history[-1] == 0.0


# ---------------------------------------------------------------------------
# AutonomyEngine — can_perform
# ---------------------------------------------------------------------------


class TestAutonomyEngineCanPerform:
    def test_void_agent_cannot_perform_observe(self):
        engine = AutonomyEngine()
        assert not engine.can_perform("void-agent", AutonomyTier.SO12)

    def test_agent_can_perform_at_or_below_tier(self):
        engine = AutonomyEngine()
        # Promote to SO12
        threshold = TIER_THRESHOLDS[AutonomyTier.SO12]
        for _ in range(PROMOTION_WINDOW):
            engine.record_coherence("so12-agent", threshold + 0.05)
        assert engine.can_perform("so12-agent", AutonomyTier.VOID)
        assert engine.can_perform("so12-agent", AutonomyTier.SO12)
        assert not engine.can_perform("so12-agent", AutonomyTier.SO3_4)


# ---------------------------------------------------------------------------
# AutonomyEngine — get_all_states
# ---------------------------------------------------------------------------


class TestAutonomyEngineGetAllStates:
    def test_get_all_states_empty_engine(self):
        engine = AutonomyEngine()
        assert engine.get_all_states() == {}

    def test_get_all_states_returns_summary_for_each_agent(self):
        engine = AutonomyEngine()
        engine.register_agent("a1")
        engine.register_agent("a2")
        states = engine.get_all_states()
        assert set(states.keys()) == {"a1", "a2"}
        for info in states.values():
            assert "tier" in info
            assert "tier_level" in info
            assert "coherence_avg" in info
            assert "history_len" in info
            assert "transitions" in info


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------


class TestAutonomyEngineSingleton:
    def test_get_autonomy_engine_returns_same_instance(self):
        engine_a = get_autonomy_engine()
        engine_b = get_autonomy_engine()
        assert engine_a is engine_b


# ---------------------------------------------------------------------------
# HIHO attractor (integration)
# ---------------------------------------------------------------------------


class TestHIHOAttractor:
    def test_sustained_hiho_coherence_reaches_sovereign_tier(self):
        """Agents sustaining coherence near 0.5 naturally converge to HIHO in <= 30 steps."""
        import random

        engine = AutonomyEngine()
        rng = random.Random(42)

        for _step in range(30):
            coherence = 0.50 + rng.gauss(0, 0.04)
            tier = engine.record_physics_coherence("hiho-attractor", "lenr", coherence)
            if tier == AutonomyTier.HIHO:
                return  # Reached HIHO within budget

        pytest.fail("Agent did not reach HIHO within 30 steps of sustained coherence near 0.5")
