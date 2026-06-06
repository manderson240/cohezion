"""Discriminating tests for the per-lane ΔP measurement harness (2026-06-06, item 17).

Item 3 found per-lane power is confounded on a unified APU; item 17 builds the controlled-load
ΔP harness that DOES isolate a lane: with other lanes idle, ΔP = mean(load) − mean(idle) is the
marginal SoC power for that lane's activity. This tests the pure ΔP math (the falsifiable core
that "separates the lanes"); the LIVE 3-lane run needs NPU+CPU up (down this session → UNPROVEN).
Each test fails a plausible wrong impl:
  - one that returns load mean instead of the DELTA,
  - one that doesn't separate a heavy lane from a light one,
  - one that crashes on None (fail-soft) readings,
  - one that reports a delta from insufficient data instead of None.
"""
from __future__ import annotations

from cohezion.substrate.hardware_monitor import marginal_power_w


def test_delta_is_load_minus_idle() -> None:
    assert marginal_power_w([20.0, 20.0], [55.0, 55.0]) == 35.0


def test_separates_a_heavy_lane_from_a_light_one() -> None:
    # The whole point: a CPU-tier load (ΔP large) must measure higher than an NPU-tier load
    # (ΔP small). A wrong impl that ignores idle baseline would not separate them.
    npu_delta = marginal_power_w([24.0], [28.0])    # ~4 W marginal
    cpu_delta = marginal_power_w([24.0], [79.0])    # ~55 W marginal
    assert npu_delta < cpu_delta
    assert npu_delta == 4.0 and cpu_delta == 55.0


def test_none_readings_are_ignored() -> None:
    assert marginal_power_w([None, 20.0], [None, 50.0]) == 30.0


def test_insufficient_data_is_none_not_a_fake_delta() -> None:
    assert marginal_power_w([], [50.0]) is None
    assert marginal_power_w([20.0], [None]) is None
    assert marginal_power_w([None], [None]) is None
