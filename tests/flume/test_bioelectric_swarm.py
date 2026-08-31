"""Unit tests for Bioelectric Swarm Morphogenesis & Dynamic Gap-Junction Topology."""

import numpy as np
import pytest

from cohezion.flume.bioelectric_swarm import (
    RESTING_V_MEM,
    V_MEM_MAX,
    V_MEM_MIN,
    BioelectricNode,
    BioelectricSwarm,
)


class TestBioelectricNode:
    """Test suite for BioelectricNode class."""

    def test_node_initialization_defaults(self):
        node = BioelectricNode(node_id=1)
        assert node.node_id == 1
        assert node.v_mem == RESTING_V_MEM
        assert node.is_healthy is True
        assert node.state_vector.shape == (12,)
        assert np.all(node.state_vector == 0.0)

    def test_membrane_potential_clamping(self):
        node = BioelectricNode(node_id=1, v_mem=-100.0)
        assert node.v_mem == V_MEM_MIN

        node.polarize(0.0)
        assert node.v_mem == V_MEM_MAX

        node.hyperpolarize(100.0)
        assert node.v_mem == V_MEM_MIN

        node.depolarize(100.0)
        assert node.v_mem == V_MEM_MAX

    def test_gap_junction_setting(self):
        node = BioelectricNode(node_id=1)
        node.set_gap_junction(2, 0.75)
        assert node.get_gap_junction(2) == pytest.approx(0.75)
        assert node.get_gap_junction(3) == 0.0

        # Clamping
        node.set_gap_junction(2, 1.5)
        assert node.get_gap_junction(2) == 1.0

    def test_fault_injection(self):
        node = BioelectricNode(node_id=1, state_vector=np.ones(12))
        assert node.is_healthy is True

        node.inject_fault("oom")
        assert node.is_healthy is False
        assert np.all(node.state_vector == 0.0)

        node.inject_fault("corruption")
        assert node.is_healthy is False
        assert np.any(np.isnan(node.state_vector))


class TestBioelectricSwarm:
    """Test suite for BioelectricSwarm class."""

    def test_swarm_initialization(self):
        swarm = BioelectricSwarm(n_nodes=12, diffusion_coeff=0.5, time_constant=1.0)
        assert swarm.n_nodes == 12
        assert len(swarm.nodes) == 12
        assert swarm.calculate_base_light_cone_radius() == pytest.approx(np.sqrt(6.0))

    def test_light_cone_expansion_boost(self):
        swarm = BioelectricSwarm(n_nodes=12, diffusion_coeff=0.5, time_constant=1.0)

        # Uncoupled -> boost = 1.0
        swarm.set_uniform_coupling(0.0)
        base_r = swarm.calculate_base_light_cone_radius()
        r_uncoupled = swarm.calculate_light_cone_radius()
        assert r_uncoupled == pytest.approx(base_r)

        # Coupled kappa >= 0.5 -> boost >= 9.0x
        swarm.set_uniform_coupling(0.5)
        r_coupled = swarm.calculate_light_cone_radius()
        boost = swarm.calculate_gap_junction_boost()

        assert boost >= 9.0
        assert r_coupled >= 9.0 * base_r
        assert r_coupled >= 4.0

    def test_self_healing_recovery(self):
        swarm = BioelectricSwarm(n_nodes=12)
        swarm.set_uniform_coupling(0.6)

        # Inject faults into nodes 2 and 5
        swarm.nodes[2].inject_fault("oom")
        swarm.nodes[5].inject_fault("corruption")

        assert set(swarm.detect_corrupted_nodes()) == {2, 5}

        # Perform self-healing
        heal_result = swarm.heal_swarm()

        assert heal_result["healed_count"] == 2
        assert heal_result["elapsed_ms"] < 50.0
        assert heal_result["success"] is True
        assert len(swarm.detect_corrupted_nodes()) == 0

        # Verify state vectors were reconstructed with finite non-zero values
        assert swarm.nodes[2].is_healthy is True
        assert swarm.nodes[5].is_healthy is True
        assert np.all(np.isfinite(swarm.nodes[2].state_vector))
        assert np.all(np.isfinite(swarm.nodes[5].state_vector))
