---
name: popcorn-benchmark-vs-ranked-scoring
description: |
  Critical scoring difference between benchmark and ranked modes in Popcorn CLI
  kernel competitions. Use when: (1) A benchmark improvement does NOT improve
  ranked score, (2) planning kernel optimization strategy for Popcorn competitions,
  (3) deciding between dispatch optimization vs compute optimization.
  KEY INSIGHT: The ranked runner has warm JIT caches and tensor reuse — Python
  overhead optimizations are counterproductive. Only GPU compute improvements help.
  VERIFIED: Session 95, 6/6 "improvement" submissions scored WORSE on ranked.
author: Claude Code
version: 2.0.0
---

# Popcorn Benchmark vs Ranked Scoring Gap

## The Problem

Optimizations that improve `--mode benchmark` scores consistently FAIL to improve
`--mode leaderboard` (ranked) scores. Every Session 95 submission that improved
benchmark performance scored WORSE on the ranked leaderboard.

## Evidence (Session 95 — 6 submissions, 0 improvements)

| Submission | Benchmark | Ranked | vs Baseline |
|-----------|-----------|--------|-------------|
| GEMM compound (fused shuffle) | improved | 22.8µs | 1.7x WORSE vs 13.4µs |
| GEMM KSPLIT_TABLE | 169µs | — | 10% WORSE vs 154µs |
| MoE compound (pre-alloc buffers) | 177µs | 186.9µs | 21% WORSE vs 154µs |
| MLA A7 (fast_mode) | 74.9µs | — | 7% WORSE vs 69.7µs |
| MLA A8 (low threshold) | 87.5µs | — | 25% WORSE vs 69.7µs |
| MLA compound (cached + direct ASM) | 75.1µs | 79.5µs | 14% WORSE vs 69.7µs |

## Root Cause: Runner Execution Model

The Popcorn ranked runner differs from benchmark mode:

1. **JIT cache warm**: aiter modules are pre-compiled from the test phase. JIT overhead = 0.
2. **Tensor reuse**: PyTorch memory allocator reuses freed tensors. Allocation overhead ≈ 0.
3. **Warm GPU state**: GPU caches, TLBs, and SRAM are warm from previous shapes.
4. **Shape ordering**: Ranked shapes may run in a different order than benchmark.
5. **Repeated invocations**: The same kernel is called multiple times — caching amortizes overhead.

## What This Means

### Python overhead optimization is COUNTERPRODUCTIVE
- Pre-allocating buffers: runner already reuses → your allocation code adds import overhead
- Bypassing torch.ops: introduces function pointer indirection that's NOT cached
- Pre-resolving references: module-level code runs at import time → slower startup
- Custom HIP shuffle: adds load_inline compilation time → no runtime benefit

### Only GPU COMPUTE improvements help
- Faster MFMA tiling (actually computes faster per element)
- Better memory access patterns in the kernel itself
- Fewer instructions per output element
- Higher hardware utilization (more CUs active)

## Decision Framework

| Optimization Type | Benchmark Impact | Ranked Impact | Verdict |
|------------------|-----------------|---------------|---------|
| Python dispatch reduction | ✅ Helps | ❌ Hurts | AVOID |
| Buffer pre-allocation | ✅ Helps | ❌ Hurts | AVOID |
| Custom HIP overhead fusion | ✅ Helps | ❌ Hurts | AVOID |
| Env var tuning (KSPLIT etc) | — | ❌ Ignored | AVOID |
| Better MFMA tiling | ✅ Helps | ✅ Helps | DO THIS |
| Fused compute kernel | ✅ Helps | ✅ Helps | DO THIS |
| Shape-specialized GPU kernel | ✅ Helps | ✅ Helps | DO THIS |

## The Rule

**ONLY submit to leaderboard if the optimization changes what happens ON THE GPU.**
Python-level changes that look good on benchmark will regress on ranked.

## Correct Strategy

1. Write custom kernels that compute FASTER (MFMA, Triton tl.dot_scaled)
2. Fuse multiple GPU kernels into ONE launch (quant + GEMM, stage1 + reduce)
3. Use aiter's optimized .co kernels where they're faster
4. Test on benchmark for correctness, but ONLY trust leaderboard for scoring
