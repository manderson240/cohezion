"""Tests for ResourceGuard.can_load_model_kv_aware — the KV-aware OOM gate.

The plain can_load_model trusts a weights-only estimate and ignores the KV cache — the exact
hidden cost that caused the 2026-06-09 OOM crash (harness note N3). can_load_model_kv_aware adds
the KV footprint (via cohezion.inference.kv_budget) so a load whose *KV cache* would OOM is
refused even when the weights alone fit.
"""

from __future__ import annotations

from unittest.mock import patch

from cohezion.reliability.resource_guard import ResourceGuard, SystemVitals


# 40 GB free sits between weights-only (20 GB + margin) and weights + full-ctx KV (20 + 64 GB),
# so the KV cache is exactly what flips the decision.
_VITALS_40GB = SystemVitals(
    cpu_load_1m=5.0, ram_available_mb=40 * 1024, ram_percent=55.0, swap_used_mb=0
)


def _guard() -> ResourceGuard:
    return ResourceGuard(min_ram_available_mb=16384, model_load_margin_mb=2048)


def test_kv_aware_refuses_when_weights_fit_but_kv_would_oom():
    """The N3 point: a heavy model's WEIGHTS fit in 40 GB, but at full 256k context the KV cache
    alone is ~64 GB — weights+KV overflow. Weight-only can_load_model would ALLOW it; the
    KV-aware gate REFUSES it."""
    guard = _guard()
    with patch.object(guard, "get_vitals", return_value=_VITALS_40GB):
        # weights alone (20 GB) fit comfortably -> plain gate allows
        weights_only_ok, _ = guard.can_load_model(estimated_mb=20 * 1024)
        # weights + full-context KV -> KV-aware gate refuses
        kv_ok, reason = guard.can_load_model_kv_aware(
            weight_mb=20 * 1024,
            num_layers=64,
            num_kv_heads=8,
            head_dim=128,
            seq_len=262144,
            cache_dtype="fp16",
        )
    assert weights_only_ok is True  # the blind spot the crash exploited
    assert kv_ok is False  # the deterministic guard closes it
    assert "OOM" in reason or "available" in reason.lower()


def test_kv_aware_allows_when_bounded_context_fits():
    """Same heavy model, ctx bounded to 16384 (the N3 fix): weights + KV fit -> allowed."""
    guard = _guard()
    with patch.object(guard, "get_vitals", return_value=_VITALS_40GB):
        ok, _ = guard.can_load_model_kv_aware(
            weight_mb=20 * 1024,
            num_layers=64,
            num_kv_heads=8,
            head_dim=128,
            seq_len=16384,
            cache_dtype="fp16",
        )
    assert ok is True


def test_kv_aware_q8_cache_flips_a_refuse_to_allow():
    """The A3 lever: halving the KV dtype can turn an OOM refuse into an allow (same model/ctx)."""
    guard = ResourceGuard(min_ram_available_mb=16384, model_load_margin_mb=2048)
    vitals = SystemVitals(
        cpu_load_1m=5.0, ram_available_mb=34 * 1024, ram_percent=60.0, swap_used_mb=0
    )
    common = {
        "weight_mb": 20 * 1024,
        "num_layers": 64,
        "num_kv_heads": 8,
        "head_dim": 128,
        "seq_len": 65536,
    }
    with patch.object(guard, "get_vitals", return_value=vitals):
        fp16_ok, _ = guard.can_load_model_kv_aware(**common, cache_dtype="fp16")
        q8_ok, _ = guard.can_load_model_kv_aware(**common, cache_dtype="q8_0")
    assert fp16_ok is False
    assert q8_ok is True
