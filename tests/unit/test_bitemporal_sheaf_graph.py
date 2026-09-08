"""Unit tests for Bi-Temporal Graphiti Knowledge Graph and Sheaf Laplacian Consistency.
========================================================================================

Verifies:
1. Bi-temporal fact representation with dual-time grounding (valid_time vs assertion_time).
2. Non-destructive retraction (setting retracted_at preserves historical truth).
3. Dynamic A-MEM synapse evolution (Hebbian co-activation strengthens link, decay reduces weight).
4. Sheaf Laplacian computation: L_Sigma = delta^T delta.
5. Topological consistency score: detecting inter-agent consensus vs semantic divergence.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import numpy as np
import pytest

from cohezion.knowledge_graph.bitemporal_sheaf_graph import (
    BiTemporalFact,
    BiTemporalSheafGraphEngine,
    DynamicSynapse,
    SheafConsistencyResult,
)


def test_bitemporal_fact_creation_and_dual_time():
    now = datetime.now(UTC)
    fact = BiTemporalFact(
        fact_id="fact_1",
        subject="Agent_A",
        predicate="located_in",
        object_val="Cluster_NPU",
        valid_from=now - timedelta(hours=2),
        valid_to=None,
        asserted_at=now,
        agent_id="Agent_A",
        confidence=0.95,
    )
    assert fact.is_valid_at(now - timedelta(hours=1)) is True
    assert fact.is_valid_at(now - timedelta(hours=3)) is False
    assert fact.is_asserted_at(now + timedelta(seconds=1)) is True
    assert fact.is_asserted_at(now - timedelta(seconds=1)) is False


def test_bitemporal_retraction_preserves_provenance():
    t0 = datetime(2026, 9, 3, 12, 0, tzinfo=UTC)
    t1 = datetime(2026, 9, 3, 14, 0, tzinfo=UTC)
    t2 = datetime(2026, 9, 3, 16, 0, tzinfo=UTC)

    fact = BiTemporalFact(
        fact_id="fact_2",
        subject="Cache",
        predicate="status",
        object_val="warm",
        valid_from=t0,
        valid_to=None,
        asserted_at=t0,
    )

    # Retract at t1
    fact.retract(retracted_at=t1)
    assert fact.retracted_at == t1

    # As of t0.5 (between t0 and t1), the fact was believed
    assert fact.is_active_belief_at(t0 + timedelta(hours=1)) is True

    # As of t2 (after t1), the fact is retracted
    assert fact.is_active_belief_at(t2) is False


def test_dynamic_synapse_hebbian_coactivation_and_decay():
    now = datetime.now(UTC)
    synapse = DynamicSynapse(
        source_id="neuron_1",
        target_id="neuron_2",
        weight=0.5,
        coactivations=0,
        decay_rate=0.1,
        last_activated=now - timedelta(days=1),
    )

    # Co-activate twice
    synapse.coactivate(now)
    assert synapse.coactivations == 1
    assert synapse.weight > 0.5
    assert synapse.last_activated == now

    synapse.coactivate(now)
    assert synapse.coactivations == 2

    # Simulate decay over 5 days
    later = now + timedelta(days=5)
    decayed_weight = synapse.compute_decayed_weight(as_of=later)
    assert decayed_weight < synapse.weight


def test_sheaf_laplacian_concordance_and_divergence():
    engine = BiTemporalSheafGraphEngine()

    # Two agents with identical beliefs in 3D feature space (Concordance)
    v_a = np.array([1.0, 0.0, 0.5])
    v_b = np.array([1.0, 0.0, 0.5])
    agent_stalks = {"agent_a": v_a, "agent_b": v_b}

    # Identity restriction map on communication edge
    edges = [("agent_a", "agent_b")]
    restriction_maps = {("agent_a", "agent_b"): (np.eye(3), np.eye(3))}

    result = engine.evaluate_sheaf_laplacian(agent_stalks, edges, restriction_maps)
    assert isinstance(result, SheafConsistencyResult)
    assert result.dirichlet_energy == pytest.approx(0.0, abs=1e-6)
    assert result.is_consistent is True
    assert result.harmonic_dimension == 3

    # Divergent beliefs
    v_b_divergent = np.array([-1.0, 0.0, -0.5])
    agent_stalks_divergent = {"agent_a": v_a, "agent_b": v_b_divergent}
    result_div = engine.evaluate_sheaf_laplacian(agent_stalks_divergent, edges, restriction_maps)
    assert result_div.dirichlet_energy > 0.1
    assert result_div.is_consistent is False


def test_sheaf_harmonic_diffusion():
    engine = BiTemporalSheafGraphEngine(consistency_threshold=0.01)
    # Stalks start discordant
    stalks = {
        "agent_a": np.array([1.0, 0.0, 0.0]),
        "agent_b": np.array([0.0, 1.0, 0.0]),
    }
    edges = [("agent_a", "agent_b")]
    # Initial Dirichlet energy = ||[1, 0, 0] - [0, 1, 0]||^2 = 2.0
    res_before = engine.evaluate_sheaf_laplacian(stalks, edges, {})
    assert res_before.dirichlet_energy == pytest.approx(2.0)
    assert not res_before.is_consistent

    # Apply 10 steps of harmonic diffusion
    cur_stalks = stalks
    for _ in range(10):
        cur_stalks = engine.harmonic_diffusion_step(cur_stalks, edges, {}, step_size=0.1)

    res_after = engine.evaluate_sheaf_laplacian(cur_stalks, edges, {})
    # Energy should have decayed significantly toward consensus
    assert res_after.dirichlet_energy < res_before.dirichlet_energy
    assert res_after.dirichlet_energy < 0.5
