"""Greenfield tests for cohezion.governance (Z7).

Targets the most-testable surfaces of the governance package:
  - AutonomyEngine: registration, coherence recording, tier promotion/demotion
  - flume_bridge: pure helper functions (similarity, projection)

Concierge and knowledge_bridge are intentionally skipped here — they perform
significant filesystem I/O at construction (loading routing history, writing
to the user's vault) that isn't safe to exercise in a default test environment.
"""

from __future__ import annotations

import math

import numpy as np
import pytest

from cohezion.governance.autonomy_engine import (
    DEMOTION_WINDOW,
    PROMOTION_WINDOW,
    TIER_THRESHOLDS,
    AgentAutonomyState,
    AutonomyEngine,
    AutonomyTier,
)
from cohezion.governance.flume_bridge import (
    FLUME_DIM,
    agent_state_to_patch_center,
    data_product_similarity,
    encode_data_product_description,
    encode_prompt,
    flume_route_similarity,
)


# -----------------------------------------------------------------------------
# AutonomyEngine
# -----------------------------------------------------------------------------


def test_autonomy_tier_levels_are_ordered():
    """Tiers form a strictly increasing ladder VOID(0) -> HIHO(5)."""
    tiers = list(AutonomyTier)
    levels = [t.level for t in tiers]
    assert levels == sorted(levels)
    assert AutonomyTier.VOID.level == 0
    assert AutonomyTier.HIHO.level == len(tiers) - 1
    # Threshold table covers every tier
    for tier in tiers:
        assert tier in TIER_THRESHOLDS


def test_register_agent_starts_at_void():
    engine = AutonomyEngine()
    state = engine.register_agent("agent-A")
    assert state.current_tier == AutonomyTier.VOID
    assert engine.get_tier("agent-A") == AutonomyTier.VOID
    assert engine.get_tier("never-registered") == AutonomyTier.VOID


def test_record_coherence_auto_registers_unknown_agent():
    engine = AutonomyEngine()
    tier = engine.record_coherence("auto-agent", 0.1)
    assert tier == AutonomyTier.VOID
    # The agent is now tracked
    assert "auto-agent" in engine.get_all_states()


def test_record_coherence_clamps_input_to_unit_interval():
    engine = AutonomyEngine()
    state = engine.register_agent("clamp-agent")
    engine.record_coherence("clamp-agent", -5.0)
    engine.record_coherence("clamp-agent", 99.0)
    assert state.coherence_history[0] == 0.0
    assert state.coherence_history[1] == 1.0


def test_sustained_high_coherence_promotes_through_tiers():
    """Feeding HIHO-level coherence promotes one tier per PROMOTION_WINDOW samples."""
    engine = AutonomyEngine()
    engine.register_agent("climber")
    # Each promotion step needs PROMOTION_WINDOW samples >= the next tier's threshold.
    # Feed a generous batch to climb several rungs.
    final_tier = AutonomyTier.VOID
    for _ in range(PROMOTION_WINDOW * (len(AutonomyTier) - 1)):
        final_tier = engine.record_coherence("climber", 0.95)
    assert final_tier == AutonomyTier.HIHO
    # Transition log should record at least one promotion
    state = engine._agents["climber"]
    promotions = [t for t in state.tier_transitions if t["reason"] == "promotion"]
    assert len(promotions) >= 1


def test_sustained_low_coherence_demotes():
    engine = AutonomyEngine()
    engine.register_agent("faller")
    # Climb to at least SO12 first
    for _ in range(PROMOTION_WINDOW):
        engine.record_coherence("faller", 0.5)
    starting_tier = engine.get_tier("faller")
    assert starting_tier.level >= AutonomyTier.SO12.level
    # Then crash with sustained zero coherence
    for _ in range(DEMOTION_WINDOW * 2):
        engine.record_coherence("faller", 0.0)
    assert engine.get_tier("faller").level < starting_tier.level


def test_can_perform_compares_tier_levels():
    engine = AutonomyEngine()
    state = engine.register_agent("performer")
    state.current_tier = AutonomyTier.U1_4
    assert engine.can_perform("performer", AutonomyTier.SO12) is True
    assert engine.can_perform("performer", AutonomyTier.U1_4) is True
    assert engine.can_perform("performer", AutonomyTier.HIHO) is False
    # Unknown agent defaults to VOID — only VOID-tier actions are allowed
    assert engine.can_perform("unknown", AutonomyTier.VOID) is True
    assert engine.can_perform("unknown", AutonomyTier.SO12) is False


def test_get_all_states_summarises_each_agent():
    engine = AutonomyEngine()
    engine.register_agent("a")
    engine.register_agent("b")
    engine.record_coherence("a", 0.4)
    snapshot = engine.get_all_states()
    assert set(snapshot.keys()) == {"a", "b"}
    assert snapshot["a"]["history_len"] == 1
    assert snapshot["b"]["history_len"] == 0
    for entry in snapshot.values():
        for key in ("tier", "tier_level", "coherence_avg", "transitions"):
            assert key in entry


def test_agent_state_average_with_no_history_is_zero():
    state = AgentAutonomyState(agent_id="x")
    assert state.average_coherence == 0.0
    assert state.recent_coherence == []


# -----------------------------------------------------------------------------
# flume_bridge
# -----------------------------------------------------------------------------


def test_encode_prompt_returns_normalised_vector_of_correct_dim():
    vec = encode_prompt("hello world")
    assert isinstance(vec, np.ndarray)
    assert vec.shape == (FLUME_DIM,)
    # The hash fallback normalises to unit length; even the VAE path will
    # return a finite-norm vector.
    norm = float(np.linalg.norm(vec))
    assert math.isfinite(norm) and norm > 0.0


def test_encode_prompt_is_deterministic_for_identical_input():
    a = encode_prompt("identical text")
    b = encode_prompt("identical text")
    np.testing.assert_allclose(a, b)


def test_flume_route_similarity_self_match_is_high():
    embedding = encode_prompt("genesis physics observer patch")
    sim = flume_route_similarity(embedding, "genesis physics observer patch")
    assert sim > 0.99
    # Allow small float overshoot above 1.0 (cosine on unit-norm float32 vectors).
    assert 0.0 <= sim <= 1.0 + 1e-5


def test_flume_route_similarity_zero_norm_returns_zero():
    zero = np.zeros(FLUME_DIM, dtype=np.float32)
    # Right-hand side will encode to a non-zero vector but LHS norm == 0
    sim = flume_route_similarity(zero, "any prompt")
    assert sim == 0.0


def test_agent_state_to_patch_center_returns_valid_bloch_angles():
    # Construct a 12D state where rotation = +1 and precession = -1
    state = np.zeros(12)
    state[6] = 1.0  # rotation
    state[7] = -1.0  # precession
    theta, phi = agent_state_to_patch_center(state)
    assert 0.0 <= theta <= math.pi + 1e-9
    assert 0.0 <= phi <= 2 * math.pi + 1e-9
    # rotation = 1 -> theta = 0
    assert theta == pytest.approx(0.0, abs=1e-9)
    # precession = -1 -> phi = 0
    assert phi == pytest.approx(0.0, abs=1e-9)


def test_agent_state_to_patch_center_pads_short_input():
    short = np.array([0.5, 0.5])  # length 2
    theta, phi = agent_state_to_patch_center(short)
    # Should not raise and should produce valid angles
    assert 0.0 <= theta <= math.pi + 1e-9
    assert 0.0 <= phi <= 2 * math.pi + 1e-9


def test_data_product_similarity_returns_unit_interval():
    sim = data_product_similarity("agent journey checkpoints", "agent state snapshots")
    assert 0.0 <= sim <= 1.0


def test_encode_data_product_description_matches_encode_prompt():
    a = encode_data_product_description("checkpoint storage")
    b = encode_prompt("checkpoint storage")
    np.testing.assert_allclose(a, b)
