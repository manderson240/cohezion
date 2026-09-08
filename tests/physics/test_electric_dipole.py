"""Electric dipole — and the exact identity linking it to the Universal HIHO kernel.

The central claim under test: with ``x = (1 + cos θ)/2``,

    4x(1-x) = (1 + cos θ)(1 - cos θ) = 1 - cos²θ = sin²θ      [exact]

so dipole torque ``τ = pE·sin θ = pE·√(HIHO kernel)``. If that holds, the kernel harness
invariant U1 asserts across seven substrates is the dipole alignment law in disguise, and the
dipole is its textbook realization rather than an eighth example.
"""

from __future__ import annotations

import numpy as np
import pytest

from cohezion.physics.electric_dipole import (
    ElectricDipole,
    permittivity_from_dipoles,
)


def _dipole_at(theta: float, q: float = 2.0, d: float = 3.0) -> ElectricDipole:
    """A dipole making angle ``theta`` with the +x axis, in the xy-plane."""
    return ElectricDipole(
        charge=q, separation=np.array([d * np.cos(theta), d * np.sin(theta), 0.0])
    )


E_X = np.array([5.0, 0.0, 0.0])


class TestConstruction:
    def test_moment_is_q_times_d(self) -> None:
        dip = ElectricDipole(charge=2.0, separation=np.array([3.0, 0.0, 0.0]))
        assert np.allclose(dip.moment, [6.0, 0.0, 0.0])
        assert dip.magnitude == pytest.approx(6.0)

    def test_negative_charge_reverses_the_moment(self) -> None:
        """p points from negative to positive; a sign flip must reverse it, not just rescale."""
        pos = ElectricDipole(charge=2.0, separation=np.array([3.0, 0.0, 0.0]))
        neg = ElectricDipole(charge=-2.0, separation=np.array([3.0, 0.0, 0.0]))
        assert np.allclose(neg.moment, -pos.moment)

    def test_non_3vector_rejected(self) -> None:
        with pytest.raises(ValueError, match="3-vector"):
            ElectricDipole(charge=1.0, separation=np.array([1.0, 0.0]))


class TestTorqueAndEnergy:
    def test_aligned_has_zero_torque_and_minimum_energy(self) -> None:
        dip = _dipole_at(0.0)
        assert np.allclose(dip.torque(E_X), np.zeros(3))
        assert dip.energy(E_X) == pytest.approx(-dip.magnitude * 5.0)

    def test_perpendicular_has_maximum_torque_and_zero_energy(self) -> None:
        dip = _dipole_at(np.pi / 2)
        assert np.linalg.norm(dip.torque(E_X)) == pytest.approx(dip.magnitude * 5.0)
        assert dip.energy(E_X) == pytest.approx(0.0)

    def test_antialigned_is_distinguished_from_aligned_by_energy_alone(self) -> None:
        """DISCRIMINATING. θ=0 and θ=180° BOTH have zero torque.

        Torque cannot tell "aligned" from "exactly backwards" — yet one is a stable equilibrium
        and the other unstable. Only the signed energy separates them. An implementation using
        ``abs(p·E)``, or normalising the moment, collapses these two states and passes every
        torque-based test while being physically wrong about which way a molecule settles.
        """
        aligned, anti = _dipole_at(0.0), _dipole_at(np.pi)
        assert np.linalg.norm(aligned.torque(E_X)) == pytest.approx(0.0, abs=1e-12)
        assert np.linalg.norm(anti.torque(E_X)) == pytest.approx(0.0, abs=1e-12)
        assert aligned.energy(E_X) == pytest.approx(-anti.energy(E_X))
        assert aligned.energy(E_X) < 0.0 < anti.energy(E_X)

    def test_torque_is_a_vector_carrying_rotation_sense(self) -> None:
        """Two dipoles equally off-axis in OPPOSITE directions rotate opposite ways.

        Returning a magnitude would report them identical.
        """
        up, down = _dipole_at(np.pi / 4), _dipole_at(-np.pi / 4)
        assert np.allclose(up.torque(E_X), -down.torque(E_X))
        assert up.torque(E_X)[2] * down.torque(E_X)[2] < 0.0


class TestHihoKernelIdentity:
    @pytest.mark.parametrize("theta_deg", [0, 22.5, 45, 67.5, 90, 112.5, 135, 157.5, 180])
    def test_kernel_equals_sin_squared(self, theta_deg: float) -> None:
        """The identity, at nine angles: 4x(1-x) == sin²θ."""
        th = np.radians(theta_deg)
        assert _dipole_at(th).hiho_kernel(E_X) == pytest.approx(np.sin(th) ** 2, abs=1e-12)

    def test_kernel_equals_squared_normalised_torque(self) -> None:
        """DISCRIMINATING: ties the kernel to the TORQUE, not merely to a trig identity.

        A kernel computed from the angle alone satisfies sin²θ trivially. This asserts it also
        equals (|τ|/(|p||E|))², i.e. that the quantity the substrates share really is the
        physical torque response and not a coincidentally-shaped function.
        """
        for th in np.linspace(0.0, np.pi, 17):
            dip = _dipole_at(th)
            normalised = np.linalg.norm(dip.torque(E_X)) / (dip.magnitude * 5.0)
            assert dip.hiho_kernel(E_X) == pytest.approx(normalised**2, abs=1e-12)

    def test_kernel_peaks_at_perpendicular(self) -> None:
        """U1's signature: the kernel returns 1.0 at the HIHO midpoint."""
        assert _dipole_at(np.pi / 2).hiho_kernel(E_X) == pytest.approx(1.0)
        assert _dipole_at(np.pi / 2).alignment_fraction(E_X) == pytest.approx(0.5)

    def test_zero_commitment_maximum_responsiveness_at_hiho(self) -> None:
        """The physical reading of x=0.5: energy zero, torque maximal — simultaneously."""
        dip = _dipole_at(np.pi / 2)
        assert dip.energy(E_X) == pytest.approx(0.0, abs=1e-12)
        assert np.linalg.norm(dip.torque(E_X)) == pytest.approx(dip.magnitude * 5.0)

    def test_alignment_fraction_spans_the_unit_interval(self) -> None:
        assert _dipole_at(0.0).alignment_fraction(E_X) == pytest.approx(1.0)
        assert _dipole_at(np.pi).alignment_fraction(E_X) == pytest.approx(0.0, abs=1e-12)


class TestHihoEquilibrium:
    def test_symmetric_at_the_exact_tolerance_boundary(self) -> None:
        """Harness S7: the float64 guard. Without +1e-9 one side of the band fails.

        Constructed directly rather than via an angle, so the boundary value is exact.
        """
        for cos_theta in (2 * 0.45 - 1, 2 * 0.55 - 1):
            sin_theta = np.sqrt(1 - cos_theta**2)
            dip = ElectricDipole(charge=1.0, separation=np.array([cos_theta, sin_theta, 0.0]))
            assert dip.hiho_equilibrium(E_X), f"boundary x for cosθ={cos_theta} must pass"

    def test_aligned_is_not_at_equilibrium(self) -> None:
        assert not _dipole_at(0.0).hiho_equilibrium(E_X)
        assert not _dipole_at(np.pi).hiho_equilibrium(E_X)


class TestDegenerateInputs:
    def test_null_field_gives_the_no_preference_midpoint(self) -> None:
        dip = _dipole_at(0.0)
        assert dip.alignment_fraction(np.zeros(3)) == pytest.approx(0.5)
        assert np.allclose(dip.torque(np.zeros(3)), np.zeros(3))

    def test_null_dipole_gives_the_no_preference_midpoint(self) -> None:
        dip = ElectricDipole(charge=0.0, separation=np.array([1.0, 0.0, 0.0]))
        assert dip.alignment_fraction(E_X) == pytest.approx(0.5)


class TestPermittivityBridge:
    def test_vacuum_when_no_dipoles(self) -> None:
        assert permittivity_from_dipoles(0.0, 6.2e-30) == pytest.approx(1.0)
        assert permittivity_from_dipoles(-1.0, 6.2e-30) == pytest.approx(1.0)

    def test_non_positive_temperature_returns_vacuum_not_a_crash(self) -> None:
        assert permittivity_from_dipoles(3.3e28, 6.2e-30, temperature_k=0.0) == pytest.approx(1.0)

    def test_permittivity_exceeds_vacuum_and_falls_with_temperature(self) -> None:
        """Orientational polarization is a 1/T effect — thermal motion randomises alignment."""
        cold = permittivity_from_dipoles(3.3e28, 6.2e-30, temperature_k=273.15)
        hot = permittivity_from_dipoles(3.3e28, 6.2e-30, temperature_k=373.15)
        assert cold > hot > 1.0

    def test_scales_with_the_square_of_the_moment(self) -> None:
        """DISCRIMINATING: p², not p. A linear implementation passes 'bigger p, bigger ε'."""
        base = permittivity_from_dipoles(1e28, 1e-30) - 1.0
        doubled = permittivity_from_dipoles(1e28, 2e-30) - 1.0
        assert doubled / base == pytest.approx(4.0, rel=1e-9)
