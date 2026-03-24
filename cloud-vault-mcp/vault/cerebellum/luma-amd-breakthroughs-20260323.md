---
type: breakthrough
name: luma-amd-breakthroughs-20260323
description: "Key breakthroughs for Luma AMD Speedrun: Persistent Triton MLA, Active MoE Masking, and Optimized GEMM"
created: 2026-03-23
title: "Luma AMD Breakthroughs — CDNA 4 (MI355X) Optimization"
tags: [cerebellum, amd, mi355x, breakthrough, mla, moe, gemm, triton]
aspect: knower
---

# Luma AMD Speedrun Breakthroughs (2026-03-23)

## 1. MLA: Persistent Triton FlashMLA
**Problem**: 15× gap between current best (67µs) and leader (4.3µs). Bottleneck identified as Python/Triton dispatch floor per batch item in the three-regime routing.
**Breakthrough**: A single persistent Triton kernel that:
- Fuses QK dot product, Online Softmax, and V accumulation into a single launch.
- Uses `tl.dot` (Matrix Cores) instead of `tl.sum` for 10× throughput.
- Supports FP8 KV cache directly in Triton.
- **Target**: <10µs.

## 2. GEMM: Refined Triton `tl.dot_scaled`
**Problem**: Current ASM kernel (14.1µs) is 1.45× slower than leader (9.7µs).
**Breakthrough**: Fully exploit Triton's native `tl.dot_scaled` for MXFP4.
- MI355X-specific tiling (BLOCK_M=64, BLOCK_N=128).
- LDS swizzle to eliminate bank conflicts during scaling factor loads.
- **Target**: <10µs.

## 3. MoE: Active-Expert Masking + JIT Persistence
**Problem**: JIT timeout (720s) and overhead from empty experts (224/257).
**Breakthrough**: 
- `expert_mask` logic to skip sorting/compute for unused experts.
- `AITER_JIT_DIR` environment variable to persist kernels across Popcorn CLI submissions.
- **Target**: <145µs (Leader level).

## Graph Relations
- [[luma-amd-speedrun-strategy]] — Implementation strategy
- [[flashattention-mla]] — Related attention architecture
- [[moe-fused-kernels]] — Fused kernel optimization

## Implementation Status
- [ ] MoE Breakthrough staged: `submission.breakthrough.moe.py`
- [ ] GEMM Breakthrough staged: `submission.breakthrough.gemm.py`
- [ ] MLA Breakthrough staged: `submission.breakthrough.mla.py`

## Critical Constraints

### 1. Stream Integrity (The "500 Error" Fix)
All GPU operations MUST occur on the stream provided by the benchmarking harness.
- **Problem**: Using the default stream (0) or creating new streams causes measurement mismatches and server crashes.
- **Rule**: Every `hipLaunchKernelGGL` or `hipMemcpyAsync` call must explicitly pass the stream handle.
- **Python Implementation**: Use `torch.cuda.current_stream().cuda_stream` to get the raw stream pointer and pass it to `ctypes` wrappers.

### 2. Scanner Blocks
- Runtime compilation via `subprocess.run(["amdclang++", ...])` is blocked on the runner.
- **Solution**: Prioritize Triton (Python-based JIT) or utilize pre-existing kernels in `aiter`.
