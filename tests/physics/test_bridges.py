"""Tests for stealthskater physics bridges: DielectricField, LENRHamiltonian, IonicClusterState."""

import numpy as np
import pytest

from cohezion.physics.dielectric import DielectricField
from cohezion.physics.ionic_cluster import IonicClusterState
from cohezion.physics.lenr import LENRHamiltonian


class TestLENRHamiltonian:
    def test_reaction_threshold_is_hiho(self) -> None:
        h = LENRHamiltonian()
        assert h.reaction_threshold == 0.5

    def test_reaction_rate_peaks_at_hiho(self) -> None:
        h = LENRHamiltonian()
        assert h.reaction_rate(0.5) == pytest.approx(1.0)

    def test_reaction_rate_vanishes_at_extremes(self) -> None:
        h = LENRHamiltonian()
        assert h.reaction_rate(0.0) == pytest.approx(0.0)
        assert h.reaction_rate(1.0) == pytest.approx(0.0)

    def test_reaction_rate_symmetric_about_half(self) -> None:
        h = LENRHamiltonian()
        for delta in [0.1, 0.2, 0.3]:
            assert h.reaction_rate(0.5 - delta) == pytest.approx(h.reaction_rate(0.5 + delta))

    def test_reaction_rate_beta_binomial_kernel(self) -> None:
        h = LENRHamiltonian()
        c = 0.3
        expected = 4.0 * c * (1.0 - c)
        assert h.reaction_rate(c) == pytest.approx(expected, rel=1e-6)

    def test_high_coherence_triggers_event(self) -> None:
        h = LENRHamiltonian()
        assert h.reaction_rate(0.9) > 0.0
        assert h.reaction_rate(0.9) < h.reaction_rate(0.5)

    def test_record_coherence_event_routes_to_autonomy_engine(self) -> None:
        """LENR bridge must call record_physics_coherence (preserves 'lenr' source label)."""
        from cohezion.governance.autonomy_engine import (
            PROMOTION_WINDOW,
            AutonomyEngine,
            AutonomyTier,
        )

        engine = AutonomyEngine()
        h = LENRHamiltonian(agent_id="test-lenr")
        for _ in range(PROMOTION_WINDOW):
            h.record_coherence_event(0.52, autonomy_engine=engine)
        assert engine.get_tier("test-lenr") == AutonomyTier.SO12

    def test_record_coherence_event_fallback_for_old_engine(self) -> None:
        """Fallback: engines without record_physics_coherence use record_coherence."""

        class MinimalEngine:
            calls: list = []

            def record_coherence(self, agent_id: str, coherence: float) -> None:
                MinimalEngine.calls.append((agent_id, coherence))

        MinimalEngine.calls = []
        h = LENRHamiltonian(agent_id="lenr-fallback")
        h.record_coherence_event(0.5, autonomy_engine=MinimalEngine())
        assert len(MinimalEngine.calls) == 1
        assert MinimalEngine.calls[0] == ("lenr-fallback", 0.5)


class TestIonicClusterState:
    def test_hiho_equilibrium_at_half_density(self) -> None:
        s = IonicClusterState(plasma_density=0.5)
        assert s.hiho_equilibrium() is True

    def test_hiho_equilibrium_false_at_extremes(self) -> None:
        assert IonicClusterState(plasma_density=0.0).hiho_equilibrium() is False
        assert IonicClusterState(plasma_density=1.0).hiho_equilibrium() is False

    def test_hiho_equilibrium_within_tolerance(self) -> None:
        assert IonicClusterState(plasma_density=0.48).hiho_equilibrium() is True
        assert IonicClusterState(plasma_density=0.52).hiho_equilibrium() is True

    def test_hiho_equilibrium_symmetric_at_exact_tolerance_boundary(self) -> None:
        """Float precision guard: density=0.55 (= 0.5 + tolerance) must return True.

        Without the +1e-9 epsilon guard, 0.55 - 0.5 = 0.050000000000000044 in IEEE 754,
        which is > 0.05, causing an asymmetric band where upper boundary excludes 0.55.
        """
        assert IonicClusterState(plasma_density=0.45).hiho_equilibrium() is True
        assert IonicClusterState(plasma_density=0.55).hiho_equilibrium() is True
        assert IonicClusterState(plasma_density=0.44).hiho_equilibrium() is False
        assert IonicClusterState(plasma_density=0.56).hiho_equilibrium() is False

    def test_density_outside_equilibrium(self) -> None:
        assert IonicClusterState(plasma_density=0.0).hiho_equilibrium() is False
        assert IonicClusterState(plasma_density=0.99).hiho_equilibrium() is False

    def test_same_hiho_threshold_as_lenr(self) -> None:
        h = LENRHamiltonian()
        s = IonicClusterState(plasma_density=h.reaction_threshold)
        assert s.hiho_equilibrium() is True


class TestDielectricField:
    def test_vacuum_is_flat_gauge(self) -> None:
        d = DielectricField()
        assert d.mean_permittivity == pytest.approx(1.0, rel=1e-6)

    def test_biefield_brown_force_shape(self) -> None:
        d = DielectricField()
        f = d.biefield_brown_force()
        assert f.shape == (3,)

    def test_force_increases_with_permittivity(self) -> None:
        d_vacuum = DielectricField()
        eps_loaded = np.diag([2.0, 2.0, 2.0])
        d_loaded = DielectricField(permittivity_tensor=eps_loaded)
        f_vacuum = np.linalg.norm(d_vacuum.biefield_brown_force())
        f_loaded = np.linalg.norm(d_loaded.biefield_brown_force())
        assert f_loaded > f_vacuum

    def test_gauge_connection_type(self) -> None:
        from cohezion.physics.gauge_theory import GaugeConnection

        d = DielectricField()
        gc = d.to_gauge_connection()
        assert isinstance(gc, GaugeConnection)

    def test_vacuum_gauge_connection_is_flat(self) -> None:
        d = DielectricField()
        gc = d.to_gauge_connection()
        assert gc.is_flat()

    def test_invalid_tensor_shape_rejected(self) -> None:
        with pytest.raises(ValueError):
            DielectricField(permittivity_tensor=np.eye(2))


class TestIonicClusterStep:
    def test_step_passes_through_hiho_boundary(self) -> None:
        """Step sequence through 0.55 must report hiho=True (float precision regression)."""
        ic = IonicClusterState(plasma_density=0.45)
        ic.step(0.05)  # 0.50 — at HIHO
        assert ic.hiho_equilibrium() is True
        ic.step(0.05)  # 0.55 — at exact tolerance boundary
        assert ic.plasma_density == pytest.approx(0.55, abs=1e-9)
        assert ic.hiho_equilibrium() is True  # Would fail before +1e-9 fix

    def test_step_exits_hiho_beyond_tolerance(self) -> None:
        ic = IonicClusterState(plasma_density=0.55)
        ic.step(0.01)  # 0.56 — outside tolerance
        assert ic.hiho_equilibrium() is False

    def test_ionisation_rate_matches_lenr_formula(self) -> None:
        """Universal 4x(1-x) kernel: IonicCluster and LENR must agree at same coherence."""
        import pytest

        c = 0.3
        ic = IonicClusterState(plasma_density=c)
        h = LENRHamiltonian()
        expected = 4.0 * c * (1.0 - c)
        assert ic.ionisation_rate() == pytest.approx(expected, rel=1e-6)
        assert h.reaction_rate(c) == pytest.approx(expected, rel=1e-6)
