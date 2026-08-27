"""Unit tests for Architecture-Aware KV-Cache Calculator."""

from __future__ import annotations

from cohezion.inference.kv_cache_calculator import (
    AttentionType,
    calculate_architecture_kv_cache_gb,
)


def test_gqa_kv_cache_calculation():
    # 80 layers, 8 kv heads, 128 head dim, 8192 total tokens in FP16
    gb_fp16 = calculate_architecture_kv_cache_gb(
        model_key="qwen3-coder-80b",
        prompt_tokens=4096,
        max_gen_tokens=4096,
        kv_bits=16,
    )
    assert 2.0 <= gb_fp16 <= 3.0  # ~2.5 GB for 8k tokens in GQA

    # Q4_0 KV-cache quantization reduces it by 4x
    gb_q4 = calculate_architecture_kv_cache_gb(
        model_key="qwen3-coder-80b",
        prompt_tokens=4096,
        max_gen_tokens=4096,
        kv_bits=4,
    )
    assert 0.5 <= gb_q4 <= 0.8  # ~0.625 GB for 8k tokens in Q4_0


def test_mla_deepseek_kv_cache_calculation():
    # DeepSeek MLA compressed latent KV cache
    gb_mla = calculate_architecture_kv_cache_gb(
        model_key="deepseek-r1-671b-mla",
        prompt_tokens=4096,
        max_gen_tokens=4096,
        kv_bits=16,
    )
    # MLA uses ~0.25 GB for 8k tokens
    assert gb_mla < 0.5
