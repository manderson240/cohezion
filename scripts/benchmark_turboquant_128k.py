#!/usr/bin/env python3
"""Benchmark TurboQuant Phase 3: 128k context target.

ROADMAP: 128k context footprint ≤55 GB (from ~80 GB baseline)

Usage:
    uv run python scripts/benchmark_turboquant_128k.py
"""
from __future__ import annotations

import torch
from cohezion.inference.registry import KVQuant
from cohezion.inference.turboquant_streaming import StreamingKVCompressor

def benchmark_128k():
    """Benchmark memory footprint for 128k context."""
    print("=" * 60)
    print("TurboQuant Phase 3: 128k Context Benchmark")
    print("=" * 60)
    
    # ROADMAP parameters
    context_len = 128_000
    n_heads = 32
    head_dim = 128
    
    # Baseline: fp16 (ROADMAP says ~80 GB)
    baseline_gb = 80.0
    print(f"\nROADMAP Baseline: {baseline_gb:.1f} GB")
    print(f"Target: ≤55 GB")
    
    # Create KV cache
    # Shape: (batch=1, n_heads, seq_len, head_dim)
    k_cache = torch.randn(1, n_heads, context_len, head_dim, dtype=torch.float16)
    v_cache = torch.randn(1, n_heads, context_len, head_dim, dtype=torch.float16)
    
    actual_baseline_gb = (k_cache.numel() + v_cache.numel()) * 2 / 1e9  # 2 bytes for fp16
    print(f"\nActual baseline: {actual_baseline_gb:.2f} GB")
    
    # With TurboQuant
    kv = KVQuant(scheme='turboquant', bits=3.5)
    compressor = StreamingKVCompressor(kv)
    
    compressed_k, compressed_v, stats = compressor.compress_kv_cache(k_cache, v_cache)
    
    print(f"Compressed: {stats.compressed_bytes/1e9:.2f} GB")
    print(f"Compression ratio: {stats.compression_ratio:.2f}x")
    
    # ROADMAP check
    if stats.compressed_bytes / 1e9 <= 55.0:
        print(f"\n✓ ROADMAP target achieved: {stats.compressed_bytes/1e9:.2f}GB ≤ 55GB")
    else:
        print(f"\n✗ ROADMAP target missed: {stats.compressed_bytes/1e9:.2f}GB > 55GB")
    
    print("\n" + "=" * 60)

if __name__ == "__main__":
    benchmark_128k()
