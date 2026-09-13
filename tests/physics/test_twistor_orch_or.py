import pytest
from cohezion.physics.twistor_orch_or import (
    PenroseTwistorEngine,
    OrchOREngine,
    TwistorState,
    OrchORReductionEvent,
)


def test_penrose_twistor_origin():
    engine = PenroseTwistorEngine()
    twistor = engine.spacetime_to_twistor((0.0, 0.0, 0.0, 0.0))
    assert isinstance(twistor, TwistorState)
    assert twistor.omega_spinor == (0j, 0j)
    assert twistor.helicity == pytest.approx(0.0)
    assert twistor.is_null_ray is True


def test_penrose_twistor_lightcone():
    engine = PenroseTwistorEngine()
    # Event on lightcone: t=1, x=1, y=0, z=0
    twistor = engine.spacetime_to_twistor((1.0, 1.0, 0.0, 0.0))
    assert isinstance(twistor, TwistorState)
    assert abs(twistor.omega_spinor[0]) > 0.0


def test_orch_or_gravitational_scaling():
    orch = OrchOREngine()
    event_1k = orch.compute_reduction_time(1000)
    event_10k = orch.compute_reduction_time(10000)

    # Eg scales quadratically with dimer count (10x dimers -> ~100x Eg)
    ratio_eg = event_10k.gravitational_self_energy_eg / event_1k.gravitational_self_energy_eg
    assert ratio_eg == pytest.approx(100.0, rel=1e-3)

    # Reduction timescale tau scales inversely
    ratio_tau = event_1k.reduction_time_tau_s / event_10k.reduction_time_tau_s
    assert ratio_tau == pytest.approx(100.0, rel=1e-3)

    # Objective reduction fixed point is 0.50 HIHO
    assert event_10k.collapsed_coherence == 0.50
    assert event_10k.is_hiho_equilibrium is True
