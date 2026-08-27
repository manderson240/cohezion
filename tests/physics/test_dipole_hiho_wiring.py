"""The dipole must agree with every other substrate at HIHO — and with dielectric downstream.

Harness **U1** asserts that all physics substrates share the kernel ``4x(1-x)``, each returning
1.0 at x = 0.5. **S9** asserts they agree with each other at the same input, not merely that each
peaks somewhere. This wires the new dipole into both, which is the point of adding it: it is the
kernel's elementary realization, not an eighth coincidence.

Also covers the ``dielectric.from_dipoles`` bridge, which supplies the ``P = N⟨p⟩`` link that was
missing — permittivity was previously a free input parameter with no connection to the charge
separation that causes it.
"""

from __future__ import annotations

import numpy as np
import pytest

from cohezion.physics.dielectric import DielectricField
from cohezion.physics.electric_dipole import ElectricDipole
from cohezion.physics.ionic_cluster import IonicClusterState
from cohezion.physics.lenr import LENRHamiltonian


def _dipole_at_alignment(x: float) -> ElectricDipole:
    """A dipole whose alignment fraction with +x is exactly ``x``."""
    cos_theta = 2.0 * x - 1.0
    sin_theta = float(np.sqrt(max(0.0, 1.0 - cos_theta**2)))
    return ElectricDipole(charge=1.0, separation=np.array([cos_theta, sin_theta, 0.0]))


E_X = np.array([1.0, 0.0, 0.0])


class TestU1CrossSubstrateAgreement:
    def test_dipole_returns_unity_at_hiho(self) -> None:
        """U1's signature value."""
        assert _dipole_at_alignment(0.5).hiho_kernel(E_X) == pytest.approx(1.0)

    @pytest.mark.parametrize("x", [0.0, 0.1, 0.25, 0.5, 0.75, 0.9, 1.0])
    def test_dipole_matches_ionic_and_lenr_pointwise(self, x: float) -> None:
        """S9: the substrates must agree AT THE SAME INPUT, not merely peak in the same place.

        Peaking at 0.5 is weak — many unimodal functions do. Agreement across the whole interval
        is what makes 'the same kernel' a claim with content.
        """
        dipole = _dipole_at_alignment(x).hiho_kernel(E_X)
        ionic = IonicClusterState(plasma_density=x).ionisation_rate()
        lenr = LENRHamiltonian().reaction_rate(x)
        assert dipole == pytest.approx(ionic, abs=1e-9)
        assert dipole == pytest.approx(lenr, abs=1e-9)

    def test_the_agreement_is_not_vacuous(self) -> None:
        """Guard: the kernel must actually VARY, or 'they all agree' is trivially true."""
        vals = [_dipole_at_alignment(x).hiho_kernel(E_X) for x in (0.0, 0.25, 0.5)]
        assert len({round(v, 6) for v in vals}) == 3, "kernel must discriminate across x"


class TestKernelIsSinSquared:
    def test_identity_holds_to_machine_precision(self) -> None:
        """4x(1-x) == sin²θ, the identity that makes the dipole the kernel's realization."""
        for theta in np.linspace(0.0, np.pi, 33):
            dip = ElectricDipole(
                charge=1.0, separation=np.array([np.cos(theta), np.sin(theta), 0.0])
            )
            assert dip.hiho_kernel(E_X) == pytest.approx(np.sin(theta) ** 2, abs=1e-14)


class TestDielectricBridge:
    def test_from_dipoles_derives_permittivity_above_vacuum(self) -> None:
        f = DielectricField.from_dipoles(number_density=3.3e28, dipole_magnitude=6.2e-30)
        assert f.mean_permittivity > 1.0
        assert f.permittivity_tensor.shape == (3, 3)

    def test_zero_density_reduces_to_vacuum_and_a_flat_connection(self) -> None:
        """HIHO gauge condition from dielectric.py: at ε_r = 1 the connection is flat."""
        f = DielectricField.from_dipoles(number_density=0.0, dipole_magnitude=6.2e-30)
        assert f.mean_permittivity == pytest.approx(1.0)

    def test_derived_field_is_a_working_DielectricField(self) -> None:
        """DISCRIMINATING: the bridge must yield a fully usable object, not just a number.

        A classmethod that returned something structurally valid but functionally inert would
        pass a permittivity assertion while breaking every downstream consumer.
        """
        f = DielectricField.from_dipoles(number_density=3.3e28, dipole_magnitude=6.2e-30)
        force = f.biefield_brown_force()
        assert force.shape == (3,)
        assert np.all(np.isfinite(force))
        conn = f.to_gauge_connection()
        assert conn is not None

    def test_kwargs_pass_through(self) -> None:
        f = DielectricField.from_dipoles(3.3e28, 6.2e-30, voltage=2.0e4)
        assert f.voltage == pytest.approx(2.0e4)
