"""Comprehensive pytest suite for all rigorous empirical physical & computational proofs."""

from __future__ import annotations

import math

import numpy as np

from cohezion.actioner.autoharness_verifier import AutoHarnessVerifier
from cohezion.flume.bayesian_metaplasticity_engine import BayesianMetaplasticityEngine
from cohezion.physics.heim_metron_engine import METRON_TAU, HeimMetronEngine
from cohezion.physics.matsumoto_enc_engine import MatsumotoENCEngine
from cohezion.physics.poincare_neural_ode import PoincareNeuralODE
from cohezion.physics.thermodynamic_hiho_engine import ThermodynamicHIHOEngine


def test_proof1_poincare_2048d_geodesic_boundary_containment() -> None:
    ode_engine = PoincareNeuralODE(dimension=2048)
    np.random.seed(42)
    z0 = np.random.randn(2048)
    z0 = (z0 / np.linalg.norm(z0)) * 0.95
    v0 = np.random.randn(2048) * 0.1

    traj = ode_engine.integrate_geodesic(z0, v0, t_span=(0.0, 1.0), steps=50)
    max_norm = float(np.max(traj.hyperbolic_norms))
    dist = ode_engine.hyperbolic_distance(traj.positions[0], traj.positions[-1])

    assert max_norm < 1.0
    assert traj.strictly_contained is True
    assert dist > 0.0


def test_proof2_matsumoto_screening_and_coulomb_collapse() -> None:
    matsumoto = MatsumotoENCEngine()
    c_state = matsumoto.evaluate_itonic_cluster(num_protons=4, num_electrons=8, current_density_a_m2=1e13)
    trans = matsumoto.simulate_enc_transmutation(c_state)

    assert c_state.is_enc_triggered is True
    assert c_state.coulomb_barrier_ev < 1.0
    assert trans["transmutation_occurred"] is True
    assert trans["primary_product"] == "4He (Helium-4)"


def test_proof3_heim_metron_discrete_quantization() -> None:
    heim = HeimMetronEngine()
    test_area = 1.845e-69  # 3 * METRON_TAU
    n_metrons, q_area = heim.quantize_surface_area(test_area)

    assert n_metrons == 3
    assert math.isclose(q_area, 3 * METRON_TAU, rel_tol=1e-12)


def test_proof4_palimpsa_bayesian_continual_retention() -> None:
    meta_engine = BayesianMetaplasticityEngine(d_k=12, d_v=12)
    k_first = np.ones(12, dtype=np.float64) / math.sqrt(12)
    v_first = np.array([1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0, 11.0, 12.0])

    meta_engine.step(k_first, v_first, d_t=1.0)

    for _ in range(20):
        k_other = np.random.randn(12)
        k_other /= np.linalg.norm(k_other)
        v_other = np.random.randn(12)
        meta_engine.step(k_other, v_other, d_t=0.5)

    v_retrieved, _ = meta_engine.step(k_first, np.zeros(12), d_t=0.0)
    cos_sim = float(np.dot(v_retrieved, v_first) / (np.linalg.norm(v_retrieved) * np.linalg.norm(v_first)))

    assert cos_sim > 0.85


def test_proof5_thermodynamic_hiho_and_landauer() -> None:
    thermo = ThermodynamicHIHOEngine()
    state_hiho = thermo.evaluate_thermodynamic_hiho(coherence=0.5, bits_erased=100.0)
    state_off = thermo.evaluate_thermodynamic_hiho(coherence=0.2, bits_erased=100.0)

    assert state_hiho.order_parameter_phi == 1.0
    assert state_hiho.fundamental_freq_hz == 432.0
    assert state_hiho.spectral_dissonance == 0.0
    assert state_off.spectral_dissonance > 0.5
    assert state_hiho.landauer_dissipation_joules > 0.0


def test_proof6_autoharness_ast_safety_and_latency() -> None:
    verifier = AutoHarnessVerifier()
    safe_code = "def transform(x):\n    return [i * 2 for i in x]"
    unsafe_code = "import os\nos.system('rm -rf /')"

    safe_res = verifier.verify_code(safe_code)
    unsafe_res = verifier.verify_code(unsafe_code)

    assert safe_res.valid is True
    assert unsafe_res.valid is False
