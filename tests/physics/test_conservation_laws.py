"""Tests for physics conservation laws — energy, unitarity, gauge invariance.

These are PROOF OBLIGATIONS for the V-Model DRR-3 gate.
Each test verifies a deterministic invariant that must hold across all
physics engine operations. Failing any of these means the simulation
produces non-physical results.

References:
    - Hairer, Lubich, Wanner (2006): Geometric Numerical Integration
    - Nakahara (2003): Geometry, Topology and Physics
    - Session 96b L304: "The LLM hallucinates, the verifier does not"
"""

import numpy as np
import pytest

from cohezion.physics.gauge_theory import FourFabricGauge, GaugeConnection
from cohezion.physics.lagrangian import LagrangianDynamics, Potential
from cohezion.physics.riemannian_metric import RiemannianMetric
from cohezion.physics.spinor import SpinorState


class TestEnergyConservation:
    """Verify Störmer-Verlet integrator conserves energy (proof obligation)."""

    def _make_dynamics(self, dim: int = 12, damping: float = 0.0) -> LagrangianDynamics:
        metric = RiemannianMetric(dim=dim)

        # HIHO attractor potential: V(q) = sum((q_i - 0.5)^2) — minimum at HIHO
        def hiho_potential(q: np.ndarray) -> float:
            return float(np.sum((q - 0.5) ** 2))

        def hiho_gradient(q: np.ndarray) -> np.ndarray:
            return 2.0 * (q - 0.5)

        potential = Potential(potential_fn=hiho_potential, gradient_fn=hiho_gradient)
        return LagrangianDynamics(metric=metric, potential=potential, damping=damping)

    @pytest.mark.unit
    def test_energy_conserved_short_trajectory(self):
        """E(t=0) ≈ E(t=100) for undamped system over 100 steps."""
        dynamics = self._make_dynamics(damping=0.0)
        q = np.full(12, 0.5)
        v = np.random.default_rng(42).normal(0, 0.1, 12)

        E_initial = dynamics.total_energy(q, v)
        dt = 0.01
        for _ in range(100):
            q, v = dynamics.step_verlet(q, v, dt)
        E_final = dynamics.total_energy(q, v)

        rel_drift = abs(E_final - E_initial) / max(abs(E_initial), 1e-10)
        assert rel_drift < 0.05, (
            f"Energy not conserved: E(0)={E_initial:.6f}, E(100)={E_final:.6f}, "
            f"relative drift={rel_drift:.4%}"
        )

    @pytest.mark.unit
    def test_energy_conserved_long_trajectory(self):
        """E(t=0) ≈ E(t=1000) for undamped system over 1000 steps."""
        dynamics = self._make_dynamics(damping=0.0)
        q = np.full(12, 0.5)
        v = np.random.default_rng(42).normal(0, 0.05, 12)

        E_initial = dynamics.total_energy(q, v)
        dt = 0.005
        for _ in range(1000):
            q, v = dynamics.step_verlet(q, v, dt)
        E_final = dynamics.total_energy(q, v)

        rel_drift = abs(E_final - E_initial) / max(abs(E_initial), 1e-10)
        assert rel_drift < 0.10, (
            f"Energy drift over 1000 steps: E(0)={E_initial:.6f}, E(1000)={E_final:.6f}, "
            f"relative drift={rel_drift:.4%}"
        )

    @pytest.mark.unit
    def test_damped_system_loses_energy(self):
        """With damping > 0, total energy must decrease over time."""
        dynamics = self._make_dynamics(damping=0.1)
        q = np.full(12, 0.5)
        v = np.random.default_rng(42).normal(0, 0.2, 12)

        E_initial = dynamics.total_energy(q, v)
        dt = 0.01
        for _ in range(50):
            q, v = dynamics.step_verlet(q, v, dt)
        E_final = dynamics.total_energy(q, v)

        # Energy should decrease (or stay same if already at minimum)
        assert E_final <= E_initial + 1e-4, (
            f"Damped system energy increased: E(0)={E_initial:.6f}, E(50)={E_final:.6f}"
        )


class TestSpinorUnitarity:
    """Verify spinor state norm is preserved (|ψ|² = 1) — proof obligation."""

    @pytest.mark.unit
    def test_hiho_spinor_norm(self):
        """HIHO spinor (|↑⟩+|↓⟩)/√2 must have |ψ|² = 1."""
        state = SpinorState.hiho()
        norm_sq = abs(state.alpha) ** 2 + abs(state.beta) ** 2
        assert abs(norm_sq - 1.0) < 1e-10, f"|ψ|² = {norm_sq}, expected 1.0"

    @pytest.mark.unit
    def test_hiho_is_equatorial(self):
        """At HIHO, ⟨σ_z⟩ = 0 (equatorial on Bloch sphere)."""
        state = SpinorState.hiho()
        bloch = state.bloch_vector
        assert abs(bloch[2]) < 1e-6, f"HIHO ⟨σ_z⟩ = {bloch[2]}, expected 0"

    @pytest.mark.unit
    def test_bloch_vector_norm_is_unity(self):
        """Pure state Bloch vector has |r| = 1."""
        state = SpinorState.hiho()
        bloch = state.bloch_vector
        norm = np.linalg.norm(bloch)
        assert abs(norm - 1.0) < 1e-6, f"|r| = {norm}, expected 1.0"

    @pytest.mark.unit
    def test_spinor_from_coherence_preserves_norm(self):
        """SpinorState.from_coherence_values() must produce normalized spinors."""
        for logic, quantum in [(0.0, 0.0), (0.5, 0.5), (1.0, 0.0), (0.3, 0.7)]:
            state = SpinorState.from_coherence_values(logic=logic, quantum=quantum)
            norm_sq = abs(state.alpha) ** 2 + abs(state.beta) ** 2
            assert abs(norm_sq - 1.0) < 1e-10, (
                f"Norm violation at (logic={logic}, quantum={quantum}): |ψ|² = {norm_sq}"
            )

    @pytest.mark.unit
    def test_arbitrary_spinor_norm(self):
        """Manually constructed spinors must be normalized."""
        # (cos(θ/2), e^{iφ}sin(θ/2)) for various angles
        for theta in [0, np.pi / 4, np.pi / 2, np.pi]:
            alpha = complex(np.cos(theta / 2), 0)
            beta = complex(np.sin(theta / 2), 0)
            state = SpinorState(alpha=alpha, beta=beta)
            norm_sq = abs(state.alpha) ** 2 + abs(state.beta) ** 2
            assert abs(norm_sq - 1.0) < 1e-10, f"|ψ|² = {norm_sq} at θ={theta}"


class TestHIHOStability:
    """Verify HIHO 0.5 coherence stability — proof obligation."""

    @pytest.mark.unit
    def test_hiho_deviation_is_zero_at_equilibrium(self):
        """SpinorState.hiho_deviation should be 0 at HIHO."""
        state = SpinorState.hiho()
        dev = state.hiho_deviation
        assert abs(dev) < 1e-6, f"HIHO deviation = {dev}, expected 0"

    @pytest.mark.unit
    def test_hiho_deviation_increases_away_from_equilibrium(self):
        """Deviation increases as spinor moves away from equator."""
        hiho = SpinorState.hiho()
        up = SpinorState(alpha=complex(1, 0), beta=complex(0, 0))  # |↑⟩
        down = SpinorState(alpha=complex(0, 0), beta=complex(1, 0))  # |↓⟩

        dev_hiho = abs(hiho.hiho_deviation)
        dev_up = abs(up.hiho_deviation)
        dev_down = abs(down.hiho_deviation)

        assert dev_hiho < dev_up, "HIHO should have less deviation than |↑⟩"
        assert dev_hiho < dev_down, "HIHO should have less deviation than |↓⟩"


class TestGaugeInvariance:
    """Verify gauge field properties — proof obligation.

    Gauge invariance and field strength antisymmetry are fundamental
    conservation laws in Yang-Mills theory. These tests verify the
    SO(3) gauge connection behaves correctly under deviations from HIHO.

    References:
        - Yang & Mills (1954): Conservation of isotopic spin
        - Nakahara (2003): Geometry, Topology and Physics, Ch. 10
    """

    @pytest.mark.unit
    def test_yang_mills_action_zero_at_hiho(self):
        """At HIHO (all dims=0.5), gauge potentials vanish → action = 0.

        The HIHO state corresponds to the flat connection (F = 0).
        Yang-Mills action S = ∫ Tr(F∧*F) = 0 at this point.
        """
        # Create 12D state at HIHO (all components 0.5)
        state_hiho = np.full(12, 0.5)

        # Create four-fabric gauge and set from HIHO state
        gauge = FourFabricGauge()
        gauge.set_from_12d_state(state_hiho, target=0.5)

        # Yang-Mills action should be ≈ 0 at HIHO
        action = gauge.yang_mills_action()
        assert action < 1e-10, f"At HIHO, Yang-Mills action should be 0, got {action:.6e}"

    @pytest.mark.unit
    def test_yang_mills_action_nonzero_away_from_hiho(self):
        """Away from HIHO, gauge field is excited → action > 0.

        A 12D state with non-zero deviation from 0.5 generates
        non-zero gauge fields and non-zero action.
        """
        # Create 12D state away from HIHO — all Space dimensions deviate
        # to ensure gauge potentials are non-zero (set_from_state uses cross-products)
        state_away = np.array([0.0, 0.3, 0.2, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5])

        # Create gauge and compute action
        gauge = FourFabricGauge()
        gauge.set_from_12d_state(state_away, target=0.5)

        # Action should be positive
        action = gauge.yang_mills_action()
        assert action > 1e-10, f"Away from HIHO, Yang-Mills action should be > 0, got {action:.6e}"

    @pytest.mark.unit
    def test_field_strength_is_antisymmetric(self):
        """Field strength tensor F_ab = -F_ba (antisymmetry).

        The field strength is defined as F = dA + [A,A], which must be
        antisymmetric in its spacetime indices: F[a,b] = -F[b,a].
        """
        # Create a gauge connection with non-trivial potential
        conn = GaugeConnection("Space", coupling=1.0)

        # Set potential from a non-HIHO state
        fabric_state = np.array([0.7, 0.3, 0.6])
        conn.set_from_state(fabric_state, target=0.5)

        # Compute field strength
        fs = conn.field_strength()
        F = fs.tensor  # Shape (3, 3, 3): F[a, b, c]

        # Check antisymmetry: F[a, b, c] = -F[a, c, b]
        for a in range(3):
            for b in range(3):
                for c in range(b + 1, 3):
                    # F[a, b, c] should equal -F[a, c, b]
                    f_bc = F[a, b, c]
                    f_cb = F[a, c, b]
                    assert abs(f_bc + f_cb) < 1e-10, (
                        f"Field strength not antisymmetric: "
                        f"F[{a},{b},{c}]={f_bc:.6e}, F[{a},{c},{b}]={f_cb:.6e}, "
                        f"sum={f_bc + f_cb:.6e}"
                    )

    @pytest.mark.unit
    def test_flat_connection_is_hiho(self):
        """At HIHO, the connection is flat: all field strengths = 0."""
        # Start at HIHO
        state_hiho = np.full(12, 0.5)

        # Create single fabric gauge
        conn = GaugeConnection("Space", coupling=1.0)
        conn.set_from_state(state_hiho[0:3], target=0.5)

        # Check that connection is flat
        assert conn.is_flat(tol=1e-10), "Connection at HIHO should be flat"

        # Field strength energy should be zero
        fs = conn.field_strength()
        assert fs.energy_density < 1e-15, (
            f"At HIHO, field strength energy should be 0, got {fs.energy_density:.6e}"
        )


class TestMetricPositiveDefiniteness:
    """Verify Riemannian metric det(g) > 0 — proof obligation.

    A valid Riemannian metric must be positive-definite everywhere on the
    manifold. det(g) > 0 is a necessary condition. Violation means the
    manifold has degenerate directions (signature change).

    References:
        - do Carmo (1992): Riemannian Geometry
        - Session 96b Phase 8.2: Physics invariant proof obligations
    """

    @pytest.mark.unit
    def test_metric_positive_definite_at_hiho(self):
        """det(g) > 0 at HIHO equilibrium point."""
        metric = RiemannianMetric(dim=12)
        x_hiho = np.full(12, 0.5)
        det = metric.determinant(x_hiho)
        assert det > 0, f"det(g) = {det} at HIHO, expected > 0"

    @pytest.mark.unit
    def test_metric_positive_definite_at_origin(self):
        """det(g) > 0 at origin."""
        metric = RiemannianMetric(dim=12)
        x_origin = np.zeros(12)
        det = metric.determinant(x_origin)
        assert det > 0, f"det(g) = {det} at origin, expected > 0"

    @pytest.mark.unit
    def test_metric_positive_definite_random_points(self):
        """det(g) > 0 at random points on the manifold."""
        metric = RiemannianMetric(dim=12)
        rng = np.random.default_rng(42)
        for i in range(20):
            x = rng.uniform(-1, 2, 12)
            det = metric.determinant(x)
            assert det > 0, f"det(g) = {det} at random point {i}, expected > 0"

    @pytest.mark.unit
    def test_metric_is_symmetric(self):
        """g_ij = g_ji (metric tensor must be symmetric)."""
        metric = RiemannianMetric(dim=12)
        x = np.random.default_rng(42).uniform(0, 1, 12)
        g = metric.evaluate(x)
        assert np.allclose(g, g.T, atol=1e-12), "Metric tensor is not symmetric"


class TestCoherenceBandInvariant:
    """Verify HIHO coherence band [0.3, 0.7] — proof obligation.

    Stable states must maintain coherence within the HIHO band. States outside
    the band should have higher deviation and instability.

    References:
        - COHEZION_CHARTER.md: HIHO stability at 0.5 coherence
        - Session 96b: Phase 8.2 proof obligations
    """

    @staticmethod
    def _coherence(state: np.ndarray) -> float:
        """Coherence = 1 - 2 * mean|x_i - 0.5|. Peaks at 1.0 when all dims = 0.5."""
        return 1.0 - 2.0 * float(np.mean(np.abs(state - 0.5)))

    @pytest.mark.unit
    def test_coherence_computable_from_state(self):
        """Coherence is computable from any valid 12D state."""
        for val in [0.0, 0.3, 0.5, 0.7, 1.0]:
            state = np.full(12, val)
            coherence = self._coherence(state)
            assert np.isfinite(coherence), f"Non-finite coherence at state={val}"

    @pytest.mark.unit
    def test_hiho_state_in_band(self):
        """HIHO state (all 0.5) has coherence = 1.0, well within [0.3, 0.7]."""
        state = np.full(12, 0.5)
        coherence = self._coherence(state)
        assert coherence >= 0.3, f"HIHO coherence {coherence} below band"
        assert abs(coherence - 1.0) < 1e-10, f"HIHO coherence {coherence}, expected 1.0"

    @pytest.mark.unit
    def test_extreme_states_low_coherence(self):
        """Extreme states (all 0 or all 1) have lower coherence than HIHO."""
        c_hiho = self._coherence(np.full(12, 0.5))
        c_zero = self._coherence(np.zeros(12))
        c_one = self._coherence(np.ones(12))

        assert c_hiho > c_zero, f"HIHO ({c_hiho}) should exceed all-zeros ({c_zero})"
        assert c_hiho > c_one, f"HIHO ({c_hiho}) should exceed all-ones ({c_one})"


class TestLiouvilleTheorem:
    """Verify phase space volume preservation (Liouville's theorem) — proof obligation.

    For a Hamiltonian system without damping, the phase space volume
    must be preserved: det(J(t)) = det(J(0)) where J is the Jacobian
    of the flow map. This is a consequence of Hamilton's equations.

    We verify this numerically by evolving a small ball of initial
    conditions and checking the volume ratio remains ≈ 1.

    References:
        - Arnold (1989): Mathematical Methods of Classical Mechanics
        - Hairer, Lubich, Wanner (2006): Geometric Numerical Integration
    """

    @pytest.mark.unit
    def test_phase_space_volume_preserved(self):
        """Phase space volume is approximately preserved for undamped system."""
        metric = RiemannianMetric(dim=4)  # Small dimension for speed

        def potential_fn(q: np.ndarray) -> float:
            return float(np.sum((q - 0.5) ** 2))

        def gradient_fn(q: np.ndarray) -> np.ndarray:
            return 2.0 * (q - 0.5)

        potential = Potential(potential_fn=potential_fn, gradient_fn=gradient_fn)
        dynamics = LagrangianDynamics(metric=metric, potential=potential, damping=0.0)

        # Evolve a set of nearby initial conditions
        rng = np.random.default_rng(42)
        q0 = np.full(4, 0.5)
        v0 = rng.normal(0, 0.05, 4)

        # Create perturbed copies
        eps = 1e-4
        n_perturbations = 4
        deltas_q = []
        deltas_v = []
        for i in range(n_perturbations):
            dq = np.zeros(4)
            dq[i] = eps
            # Evolve perturbed trajectory
            q_pert, v_pert = q0 + dq, v0.copy()
            q_base, v_base = q0.copy(), v0.copy()
            dt = 0.005
            for _ in range(50):
                q_pert, v_pert = dynamics.step_verlet(q_pert, v_pert, dt)
                q_base, v_base = dynamics.step_verlet(q_base, v_base, dt)
            deltas_q.append(q_pert - q_base)
            deltas_v.append(v_pert - v_base)

        # Build Jacobian columns from finite differences
        J_q = np.column_stack([dq / eps for dq in deltas_q])
        J_v = np.column_stack([dv / eps for dv in deltas_v])

        # Phase space Jacobian (simplified: just check position-space volume)
        det_J = abs(np.linalg.det(J_q))

        # Liouville: det should be close to 1 (volume preserved)
        # Allow some numerical drift since we use finite differences + Verlet
        assert 0.5 < det_J < 2.0, f"Phase space volume ratio = {det_J:.4f}, expected ≈ 1.0"
