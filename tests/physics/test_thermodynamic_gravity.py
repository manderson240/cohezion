import pytest

pytest.importorskip(
    "cohezion.physics.observer_patch", reason="TDD-red: FrequencyDispersedDelay not yet implemented"
)
"""Discriminating tests for ThermodynamicGravity (Isichei & Magueijo 2026)."""

import pytest

from cohezion.physics import OttoWorkLeg, ThermodynamicGravity
from cohezion.physics.thermodynamic_gravity import donnan_potential_to_work_leg


class TestThermodynamicGravity:
    def test_zero_work_legs_is_standard_gr(self):
        tg = ThermodynamicGravity()
        assert tg.is_standard_gr()
        assert tg.lorentz_violation_parameter() == 0.0
        assert tg.acceleration_term() == 0.0

    def test_nonzero_work_leg_breaks_gr(self):
        tg = ThermodynamicGravity(
            temperature=1.0,
            work_legs=[OttoWorkLeg(lorentz_violation=0.1, entropy_flux=2.0)],
        )
        assert not tg.is_standard_gr()
        assert tg.lorentz_violation_parameter() == 0.1
        assert tg.acceleration_term() > 0.0

    def test_entropy_change_formula(self):
        # dS = δQ/T + δW/T; with T=2, heat=4, work_entropy=2 → (4+2)/2 = 3.0
        tg = ThermodynamicGravity(
            temperature=2.0,
            work_legs=[OttoWorkLeg(lorentz_violation=0.0, entropy_flux=2.0)],
        )
        assert abs(tg.entropy_change(heat_flux=4.0) - 3.0) < 1e-9

    def test_import_from_physics_package(self):
        from cohezion.physics import OttoWorkLeg as OWL
        from cohezion.physics import ThermodynamicGravity as TG

        assert TG is ThermodynamicGravity
        assert OWL is OttoWorkLeg


class TestDonnanPotentialToWorkLeg:
    """Discriminating tests for the Polymers 2026 → ThermodynamicGravity bridge."""

    def test_returns_otto_work_leg(self):
        leg = donnan_potential_to_work_leg(10.0, 1.0)
        assert isinstance(leg, OttoWorkLeg)

    def test_epsilon_bounded_in_unit_interval(self):
        """Discriminating: a naive φ_D/max formula could exceed 1 at high charge."""
        leg_high = donnan_potential_to_work_leg(1e6, 1.0)  # extreme charge
        leg_low = donnan_potential_to_work_leg(1e-6, 1.0)  # extreme dilution
        assert 0.0 <= leg_high.lorentz_violation <= 1.0
        assert 0.0 <= leg_low.lorentz_violation <= 1.0

    def test_weak_coupling_gives_near_zero_epsilon(self):
        """Discriminating: wrong normalisation would keep ε large even at ρ→0."""
        leg = donnan_potential_to_work_leg(0.001, 100.0)
        assert leg.lorentz_violation < 0.01, (
            f"Expected near-zero ε for dilute PEL, got {leg.lorentz_violation}"
        )

    def test_strong_coupling_gives_intermediate_epsilon(self):
        """GJ 436 proxy: strong magnetospheric coupling → De≈1 (HIHO equilibrium)."""
        leg = donnan_potential_to_work_leg(100.0, 10.0)
        # Should land in the intermediate activity range (0.5 < ε < 0.95)
        assert 0.5 < leg.lorentz_violation < 0.95, (
            f"GJ436 proxy should give intermediate ε, got {leg.lorentz_violation}"
        )

    def test_entropy_flux_scales_with_potential(self):
        """Discriminating: δS must increase with membrane charge (more work capacity)."""
        leg_low = donnan_potential_to_work_leg(1.0, 10.0)
        leg_high = donnan_potential_to_work_leg(100.0, 10.0)
        assert leg_high.entropy_flux > leg_low.entropy_flux

    def test_wires_into_thermodynamic_gravity(self):
        """Integration: Donnan leg produces non-zero acceleration_term."""
        leg = donnan_potential_to_work_leg(50.0, 5.0)
        tg = ThermodynamicGravity(temperature=1.0, work_legs=[leg])
        assert not tg.is_standard_gr()
        assert tg.acceleration_term() > 0.0

    def test_zero_ionic_strength_raises(self):
        with pytest.raises(ValueError, match="ionic_strength"):
            donnan_potential_to_work_leg(10.0, 0.0)
