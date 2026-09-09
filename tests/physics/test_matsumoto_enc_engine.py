"""Unit tests for Dr. Takaaki Matsumoto's Electro-Nuclear Collapse (ENC) & Itonic Cluster Engine."""

from __future__ import annotations

from cohezion.physics.matsumoto_enc_engine import MatsumotoENCEngine


def test_matsumoto_screening_length_calculation() -> None:
    engine = MatsumotoENCEngine()
    # High density electron plasma (1e28 electrons/m^3)
    lambda_screen = engine.compute_screening_length(1e28)
    assert 0.0 < lambda_screen < 1e-10


def test_itonic_cluster_enc_trigger() -> None:
    engine = MatsumotoENCEngine()
    # Sub-critical cluster
    sub_crit = engine.evaluate_itonic_cluster(
        num_protons=2, num_electrons=2, current_density_a_m2=1e8
    )
    assert sub_crit.is_enc_triggered is False

    # Super-critical Itonic cluster (1e13 A/m^2 current density, 8 electrons in 1nm cluster)
    enc_crit = engine.evaluate_itonic_cluster(
        num_protons=4, num_electrons=8, current_density_a_m2=1e13
    )
    assert enc_crit.is_enc_triggered is True
    assert enc_crit.coulomb_barrier_ev < 1.0  # Barrier effectively collapsed


def test_enc_transmutation_simulation() -> None:
    engine = MatsumotoENCEngine()
    enc_crit = engine.evaluate_itonic_cluster(
        num_protons=4, num_electrons=8, current_density_a_m2=1e13
    )
    res = engine.simulate_enc_transmutation(enc_crit)

    assert res["transmutation_occurred"] is True
    assert res["primary_product"] == "4He (Helium-4)"
    assert res["energy_released_mev"] > 20.0
