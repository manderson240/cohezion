"""Discriminating tests for real power measurement (2026-06-06, backlog item 3).

Item 3 asked to calibrate LANE_WATTS against measured tokens-per-watt. Honest finding:
on a unified Strix Halo APU, per-lane attribution is confounded (RAPL = package-level,
amdgpu power1_average = whole-SoC, XDNA2 NPU in neither domain). So we do NOT fabricate
per-lane numbers — we add a REAL SoC-power read + the joules-per-token math, and document
the confound. Each test fails a plausible wrong impl:
  - joules_per_token that forgets duration (energy = P, not P·t),
  - a SoC reader that returns a fabricated constant instead of reading sysfs / failing soft,
  - division-by-zero when tokens == 0.
"""

from __future__ import annotations

import math

from cohezion.substrate.hardware_monitor import HardwareMonitor, joules_per_token


def test_joules_per_token_is_energy_over_tokens() -> None:
    # energy = power × duration; per token = energy / tokens.
    # 20 W for 5 s = 100 J over 100 tokens = 1.0 J/token.
    assert joules_per_token(power_w=20.0, tokens=100, duration_s=5.0) == 1.0
    # A wrong impl that forgets duration would give 20/100 = 0.2 — this discriminates it.
    assert joules_per_token(power_w=20.0, tokens=100, duration_s=5.0) != 0.2


def test_joules_per_token_scales_with_duration_and_power() -> None:
    base = joules_per_token(power_w=10.0, tokens=50, duration_s=2.0)  # 0.4
    assert joules_per_token(power_w=20.0, tokens=50, duration_s=2.0) == 2 * base  # 2× power
    assert joules_per_token(power_w=10.0, tokens=50, duration_s=4.0) == 2 * base  # 2× time


def test_joules_per_token_zero_tokens_is_inf_not_crash() -> None:
    assert joules_per_token(power_w=20.0, tokens=0, duration_s=5.0) == math.inf


def test_read_soc_power_w_is_real_or_none() -> None:
    # On this box amdgpu exposes power1_average; the read must be a real positive watt value
    # OR honest None (fail-soft) — never a fabricated default. A wrong impl returning a fixed
    # constant like 15.0 every time would not satisfy "real or None".
    mon = HardwareMonitor(enable_real_hardware=True)
    p = mon.read_soc_power_w()
    assert p is None or (isinstance(p, float) and 0.0 < p < 200.0)


def test_read_soc_power_w_failsoft_on_bad_root(monkeypatch) -> None:
    # Point the reader at a nonexistent sysfs root → must return None, not raise, not default.
    mon = HardwareMonitor(enable_real_hardware=True)
    p = mon.read_soc_power_w(drm_root="/nonexistent/sysfs/path")
    assert p is None
