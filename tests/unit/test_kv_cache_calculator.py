"""KV-budget MLA-axis tests — retargeted from the retired kv_cache_calculator.py.

kv_cache_calculator.py duplicated kv_budget's GQA formula and added one axis:
DeepSeek-style multi-head latent attention (MLA), which caches a single
latent vector per layer per token. That axis now lives in kv_budget (the
harness-blessed N3 pre-flight gate); these tests pin it.
"""

from __future__ import annotations

from cohezion.inference.kv_budget import kv_cache_bytes, preflight


def test_gqa_formula_unchanged() -> None:
    # Llama-3.1-8B shape @ 32k, fp16 — documented anchor: ~4 GiB.
    got = kv_cache_bytes(num_layers=32, num_kv_heads=8, head_dim=128, seq_len=32768)
    assert abs(got - 4 * 1024**3) / 4 / 1024**3 < 0.01


def test_mla_latent_dim_reduces_footprint() -> None:
    """Discriminating: MLA must use latent_dim per layer, not 2·kv_heads·head_dim.

    A wrong implementation that ignores mla_latent_dim returns the (much
    larger) GQA number for the same shape.
    """
    gqa = kv_cache_bytes(num_layers=61, num_kv_heads=128, head_dim=128, seq_len=8192)
    mla = kv_cache_bytes(
        num_layers=61, num_kv_heads=128, head_dim=128, seq_len=8192, mla_latent_dim=512
    )
    # MLA formula: layers · latent · seq · 2B
    assert mla == (61 * 512 * 8192 * 2)
    assert mla < gqa / 50, "MLA compression must dominate the GQA footprint"


def test_mla_respects_cache_dtype() -> None:
    fp16 = kv_cache_bytes(
        num_layers=61, num_kv_heads=128, head_dim=128, seq_len=8192, mla_latent_dim=512
    )
    q8 = kv_cache_bytes(
        num_layers=61,
        num_kv_heads=128,
        head_dim=128,
        seq_len=8192,
        mla_latent_dim=512,
        cache_dtype="q8_0",
    )
    assert q8 * 2 == fp16


def test_preflight_threads_mla_axis() -> None:
    ok_gqa, info_gqa = preflight(
        free_bytes=8 * 1024**3,
        weight_bytes=2 * 1024**3,
        num_layers=61,
        num_kv_heads=128,
        head_dim=128,
        seq_len=8192,
        buffer_bytes=1 * 1024**3,
    )
    ok_mla, info_mla = preflight(
        free_bytes=8 * 1024**3,
        weight_bytes=2 * 1024**3,
        num_layers=61,
        num_kv_heads=128,
        head_dim=128,
        seq_len=8192,
        buffer_bytes=1 * 1024**3,
        mla_latent_dim=512,
    )
    # The GQA shape overflows 8 GiB; the MLA-compressed cache fits.
    assert not ok_gqa
    assert ok_mla
    assert info_mla["kv_bytes"] < info_gqa["kv_bytes"]
