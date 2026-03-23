---
type: skill
name: luma-amd-speedrun-strategy
description: "Competition strategy for Luma AMD Speedrun on MI355X"
triggers:
  - "Luma AMD Speedrun"
  - "MI355X competition"
  - "kernel competition"
version: 1.0.0
created: 2026-03-17
title: "Luma AMD Speedrun Strategy — MI355X Competition"
date: 2026-03-17
tags: [cerebellum, amd, mi355x, competition, luma-speedrun, gpu-optimization, hip-kernels]
aspect: thinker
---

# Luma AMD Speedrun Strategy

## Competition Overview

**Goal**: Win $650K prize pool by achieving Top 10 on all 3 leaderboards
**Timeline**: March 16-30, 2026 (14 days)
**Hardware**: AMD Instinct MI355X (gfx950)

## Current Status (2026-03-17)

| Kernel | Current | Leader | Gap | Rank |
|--------|---------|--------|-----|------|
| GEMM | ~13.4µs | 9.671µs | 1.39× | ~30 |
| MoE | ~154µs | 145.177µs | 1.06× | ~16 |
| MLA | ~67µs | 4.335µs | 15.5× | ~20 |

## Optimization Strategies

### GEMM (amd-mxfp4-mm)

**Current Approach**: `aiter.gemm_a4w4_asm()` with split-K
**Target**: 9.671µs (leader)
**Strategy**: Custom HIP kernel with:
- Fused quantization + GEMM
- 8-wave ping-pong scheduling
- LDS swizzle for bank conflicts
- Direct global→LDS 128-bit transfers

**Key Parameters**:
- `log2_k_split`: 0-4 (shape-dependent)
- Tile sizes: 256×256×128 for large M
- Kernel: `_ZN5aiter41f4gemm_bf16_per1x32Fp4_BpreShuffle_32x128E`

### MoE (amd-moe-mxfp4)

**Current Approach**: `aiter.fused_moe()` with KSPLIT tuning
**Target**: 145µs (leader)
**Strategy**: Custom fused HIP kernel

**Critical Finding**: `doweight_stage1=True` is **BROKEN**
- CK path: 82% element mismatches
- cktile path: GPU memory fault
- **Always use `doweight_stage1=False`**

**KSPLIT Strategy**:
- `estimated_m < 10`: KSPLIT=4
- `estimated_m < 30`: KSPLIT=2
- `estimated_m >= 30`: KSPLIT=1

### MLA (amd-mixed-mla)

**Current Approach**: `aiter.mla_decode_fwd()` with num_kv_splits
**Target**: 4.335µs (leader) - may be unattainable
**Realistic Target**: 20µs (3× improvement)

**Three-Regime Strategy**:
1. **Small** (bs≤4, total_kv≤65536): `torch.einsum` bf16
2. **Medium** (total_kv≤262144): `mla_decode_fwd` a16w8
3. **Large** (total_kv>262144): `mla_decode_fwd` a8w8

**Custom Kernel Approach**:
- FlashAttention-style fused kernel
- Two-stage: Q×K + Softmax×V
- Use `__builtin_amdgcn_mfma_scale_f32_32x32x64_f8f6f4`
- Target: 64×64 tiles per head

## Submission Workflow

1. **Test Mode First**: Verify compilation and correctness
2. **Leaderboard**: Submit only after test passes
3. **Queue Management**: Max 3 pending per kernel
4. **Variant Tracking**: Document all attempts

## Key Learnings

### What Works
- Shape-aware dispatch (different params per M/N/K)
- Conservative parallelism (avoid overflow)
- FP8 KV cache for MLA (2× bandwidth)
- OPUS sorting for MoE routing

### What Doesn't Work
- `doweight_stage1=True` (catastrophic failure)
- Ultra-aggressive KSPLIT=8 (numerical overflow)
- Pure Triton (too many constraints)
- Maximum aggression everywhere (breaks correctness)

## References

- [[amd-hip-kernel-development]]
- [[cdna4-architecture-gfx950]]
- [[flashattention-mla]]
- [[moe-fused-kernels]]

## Related Submissions

- [[submission-gemm-v11-micro-optimized]]
- [[submission-moe-v14-grid-search]]
- [[submission-mla-v9-grid-search]]

## Vault Navigation

- [[MOC-machine-learning]] — Parent map of content
- [[2026-03-17-session-kimi-k2-5]] — Session log for this work
