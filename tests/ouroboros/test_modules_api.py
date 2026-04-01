"""Tests for M24 disconnected modules API integration."""


import numpy as np

from cohezion.physics.hamiltonian import HamiltonianDynamics, PotentialType
from cohezion.physics.manifold_utils import SemanticLagrangeFinder
from cohezion.physics.rewards_bridge import CoherenceRatchet, RewardsBridge
from cohezion.rewards.calculator import RewardCalculator
from cohezion.simulation.emergent_detector import EmergentDetector
from cohezion.universe.triune_manifold import calculate_hiho_coherence, compute_restoring_force


class TestHamiltonianDynamics:
    def test_double_well_simulation(self):
        """Hamiltonian dynamics should evolve state toward HIHO target."""
        dynamics = HamiltonianDynamics(potential=PotentialType.DOUBLE_WELL, temperature=0.01)
        z0 = np.full((4, 12), 0.5, dtype=np.float32)
        z_final = dynamics.simulate(z0, epochs=50, seed=42)
        assert z_final.shape == (4, 12)

    def test_harmonic_converges_to_target(self):
        """Harmonic potential should drive state toward target=0.5."""
        dynamics = HamiltonianDynamics(potential=PotentialType.HARMONIC, temperature=0.001, dt=0.05)
        z0 = np.full((1, 4), 0.8, dtype=np.float32)
        z_final = dynamics.simulate(z0, epochs=200, seed=42)
        assert np.mean(np.abs(z_final - 0.5)) < 0.3

    def test_energy_computation(self):
        """Energy should be computable for any state."""
        dynamics = HamiltonianDynamics(potential=PotentialType.HIHO_WELL)
        z = np.array([[0.5, 0.5, 0.5]], dtype=np.float32)
        energy = dynamics.energy(z)
        assert energy.shape == z.shape

    def test_trajectory_recording(self):
        """simulate_with_trajectory should return checkpoints."""
        dynamics = HamiltonianDynamics(potential=PotentialType.DOUBLE_WELL)
        z0 = np.full((2, 8), 0.5, dtype=np.float32)
        trajectory = dynamics.simulate_with_trajectory(z0, epochs=30, checkpoint_interval=10)
        assert len(trajectory) >= 3  # initial + checkpoints + final


class TestManifoldUtils:
    def test_lagrange_points_stable(self):
        """Should find stable L4/L5 points for valid mass ratios."""
        finder = SemanticLagrangeFinder()
        a = np.full(12, 0.3)
        b = np.full(12, 0.7)
        result = finder.find_triangular_points(a, b, 1.0, 0.02)
        assert result["stable"] is True
        assert len(result["l4_point"]) == 12
        assert len(result["l5_point"]) == 12

    def test_lagrange_points_unstable(self):
        """Should detect instability when mass ratio exceeds Routh critical value."""
        finder = SemanticLagrangeFinder()
        a = np.full(12, 0.3)
        b = np.full(12, 0.7)
        result = finder.find_triangular_points(a, b, 0.5, 0.5)
        assert result["stable"] is False

    def test_identical_topics(self):
        """Should handle identical topic vectors gracefully."""
        finder = SemanticLagrangeFinder()
        a = np.full(12, 0.5)
        result = finder.find_triangular_points(a, a, 1.0, 1.0)
        assert result["stable"] is False


class TestTriuneManifold:
    def test_hiho_coherence_range(self):
        """Coherence should be in [0, 1]."""
        import torch

        intent = torch.randn(12)
        env = torch.randn(12)
        coh = calculate_hiho_coherence(intent, env)
        assert 0.0 <= coh <= 1.0

    def test_hiho_coherence_self(self):
        """Coherence of a vector with itself should be 1.0."""
        import torch

        vec = torch.ones(12)
        coh = calculate_hiho_coherence(vec, vec)
        assert abs(coh - 1.0) < 1e-5

    def test_restoring_force_at_hiho(self):
        """Restoring force should be zero at HIHO target (0.5)."""
        force = compute_restoring_force(0.5)
        assert abs(force) < 1e-10

    def test_restoring_force_direction(self):
        """Force should push toward 0.5 from both sides."""
        assert compute_restoring_force(0.3) > 0  # Below target, push up
        assert compute_restoring_force(0.7) < 0  # Above target, push down


class TestEmergentDetector:
    def test_detection_runs(self):
        """EmergentDetector should produce a report."""
        rng = np.random.default_rng(42)
        n_cycles, n_agents, z_dim = 50, 10, 8

        coherence = 0.5 + 0.1 * rng.standard_normal((n_cycles, n_agents))
        z_vectors = rng.standard_normal((n_cycles, n_agents, z_dim)).astype(np.float32)

        detector = EmergentDetector()
        report = detector.analyze(coherence, z_vectors, run_id="test")
        assert report.run_id == "test"
        assert report.total_cycles == 50
        assert report.complexity_score >= 0.0

    def test_phase_transition_detection(self):
        """Should detect a phase transition when coherence shifts."""
        rng = np.random.default_rng(42)
        n_cycles, n_agents, z_dim = 100, 5, 4

        coherence = np.zeros((n_cycles, n_agents))
        coherence[:50] = 0.3 + 0.02 * rng.standard_normal((50, n_agents))
        coherence[50:] = 0.8 + 0.02 * rng.standard_normal((50, n_agents))

        z_vectors = rng.standard_normal((n_cycles, n_agents, z_dim)).astype(np.float32)

        detector = EmergentDetector(phase_threshold=1.5)
        report = detector.analyze(coherence, z_vectors, run_id="phase_test")
        phase_events = [e for e in report.events if e.event_type == "phase_transition"]
        assert len(phase_events) >= 1


class TestRewardsIntegration:
    def test_reward_at_hiho(self):
        """Reward should be maximal at coherence=0.5."""
        calc = RewardCalculator()
        at_hiho = calc.calculate_score(0.5, 0)
        off_hiho = calc.calculate_score(0.1, 0)
        assert at_hiho > off_hiho

    def test_rewards_bridge_combined(self):
        """RewardsBridge should combine Gaussian + ratchet."""
        bridge = RewardsBridge()
        reward = bridge.compute(0.5, 0)
        assert 0.0 <= reward <= 1.0

    def test_ratchet_penalty(self):
        """Ratchet should penalize coherence backsliding."""
        ratchet = CoherenceRatchet(margin=0.01, penalty=1.0)
        ratchet.check(0.5)  # set high-water mark
        penalty = ratchet.check(0.1)  # big backslide
        assert penalty < 0.0

    def test_ratchet_no_penalty_on_improvement(self):
        """Ratchet should not penalize when coherence improves."""
        ratchet = CoherenceRatchet()
        ratchet.check(0.3)
        penalty = ratchet.check(0.5)  # improved toward HIHO
        assert penalty == 0.0
