"""Discriminating tests for pipeline.hyperparameter_debate bounds (V-model audit, 2026-06-05).

`pipeline` was a no-test module. _apply_bounds is the pure clamp/canonicalize core, and it
is where harness invariant **A3** (FlumeVAE kl_weight <= 0.015, posterior-collapse guard) is
enforced at the source. Each test fails a plausible wrong impl:
  - a kl_weight bound that lets 0.02 through (collapse) or clamps to the wrong value,
  - dropping alias canonicalization (lr -> learning_rate),
  - hidden_dim that isn't snapped to a power of 2 / isn't int,
  - keeping unknown params, or not filling defaults.
"""
from __future__ import annotations

from cohezion.pipeline.hyperparameter_debate import (
    _apply_bounds,
    _clamp,
    _nearest_power_of_2,
)


def test_A3_kl_weight_clamped_to_collapse_guard_max() -> None:
    # Harness A3: kl_weight must never exceed 0.015 (collapse at ~0.02). Source enforcement.
    assert _apply_bounds({"kl_weight": 0.02})["kl_weight"] == 0.015
    assert _apply_bounds({"kl_weight": 0.05})["kl_weight"] == 0.015
    assert _apply_bounds({"kl_weight": 0.01})["kl_weight"] == 0.01   # within bounds: unchanged
    assert _apply_bounds({"kl_weight": 1e-9})["kl_weight"] == 1e-4   # floor


def test_alias_canonicalization() -> None:
    # lr -> learning_rate; an impl that doesn't canonicalize would emit key "lr".
    out = _apply_bounds({"lr": 0.001})
    assert out["learning_rate"] == 0.001 and "lr" not in out


def test_hidden_dim_snapped_to_power_of_2_int() -> None:
    out = _apply_bounds({"hidden": 100})           # alias hidden -> hidden_dim
    assert out["hidden_dim"] == 128                # nearest power of 2
    assert isinstance(out["hidden_dim"], int)


def test_unknown_params_dropped() -> None:
    out = _apply_bounds({"bogus_param": 5.0})
    assert "bogus_param" not in out


def test_defaults_filled_when_absent() -> None:
    out = _apply_bounds({})
    assert out["learning_rate"] == 3e-4
    assert out["hidden_dim"] == 128
    assert out["gamma"] == 0.99
    assert out["action_scale"] == 0.01


def test_clamp_and_power_of_2_units() -> None:
    assert _clamp(5, 0, 10) == 5
    assert _clamp(-1, 0, 10) == 0
    assert _clamp(20, 0, 10) == 10
    assert _nearest_power_of_2(100) == 128
    assert _nearest_power_of_2(0) == 64            # x<=0 guard
    assert _nearest_power_of_2(63) == 64
