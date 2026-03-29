"""Tests for bioelectric network model — Levin-inspired collective intelligence.

Verifies network diffusion dynamics, cognitive light cone scaling,
HIHO percolation threshold, and information capacity calculations.
"""

import numpy as np
import pytest

from cohezion.physics.bioelectric_model import BioelectricNetwork


class TestNetworkDynamics:
    """Verify the cable equation dynamics."""

    def test_network_creates_with_correct_size(self):
        net = BioelectricNetwork(n_cells=8)
        assert net.n_cells == 8
        assert len(net.v_mem) == 8

    def test_initial_potential_near_resting(self):
        net = BioelectricNetwork(n_cells=16, resting_potential=-0.5)
        assert np.allclose(net.v_mem, -0.5, atol=0.2)

    def test_uncoupled_cells_relax_to_resting(self):
        """Without gap junctions, each cell relaxes to V_rest independently."""
        net = BioelectricNetwork(n_cells=4, resting_potential=-0.3)
        net.v_mem = np.array([0.5, -0.8, 0.2, -0.1])  # Far from rest
        net.simulate(n_steps=500, dt=0.1)
        assert np.allclose(net.v_mem, -0.3, atol=0.05)

    def test_coupled_cells_synchronize(self):
        """With strong gap junctions, cells converge to the same potential."""
        net = BioelectricNetwork(n_cells=4, resting_potential=0.0)
        net.v_mem = np.array([1.0, -1.0, 0.5, -0.5])
        net.set_full_conductance(5.0)
        net.simulate(n_steps=500, dt=0.01)
        # All cells should be at approximately the same value
        assert np.std(net.v_mem) < 0.05

    def test_simulation_returns_trajectory(self):
        net = BioelectricNetwork(n_cells=4)
        traj = net.simulate(n_steps=10)
        assert traj.shape == (11, 4)  # n_steps + 1

    def test_potentials_stay_bounded(self):
        """V_mem stays within [-1, 1]."""
        net = BioelectricNetwork(n_cells=8)
        net.v_mem = np.array([1.0, -1.0, 0.9, -0.9, 0.5, -0.5, 0.0, 0.0])
        net.set_full_conductance(10.0)
        net.simulate(n_steps=100, dt=0.01)
        assert np.all(net.v_mem >= -1.0)
        assert np.all(net.v_mem <= 1.0)


class TestCoherence:
    """Verify coherence metric (synchronization measure)."""

    def test_fully_synchronized_is_one(self):
        net = BioelectricNetwork(n_cells=4)
        net.v_mem = np.full(4, 0.3)
        assert net.coherence() == pytest.approx(1.0)

    def test_fully_spread_is_zero(self):
        net = BioelectricNetwork(n_cells=4)
        net.v_mem = np.array([-1.0, 1.0, -1.0, 1.0])
        assert net.coherence() == pytest.approx(0.0)

    def test_partial_sync_between_zero_and_one(self):
        net = BioelectricNetwork(n_cells=4)
        net.v_mem = np.array([0.3, 0.4, 0.5, 0.6])
        c = net.coherence()
        assert 0.0 < c < 1.0

    def test_single_cell_coherence_is_one(self):
        net = BioelectricNetwork(n_cells=1)
        assert net.coherence() == 1.0


class TestCognitiveLightCone:
    """Verify Levin's cognitive light cone computation."""

    def test_uncoupled_has_zero_radius(self):
        net = BioelectricNetwork(n_cells=4)
        cone = net.cognitive_light_cone()
        assert cone.radius == 0.0

    def test_coupled_has_positive_radius(self):
        net = BioelectricNetwork(n_cells=4)
        net.set_full_conductance(1.0)
        cone = net.cognitive_light_cone()
        assert cone.radius > 0.0

    def test_stronger_coupling_larger_cone(self):
        """R_c ∝ √(D×τ) — higher D (stronger coupling) → larger cone."""
        net_weak = BioelectricNetwork(n_cells=8)
        net_weak.set_full_conductance(0.1)
        r_weak = net_weak.cognitive_light_cone().radius

        net_strong = BioelectricNetwork(n_cells=8)
        net_strong.set_full_conductance(10.0)
        r_strong = net_strong.cognitive_light_cone().radius

        assert r_strong > r_weak


class TestPercolation:
    """Verify HIHO percolation threshold detection."""

    def test_uncoupled_not_percolated(self):
        net = BioelectricNetwork(n_cells=8)
        result = net.percolation_analysis()
        assert not result.is_percolated
        assert result.cluster_count == 8  # Each cell is its own cluster

    def test_fully_coupled_is_percolated(self):
        net = BioelectricNetwork(n_cells=8)
        net.set_full_conductance(1.0)
        result = net.percolation_analysis()
        assert result.is_percolated
        assert result.largest_cluster_size == 8
        assert result.cluster_count == 1

    def test_ring_topology_is_percolated(self):
        """Ring connects all cells → single cluster."""
        net = BioelectricNetwork(n_cells=8)
        net.set_uniform_conductance(1.0)
        result = net.percolation_analysis()
        assert result.is_percolated

    def test_partial_coupling_creates_clusters(self):
        """Coupling some but not all cells creates multiple clusters."""
        net = BioelectricNetwork(n_cells=8)
        # Connect cells 0-3 and 4-7 separately
        for i in range(3):
            net.set_conductance(i, i + 1, 1.0)
        for i in range(4, 7):
            net.set_conductance(i, i + 1, 1.0)
        result = net.percolation_analysis()
        assert result.cluster_count == 2


class TestInformationCapacity:
    """Verify information capacity calculations."""

    def test_capacity_increases_with_cells(self):
        net_small = BioelectricNetwork(n_cells=4)
        net_large = BioelectricNetwork(n_cells=16)
        assert net_large.information_capacity() > net_small.information_capacity()

    def test_capacity_increases_with_resolution(self):
        net = BioelectricNetwork(n_cells=8)
        cap_coarse = net.information_capacity(v_resolution=0.1)
        cap_fine = net.information_capacity(v_resolution=0.001)
        assert cap_fine > cap_coarse

    def test_capacity_positive(self):
        net = BioelectricNetwork(n_cells=8)
        assert net.information_capacity() > 0


class TestHIHODeviation:
    """Verify HIHO deviation metric."""

    def test_synchronized_at_half(self):
        """Coherence=1 → deviation = |1 - 0.5| = 0.5."""
        net = BioelectricNetwork(n_cells=4)
        net.v_mem = np.full(4, 0.3)  # All same → coherence=1
        assert net.hiho_deviation() == pytest.approx(0.5)

    def test_fully_spread(self):
        """Coherence=0 → deviation = |0 - 0.5| = 0.5."""
        net = BioelectricNetwork(n_cells=4)
        net.v_mem = np.array([-1.0, 1.0, -1.0, 1.0])
        assert net.hiho_deviation() == pytest.approx(0.5)

    def test_hiho_state_minimal_deviation(self):
        """At coherence ≈ 0.5, deviation is minimal."""
        net = BioelectricNetwork(n_cells=4)
        # Set values with spread ~1.0 → coherence ~0.5
        net.v_mem = np.array([0.0, 0.5, 0.5, 1.0])
        assert net.hiho_deviation() < 0.3


class TestSerialization:
    """Verify API serialization."""

    def test_to_dict_has_required_fields(self):
        net = BioelectricNetwork(n_cells=4)
        net.set_full_conductance(1.0)
        data = net.to_dict()
        assert "n_cells" in data
        assert "v_mem" in data
        assert "coherence" in data
        assert "hiho_deviation" in data
        assert "information_capacity_bits" in data
        assert "cognitive_light_cone" in data
        assert "percolation" in data
        assert data["cognitive_light_cone"]["is_collective"] is True

    def test_to_dict_values_are_json_serializable(self):
        """All values must be JSON-safe (no numpy types)."""
        import json

        net = BioelectricNetwork(n_cells=4)
        net.set_full_conductance(0.5)
        data = net.to_dict()
        json.dumps(data)  # Should not raise
