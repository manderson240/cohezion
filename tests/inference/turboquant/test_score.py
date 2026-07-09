"""Tests for ``cohezion.inference.turboquant.score.compute_hybrid_attention``.

Covers the four routing branches of the read path:

  * zeros early-return  (no history, no recent)
  * exact recent-only   (lossless — supports known-value assertions)
  * compressed-only     (lossy — structural assertions only)
  * hybrid              (lossy — structural assertions only)

All fixtures construct ``CompressedKVStore`` on CPU; no network/DB/model is
touched, so the suite is synchronous and fast.

The exact recent-only path is lossless (no quantization), so several tests
anchor it to hand-computable values derived from the ``_matmul_attend`` einsum:
a uniform softmax over the recent tokens yields the per-kv-head mean of the
values, broadcast across each GQA group.
"""

from __future__ import annotations

import math

import pytest


torch = pytest.importorskip("torch")

pytestmark = pytest.mark.fast

from cohezion.inference.turboquant.score import (
    MIN_HISTORY_FOR_TQ,
    compute_hybrid_attention,
)
from cohezion.inference.turboquant.store import CompressedKVStore


CPU = torch.device("cpu")

# head_dim used for compressed/hybrid paths must be divisible by 32, because
# score.py dequantizes values with a hardcoded group_size of 32. The store
# clamps value_group_size to min(32, head_dim), so head_dim>=32 keeps the
# quantize/dequantize group sizes aligned.
HEAD_DIM_COMPRESSED = 32
# For lossless recent-only tests any small head_dim works.
HEAD_DIM_RECENT = 4


def _make_store(head_dim: int, num_kv_heads: int) -> CompressedKVStore:
    """Construct a CPU-resident compressed KV store (no CUDA)."""
    return CompressedKVStore(
        head_dim=head_dim,
        num_kv_heads=num_kv_heads,
        device=CPU,
    )


def _expected_mean_broadcast(
    recent_v: torch.Tensor, num_query_heads: int, num_kv_heads: int
) -> torch.Tensor:
    """Per-kv-head mean of recent values, broadcast across each GQA group.

    Mirrors what _matmul_attend produces under a uniform softmax: the GQA
    expansion maps consecutive query heads to the same kv head (repeat_interleave
    of the group dimension), so query head index = kv_head * gqa_ratio + group.
    """
    gqa_ratio = num_query_heads // num_kv_heads
    mean = recent_v.mean(dim=0)  # (num_kv_heads, head_dim)
    return mean.repeat_interleave(gqa_ratio, dim=0).unsqueeze(0)  # (1, Q, D)


# ---------------------------------------------------------------------------
# Zeros early-return branch (no history, no recent)
# ---------------------------------------------------------------------------


def test_no_history_no_recent_returns_zeros():
    num_kv_heads, num_query_heads, head_dim = 2, 8, HEAD_DIM_RECENT
    store = _make_store(head_dim, num_kv_heads)  # empty: get_flat_cache() -> None
    query = torch.randn(1, num_query_heads, head_dim)

    out = compute_hybrid_attention(
        query, store, recent_k=None, recent_v=None, num_query_heads=num_query_heads
    )

    assert out.shape == (1, num_query_heads, head_dim)
    assert (out == 0).all()


def test_zeros_output_matches_query_device_and_dtype():
    num_kv_heads, num_query_heads, head_dim = 2, 8, HEAD_DIM_RECENT
    store = _make_store(head_dim, num_kv_heads)
    query = torch.zeros(1, num_query_heads, head_dim, device=CPU, dtype=torch.float16)

    out = compute_hybrid_attention(
        query, store, recent_k=None, recent_v=None, num_query_heads=num_query_heads
    )

    assert out.device == query.device
    assert out.dtype == query.dtype
    assert (out == 0).all()


def test_subthreshold_history_no_recent_returns_zeros():
    """flat is not None but num_tokens (15) < MIN_HISTORY_FOR_TQ (16) -> zeros."""
    num_kv_heads, num_query_heads, head_dim = 2, 8, HEAD_DIM_COMPRESSED
    store = _make_store(head_dim, num_kv_heads)
    store.append_chunk(
        torch.randn(15, num_kv_heads, head_dim),
        torch.randn(15, num_kv_heads, head_dim),
    )
    # flat cache exists (chunk appended) but is sub-threshold.
    assert store.get_flat_cache() is not None
    assert store.num_tokens == 15

    query = torch.randn(1, num_query_heads, head_dim)
    out = compute_hybrid_attention(
        query, store, recent_k=None, recent_v=None, num_query_heads=num_query_heads
    )

    assert out.shape == (1, num_query_heads, head_dim)
    assert (out == 0).all()


def test_history_boundary_15_vs_16_tokens():
    """Boundary on MIN_HISTORY_FOR_TQ: 15 -> zeros, 16 -> non-zero finite."""
    assert MIN_HISTORY_FOR_TQ == 16
    num_kv_heads, num_query_heads, head_dim = 2, 8, HEAD_DIM_COMPRESSED
    query = torch.randn(1, num_query_heads, head_dim)

    store_15 = _make_store(head_dim, num_kv_heads)
    store_15.append_chunk(
        torch.randn(15, num_kv_heads, head_dim),
        torch.randn(15, num_kv_heads, head_dim),
    )
    out_15 = compute_hybrid_attention(
        query, store_15, recent_k=None, recent_v=None, num_query_heads=num_query_heads
    )
    assert (out_15 == 0).all()

    store_16 = _make_store(head_dim, num_kv_heads)
    store_16.append_chunk(
        torch.randn(16, num_kv_heads, head_dim),
        torch.randn(16, num_kv_heads, head_dim),
    )
    out_16 = compute_hybrid_attention(
        query, store_16, recent_k=None, recent_v=None, num_query_heads=num_query_heads
    )
    assert out_16.shape == (1, num_query_heads, head_dim)
    assert torch.isfinite(out_16).all()
    assert (out_16 != 0).any()


# ---------------------------------------------------------------------------
# Exact recent-only path (lossless — known-value assertions allowed)
# ---------------------------------------------------------------------------


def test_recent_only_path_shape_and_finite():
    num_kv_heads, num_query_heads, head_dim = 2, 8, HEAD_DIM_RECENT
    store = _make_store(head_dim, num_kv_heads)  # empty -> no history
    recent_len, num_tokens = 5, 1
    query = torch.randn(num_tokens, num_query_heads, head_dim)
    recent_k = torch.randn(recent_len, num_kv_heads, head_dim)
    recent_v = torch.randn(recent_len, num_kv_heads, head_dim)

    out = compute_hybrid_attention(
        query, store, recent_k, recent_v, num_query_heads=num_query_heads
    )

    assert out.shape == (num_tokens, num_query_heads, head_dim)
    assert torch.isfinite(out).all()


def test_recent_only_zero_query_equals_mean_of_values():
    """All-zero query -> uniform softmax -> output is mean of recent_v."""
    num_kv_heads, num_query_heads, head_dim = 2, 8, HEAD_DIM_RECENT
    store = _make_store(head_dim, num_kv_heads)
    recent_len = 5
    query = torch.zeros(1, num_query_heads, head_dim)
    recent_k = torch.randn(recent_len, num_kv_heads, head_dim)
    recent_v = torch.randn(recent_len, num_kv_heads, head_dim)

    out = compute_hybrid_attention(
        query, store, recent_k, recent_v, num_query_heads=num_query_heads
    )

    expected = _expected_mean_broadcast(recent_v, num_query_heads, num_kv_heads)
    assert torch.allclose(out, expected, atol=1e-5)


def test_recent_only_identical_keys_equals_mean_of_values():
    """Identical keys -> equal scores -> uniform softmax -> mean of recent_v."""
    num_kv_heads, num_query_heads, head_dim = 2, 8, HEAD_DIM_RECENT
    store = _make_store(head_dim, num_kv_heads)
    recent_len = 4
    query = torch.randn(1, num_query_heads, head_dim)  # arbitrary; keys uniform
    recent_k = torch.ones(recent_len, num_kv_heads, head_dim)
    recent_v = torch.randn(recent_len, num_kv_heads, head_dim)

    out = compute_hybrid_attention(
        query, store, recent_k, recent_v, num_query_heads=num_query_heads
    )

    expected = _expected_mean_broadcast(recent_v, num_query_heads, num_kv_heads)
    assert torch.allclose(out, expected, atol=1e-5)


def test_recent_only_one_token_returns_that_value():
    """recent_len == 1: softmax over one token is 1.0 -> output is that value."""
    num_kv_heads, num_query_heads, head_dim = 2, 8, HEAD_DIM_RECENT
    store = _make_store(head_dim, num_kv_heads)
    query = torch.randn(1, num_query_heads, head_dim)
    recent_k = torch.randn(1, num_kv_heads, head_dim)
    recent_v = torch.randn(1, num_kv_heads, head_dim)

    out = compute_hybrid_attention(
        query, store, recent_k, recent_v, num_query_heads=num_query_heads
    )

    expected = _expected_mean_broadcast(recent_v, num_query_heads, num_kv_heads)
    assert torch.allclose(out, expected, atol=1e-5)


def test_empty_recent_buffer_treated_as_no_recent():
    """recent_k.shape[0] == 0 -> has_recent False; empty store -> zeros branch."""
    num_kv_heads, num_query_heads, head_dim = 2, 8, HEAD_DIM_RECENT
    store = _make_store(head_dim, num_kv_heads)
    query = torch.randn(1, num_query_heads, head_dim)
    recent_k = torch.zeros(0, num_kv_heads, head_dim)
    recent_v = torch.zeros(0, num_kv_heads, head_dim)

    out = compute_hybrid_attention(
        query, store, recent_k, recent_v, num_query_heads=num_query_heads
    )

    assert out.shape == (1, num_query_heads, head_dim)
    assert (out == 0).all()


# ---------------------------------------------------------------------------
# Compressed-only and hybrid paths (lossy — structural assertions only)
# ---------------------------------------------------------------------------


def test_compressed_only_path_structural():
    num_kv_heads, num_query_heads, head_dim = 2, 8, HEAD_DIM_COMPRESSED
    store = _make_store(head_dim, num_kv_heads)
    store.append_chunk(
        torch.randn(16, num_kv_heads, head_dim),
        torch.randn(16, num_kv_heads, head_dim),
    )
    query = torch.randn(1, num_query_heads, head_dim)

    out = compute_hybrid_attention(
        query, store, recent_k=None, recent_v=None, num_query_heads=num_query_heads
    )

    assert out.shape == (1, num_query_heads, head_dim)
    assert out.dtype == query.dtype
    assert out.device == query.device
    assert torch.isfinite(out).all()


def test_hybrid_path_structural():
    num_kv_heads, num_query_heads, head_dim = 2, 8, HEAD_DIM_COMPRESSED
    store = _make_store(head_dim, num_kv_heads)
    store.append_chunk(
        torch.randn(16, num_kv_heads, head_dim),
        torch.randn(16, num_kv_heads, head_dim),
    )
    query = torch.randn(1, num_query_heads, head_dim)
    recent_k = torch.randn(4, num_kv_heads, head_dim)
    recent_v = torch.randn(4, num_kv_heads, head_dim)

    out = compute_hybrid_attention(
        query, store, recent_k, recent_v, num_query_heads=num_query_heads
    )

    assert out.shape == (1, num_query_heads, head_dim)
    assert out.dtype == query.dtype
    assert out.device == query.device
    assert torch.isfinite(out).all()


# ---------------------------------------------------------------------------
# Scale, GQA, and decode-vs-prefill behavior
# ---------------------------------------------------------------------------


def test_scale_defaults_to_inverse_sqrt_head_dim():
    """scale=None must equal explicit 1/sqrt(head_dim) and differ from a wrong scale."""
    num_kv_heads, num_query_heads, head_dim = 2, 8, HEAD_DIM_RECENT
    store = _make_store(head_dim, num_kv_heads)
    query = torch.randn(1, num_query_heads, head_dim)
    recent_k = torch.randn(5, num_kv_heads, head_dim)
    recent_v = torch.randn(5, num_kv_heads, head_dim)

    out_default = compute_hybrid_attention(
        query, store, recent_k, recent_v, num_query_heads=num_query_heads
    )
    out_explicit = compute_hybrid_attention(
        query,
        store,
        recent_k,
        recent_v,
        num_query_heads=num_query_heads,
        scale=1.0 / math.sqrt(head_dim),
    )
    out_wrong = compute_hybrid_attention(
        query,
        store,
        recent_k,
        recent_v,
        num_query_heads=num_query_heads,
        scale=5.0,
    )

    assert torch.allclose(out_default, out_explicit, atol=1e-5)
    assert not torch.allclose(out_default, out_wrong, atol=1e-5)


def test_gqa_expansion_output_head_count():
    """num_query_heads = gqa_ratio * num_kv_heads; heads in a group share a kv head."""
    num_kv_heads, num_query_heads, head_dim = 2, 8, HEAD_DIM_RECENT  # gqa_ratio = 4
    store = _make_store(head_dim, num_kv_heads)
    recent_k = torch.randn(5, num_kv_heads, head_dim)
    recent_v = torch.randn(5, num_kv_heads, head_dim)
    # All query heads identical -> heads in the same GQA group must produce equal output.
    query = torch.randn(1, 1, head_dim).expand(1, num_query_heads, head_dim).contiguous()

    out = compute_hybrid_attention(
        query, store, recent_k, recent_v, num_query_heads=num_query_heads
    )

    assert out.shape[1] == num_query_heads
    gqa_ratio = num_query_heads // num_kv_heads  # 4
    # Group 0 = query heads [0, gqa_ratio); group 1 = [gqa_ratio, 2*gqa_ratio).
    for offset in range(1, gqa_ratio):
        assert torch.allclose(out[0, 0], out[0, offset], atol=1e-5)
        assert torch.allclose(out[0, gqa_ratio], out[0, gqa_ratio + offset], atol=1e-5)
    # Different kv heads -> different group outputs (with distinct value rows).
    assert not torch.allclose(out[0, 0], out[0, gqa_ratio], atol=1e-5)


def test_incompatible_gqa_shapes_raises_value_error():
    """num_query_heads != num_kv_heads * gqa_ratio raises ValueError from _matmul_attend."""
    num_kv_heads, num_query_heads, head_dim = 2, 3, HEAD_DIM_RECENT  # gqa_ratio = 1, 2 != 3
    store = _make_store(head_dim, num_kv_heads)
    query = torch.randn(1, num_query_heads, head_dim)
    recent_k = torch.randn(4, num_kv_heads, head_dim)
    recent_v = torch.randn(4, num_kv_heads, head_dim)

    with pytest.raises(ValueError):
        compute_hybrid_attention(query, store, recent_k, recent_v, num_query_heads=num_query_heads)


def test_multi_token_query_decode_vs_prefill():
    """T > 1 query (prefill-style) on the recent-only path: shape (T, Q, D), finite."""
    num_kv_heads, num_query_heads, head_dim = 2, 8, HEAD_DIM_RECENT
    num_tokens = 4
    store = _make_store(head_dim, num_kv_heads)
    query = torch.randn(num_tokens, num_query_heads, head_dim)
    recent_k = torch.randn(5, num_kv_heads, head_dim)
    recent_v = torch.randn(5, num_kv_heads, head_dim)

    out = compute_hybrid_attention(
        query, store, recent_k, recent_v, num_query_heads=num_query_heads
    )

    assert out.shape == (num_tokens, num_query_heads, head_dim)
    assert torch.isfinite(out).all()


def test_runs_offline_on_cpu():
    """Guard: store + tensors are CPU-resident, no network/DB/model used."""
    num_kv_heads, num_query_heads, head_dim = 2, 8, HEAD_DIM_RECENT
    store = _make_store(head_dim, num_kv_heads)
    assert store.device == CPU

    query = torch.randn(1, num_query_heads, head_dim, device=CPU)
    recent_k = torch.randn(3, num_kv_heads, head_dim, device=CPU)
    recent_v = torch.randn(3, num_kv_heads, head_dim, device=CPU)

    out = compute_hybrid_attention(
        query, store, recent_k, recent_v, num_query_heads=num_query_heads
    )

    assert out.device == CPU
    assert torch.isfinite(out).all()
