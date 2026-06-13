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
