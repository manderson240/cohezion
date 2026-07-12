"""V-model tests for the KV-cache budget pre-flight gate (cohezion.inference.kv_budget).

Turns overnight finding A9 (KV-cache memory formula) into a deterministic OOM guard that
replaces harness note N3's "non-deterministic, depends on free memory at load" caution.
Reference anchors are the published Llama-3.1-8B numbers; the N3 scenario encodes the real
2026-06-09 crash + its fix (bound ctx_size).
"""

from __future__ import annotations

import pytest

from cohezion.inference.kv_budget import kv_cache_bytes, preflight


_GiB = 1024**3


# --- kv_cache_bytes: reference-anchored (Llama-3.1-8B: 32 layers, 8 KV heads, head_dim 128) ---
def test_kv_bytes_matches_published_reference_fp16_32k():
    b = kv_cache_bytes(
        num_layers=32, num_kv_heads=8, head_dim=128, seq_len=32768, cache_dtype="fp16"
    )
    assert b / _GiB == pytest.approx(4.0, abs=0.05)  # published ~4 GB @32k


def test_kv_bytes_matches_published_reference_fp16_128k():
    b = kv_cache_bytes(
        num_layers=32, num_kv_heads=8, head_dim=128, seq_len=131072, cache_dtype="fp16"
    )
    assert b / _GiB == pytest.approx(16.0, abs=0.1)  # published ~16 GB @128k


def test_kv_bytes_dtype_scaling_q8_half_q4_quarter():
    base = {"num_layers": 32, "num_kv_heads": 8, "head_dim": 128, "seq_len": 131072}
    fp16 = kv_cache_bytes(**base, cache_dtype="fp16")
    assert kv_cache_bytes(**base, cache_dtype="q8_0") == fp16 // 2
    assert kv_cache_bytes(**base, cache_dtype="q4_0") == fp16 // 4


def test_kv_bytes_linear_in_ctx_and_batch():
    base = {"num_layers": 32, "num_kv_heads": 8, "head_dim": 128, "cache_dtype": "fp16"}
    assert kv_cache_bytes(**base, seq_len=2048, batch=1) * 4 == kv_cache_bytes(
        **base, seq_len=8192, batch=1
    )
    assert kv_cache_bytes(**base, seq_len=4096, batch=1) * 3 == kv_cache_bytes(
        **base, seq_len=4096, batch=3
    )


def test_kv_bytes_rejects_unknown_dtype():
    with pytest.raises(KeyError):
        kv_cache_bytes(
            num_layers=32, num_kv_heads=8, head_dim=128, seq_len=1024, cache_dtype="int3"
        )


# --- preflight gate: the deterministic OOM guard (fit decision + diagnostics) ---
def test_preflight_allows_a_load_that_fits():
    ok, info = preflight(
        free_bytes=90 * _GiB,
        weight_bytes=5 * _GiB,
        num_layers=32,
        num_kv_heads=8,
        head_dim=128,
        seq_len=32768,
        cache_dtype="fp16",
        buffer_bytes=8 * _GiB,
    )
    assert ok is True
    assert info["headroom_bytes"] > 0
    assert info["kv_bytes"] / _GiB == pytest.approx(4.0, abs=0.05)


def test_preflight_refuses_a_load_that_would_oom():
    ok, info = preflight(
        free_bytes=19 * _GiB,
        weight_bytes=20 * _GiB,
        num_layers=64,
        num_kv_heads=8,
        head_dim=128,
        seq_len=262144,
        cache_dtype="fp16",
        buffer_bytes=8 * _GiB,
    )
    assert ok is False
    assert info["headroom_bytes"] < 0


def test_preflight_encodes_the_n3_incident_full_ctx_refuses_bounded_ctx_fits():
    """The 2026-06-09 crasher: a heavy model at FULL context OOMs even with lots of free
    memory; the fix is to BOUND ctx_size. The gate must refuse the first and allow the second."""
    heavy = {
        "free_bytes": 90 * _GiB,
        "weight_bytes": 20 * _GiB,
        "num_layers": 64,
        "num_kv_heads": 8,
        "head_dim": 128,
        "cache_dtype": "fp16",
        "buffer_bytes": 8 * _GiB,
    }
    ok_full, _ = preflight(**heavy, seq_len=262144)  # ctx_size=0 -> full 256k context (the crash)
    ok_bounded, _ = preflight(**heavy, seq_len=16384)  # the N3 fix: bound to 16384
    assert ok_full is False  # would OOM -> refused (deterministic, not "depends on luck")
    assert ok_bounded is True  # bounded ctx fits -> allowed


def test_preflight_q8_cache_lets_a_borderline_load_fit_that_fp16_would_not():
    """The A3 lever inside the same formula: halving the KV dtype can turn a refuse into an allow."""
    # free (34) sits between the FP16 total (20w+16kv+4buf=40) and the Q8 total (20w+8kv+4buf=32),
    # so halving the KV dtype flips the decision refuse -> allow.
    common = {
        "free_bytes": 34 * _GiB,
        "weight_bytes": 20 * _GiB,
        "num_layers": 64,
        "num_kv_heads": 8,
        "head_dim": 128,
        "seq_len": 65536,
        "buffer_bytes": 4 * _GiB,
    }
    ok_fp16, _ = preflight(**common, cache_dtype="fp16")
    ok_q8, _ = preflight(**common, cache_dtype="q8_0")
    assert ok_fp16 is False
    assert ok_q8 is True


def test_preflight_info_is_a_complete_diagnostic():
    _, info = preflight(
        free_bytes=90 * _GiB,
        weight_bytes=5 * _GiB,
        num_layers=32,
        num_kv_heads=8,
        head_dim=128,
        seq_len=32768,
        cache_dtype="fp16",
        buffer_bytes=8 * _GiB,
    )
    assert set(info) >= {
        "kv_bytes",
        "weight_bytes",
        "total_bytes",
        "free_bytes",
        "buffer_bytes",
        "headroom_bytes",
    }
    assert info["total_bytes"] == info["kv_bytes"] + info["weight_bytes"]
