"""Tests for CosmicScaleHierarchy scale calibration (#96)."""

from cohezion.physics.cosmogony import CosmicScaleHierarchy


def test_hierarchy_monotonic_and_span():
    bench = CosmicScaleHierarchy().calibration_benchmark()
    assert bench["monotonic"] is True
    assert bench["log10_span"] > 55
    assert bench["valid"] is True


def test_scale_for_step_planck():
    name, scale = CosmicScaleHierarchy().scale_for_step(1)
    assert name == "Planck"
    assert scale == 1.616e-35


def test_log_ratio_directional():
    h = CosmicScaleHierarchy()
    assert h.log_ratio(1, 12) > 55
    assert h.log_ratio(12, 1) < 0
