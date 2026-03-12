"""Unit tests for ViscoelasticController."""

import time

import pytest

from cohezion.reliability.viscoelastic import ViscoelasticController


def test_viscoelastic_init():
    """Verify initial state."""
    vc = ViscoelasticController(relaxation_tau=30.0)
    assert vc.viscosity == 0.0
    assert vc.last_pressure is None


def test_viscoelastic_rising_pressure():
    """Verify viscosity increase on rising pressure."""
    vc = ViscoelasticController(relaxation_tau=30.0)

    # First call sets baseline
    vc.calculate_dilation_adjustment(10, 10, 10, dt_override=2.0)

    # Second call with spike (from 10% to 50%)
    # rate = (0.5 - 0.1) / 2.0 = 0.2
    # increase = 0.2 * 30.0 = 6.0
    # capped at 1.0
    adjustment = vc.calculate_dilation_adjustment(50, 50, 50, dt_override=2.0)

    assert vc.viscosity == 1.0
    assert adjustment == 1.0


def test_viscoelastic_decay():
    """Verify viscosity decay on stable/falling pressure."""
    vc = ViscoelasticController(relaxation_tau=10.0)

    # Set initial high viscosity manually for test
    vc.viscosity = 1.0
    vc.last_pressure = 0.5
    vc.last_time = time.time() - 2.0

    # Stable pressure (no change)
    # decay = 1.0 - 2.0 / 10.0 = 0.8
    # new viscosity = 1.0 * 0.8 = 0.8
    adjustment = vc.calculate_dilation_adjustment(50, 50, 50, dt_override=2.0)

    assert vc.viscosity == pytest.approx(0.8)
    assert adjustment == pytest.approx(0.8)


def test_viscoelastic_reset():
    """Verify reset logic."""
    vc = ViscoelasticController()
    vc.viscosity = 0.5
    vc.last_pressure = 0.5
    vc.reset()
    assert vc.viscosity == 0.0
    assert vc.last_pressure is None
