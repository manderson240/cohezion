"""Tests for ASI Pathways, Friction Models, and Collective Superintelligence.
=============================================================================
Validates:
1. Intelligence tiers, pathway definitions, and friction enumerations.
2. Multi-agent scaling laws with sublinear parallelization and bureaucracy decay.
3. Hyperbolic recursive self-improvement simulation under friction damping.
4. Universal Legg-Hutter intelligence metric approximation.
5. Substrate migration harness and lossless state replication across silicon tiers.
"""

import pytest

from cohezion.compound.asi_pathways import (
    ASIFriction,
    ASIPathway,
    DigitalIntelligenceAdvantages,
    HyperbolicRSISimulator,
    IntelligenceTier,
    LeggHutterApproximator,
    MultiAgentScalingLaw,
    SubstrateMigrationHarness,
)


def test_intelligence_tiers_and_pathways():
    """Validates categorization of intelligence and formal ASI pathways."""
    assert IntelligenceTier.NARROW_AI.value == "narrow_ai"
    assert IntelligenceTier.COMPETENT_AGI.value == "competent_agi"
    assert IntelligenceTier.EXPERT_AGI.value == "expert_agi"
    assert IntelligenceTier.ASI.value == "artificial_superintelligence"
    assert IntelligenceTier.UNIVERSAL_AI.value == "universal_ai"

    # All 4 pathways
    pathways = {p.value for p in ASIPathway}
    assert "scaling_compute_models_data" in pathways
    assert "algorithmic_paradigm_shifts" in pathways
    assert "recursive_self_improvement" in pathways
    assert "multi_agent_group_agency" in pathways

    # All 6 frictions
    frictions = {f.value for f in ASIFriction}
    assert "data_wall" in frictions
    assert "economic_and_natural_resource_demand" in frictions
    assert "neural_paradigm_is_insufficient" in frictions
    assert "research_gets_harder" in frictions
    assert "abstraction_barrier" in frictions
    assert "deliberate_slowdown" in frictions


def test_digital_intelligence_advantages():
    """Validates digital intelligence scaling advantages struct."""
    adv = DigitalIntelligenceAdvantages(
        io_speed_bps=1e11,
        internal_processing_flops=1e15,
        working_memory_bytes=128 * (1024**3),
        substrate_independent=True,
        lossless_replication=True,
        high_bandwidth_sharing=True,
    )
    assert adv.substrate_independent is True
    assert adv.lossless_replication is True
    assert adv.high_bandwidth_sharing is True
    assert adv.working_memory_bytes == 128 * 1024**3


def test_multi_agent_scaling_law():
    """Validates collective swarm intelligence scaling and ASI threshold check."""
    scaling = MultiAgentScalingLaw(individual_iq=100.0, alpha=0.85, beta=0.05)

    assert scaling.compute_collective_intelligence(0) == 0.0
    assert scaling.compute_collective_intelligence(1) == 100.0

    score_10 = scaling.compute_collective_intelligence(10)
    score_100 = scaling.compute_collective_intelligence(100)
    score_1000 = scaling.compute_collective_intelligence(1000)

    # Collective intelligence grows with N
    assert score_10 > 100.0
    assert score_100 > score_10
    assert score_1000 > score_100

    # Sublinear scaling (alpha < 1.0 plus bureaucracy damping)
    # 10 agents with alpha=0.85 should produce roughly ~600-700
    assert 400.0 < score_10 < 800.0

    # Check ASI threshold detection
    assert scaling.is_superintelligent(1, threshold=500.0) is False
    assert scaling.is_superintelligent(100, threshold=500.0) is True


def test_hyperbolic_rsi_simulator():
    """Validates recursive self-improvement simulation with friction damping."""
    sim = HyperbolicRSISimulator(
        initial_intelligence=100.0,
        k_acceleration=0.02,
        gamma_hyperbolic=0.25,
    )

    # Simulation with countermeasures (synthetic data, specialized silicon)
    trajectory_damped = sim.simulate_trajectory(steps=10, dt=0.1, counter_measures_active=True)
    assert len(trajectory_damped) == 11
    assert trajectory_damped[0] == (0.0, 100.0)

    # Intelligence should monotonically increase
    prev_i = 100.0
    for _t, i in trajectory_damped[1:]:
        assert i >= prev_i
        prev_i = i

    final_damped = trajectory_damped[-1][1]

    # Simulation without countermeasures (higher friction)
    trajectory_undamped = sim.simulate_trajectory(steps=10, dt=0.1, counter_measures_active=False)
    final_undamped = trajectory_undamped[-1][1]

    # Active countermeasures achieve higher net intelligence
    assert final_damped >= final_undamped


def test_legg_hutter_approximator():
    """Validates universal Legg-Hutter score calculation over algorithmic priors."""
    # Complexities K(mu) and values V_mu
    complexities = [1, 2, 3, 4]  # Weights: 1/2, 1/4, 1/8, 1/16
    values = [1.0, 1.0, 1.0, 1.0]

    score = LeggHutterApproximator.evaluate_policy(complexities, values)
    assert pytest.approx(score, rel=1e-3) == 1.0

    # Half score
    values_half = [0.5, 0.5, 0.5, 0.5]
    score_half = LeggHutterApproximator.evaluate_policy(complexities, values_half)
    assert pytest.approx(score_half, rel=1e-3) == 0.5

    # Simple tasks high, complex tasks zero
    values_skewed = [1.0, 0.0, 0.0, 0.0]
    score_skewed = LeggHutterApproximator.evaluate_policy(complexities, values_skewed)
    # Total weight = 0.5 + 0.25 + 0.125 + 0.0625 = 0.9375
    # Weighted score = 0.5 * 1.0 = 0.5 -> 0.5 / 0.9375 = 0.5333...
    assert pytest.approx(score_skewed, rel=1e-3) == 0.5 / 0.9375

    # Mismatched lengths raise ValueError
    with pytest.raises(ValueError, match="Mismatched"):
        LeggHutterApproximator.evaluate_policy([1, 2], [1.0])


def test_substrate_migration_harness():
    """Validates lossless state replication and heterogeneous lane transfer audits."""
    state1 = {"agent_id": "architect_01", "poincare_dim": 2048, "weights_crc": "0xABC123"}
    state2 = {"poincare_dim": 2048, "agent_id": "architect_01", "weights_crc": "0xABC123"}
    state_corrupt = {"agent_id": "architect_01", "poincare_dim": 2047, "weights_crc": "0xABC123"}

    assert SubstrateMigrationHarness.verify_lossless_replication(state1, state2) is True
    assert SubstrateMigrationHarness.verify_lossless_replication(state1, state_corrupt) is False

    # Audit migration between valid lanes
    audit = SubstrateMigrationHarness.audit_substrate_migration(
        source_lane="npu_flm",
        target_lane="cpu_zen5",
        state_size_bytes=100 * 1024 * 1024,  # 100 MB
    )
    assert audit["status"] == "APPROVED"
    assert audit["lossless_guarantee"] is True
    assert audit["estimated_transfer_latency_ms"] > 0.0

    # Invalid lane raises ValueError
    with pytest.raises(ValueError, match="Invalid hardware lane"):
        SubstrateMigrationHarness.audit_substrate_migration(
            source_lane="unknown_lane",
            target_lane="cpu_zen5",
            state_size_bytes=1024,
        )
