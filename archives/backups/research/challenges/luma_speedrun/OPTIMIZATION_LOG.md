# Optimization Log — Luma AMD Speedrun

## Current Bests (manderson240)
| Kernel | Ranked Score | Rank | Leader | File |
|--------|-------------|------|--------|------|
| GEMM | 13.425µs | ~126/391 | 4.354µs | `submission_naive_13us.py` (aiter baseline) |
| MoE | 154.183µs | ~63/274 | 70.470µs | Original `submission.py` (default fused_moe) |
| MLA | 69.745µs | ~96/? | 19.484µs | Original `submission.py` (einsum+ASM hybrid) |

## Cycle Log

| # | Time | Kernel | Approach | Ranked Score | vs Best | Verdict |
|---|------|--------|----------|-------------|---------|---------|
| — | Session 91 | GEMM | v5 custom MFMA | 27.174µs | +102% | WORSE |
| — | Session 91 | GEMM | v6 hybrid | 23.987µs | +78% | WORSE |
| — | Session 91 | MoE | dispatch_policy=1 | 214.153µs | +39% | WORSE |
| — | Session 91 | MLA | hybrid_v2 wider einsum | 83.320µs | +19% | WORSE |
| — | Session 91 | MLA | hybrid earlier | 79.484µs | +14% | WORSE |

## Session 92 Cycles

| # | Time | Kernel | Approach | Ranked Score | vs Best | Verdict |
|---|------|--------|----------|-------------|---------|---------|
| G1 | skip | GEMM | Per-shape timing (sync overhead poisoned data) | N/A | N/A | SKIP — used task.yml ref times instead |
| G2 | 04:30 | GEMM | gemm_a4w4_asm log2_k_split=1 for K≥2048 | N/A | ❌ K=7168 fails | FAIL — k_split breaks M=8 K=7168 |
| G6 | 05:31 | GEMM | AITER_BYPASS_TUNE_CONFIG=1 | 24.091µs | +79% WORSE | FAIL — bypass selects slower kernel |
| G7 | 05:27 | GEMM | AITER_USE_NT=1 + BYPASS | N/A | N/A | BLOCKED — "work on another stream" error |
| A2 | 04:50 | MLA | num_kv_splits=32 fixed (match reference) | PENDING | PENDING | Leaderboard scheduled |

## Research Findings (Session 92)

### GEMM Leader Analysis (from research agent)
- **bhagawan-yantrion** (4.354µs, 405 submissions): Yantrion Inc, UC Berkeley
- **mars-compute** (4.409µs, **1 submission!**): Mars Compute startup, automated kernel gen
- **Key technique: shape-specialized dispatch** — different kernel configs per M value
  - M=4,16: Split-K + small tiles, maximize CU occupancy
  - M=32,64: Medium tiles, 4-wave scheduling
  - M=256: 8-wave ping-pong, 256×256 tiles, double-buffered LDS
- **petit-kernel** achieves 2.56× over hipBLASLt for M=16 decode
- **HuggingFace skinny GEMM**: producer-consumer warp specialization for small M
- **RadeonFlow** (2025 winner): custom HIP kernels with load_inline

## Key Research Finding (Session 92)

**API tuning is EXHAUSTED for GEMM.** G2 (k_split), G6 (bypass), G7 (NT) all failed or regressed.
Only custom load_inline kernels can close the 3× gap. The leaders use:
1. **Shape-specialized dispatch** — different kernel config per M value
2. **Split-K for M=4,16** — parallelize K dimension for small M
3. **8-wave ping-pong** with double-buffered LDS for M=64,256
4. **Producer-consumer warp specialization** — 8 producer warps + 3 consumer warps

**mars-compute** achieved 4.409µs in **1 submission** — automated kernel generation.
**petit-kernel** achieves 2.56× over hipBLASLt for M=16 decode shapes.
**HuggingFace skinny GEMM** uses sparse MFMA for M≤8.

See: SESSION_91_FINAL.md, RANKED_SHAPES.md, LEADERBOARD_SCORES.md

## Queue Position
- GEMM: API tuning exhausted. Next: **Build split-K custom kernel for M=4,16** (the breakthrough path)
- MoE: At M1 (clean baseline pending leaderboard). Next: M2 (KSPLIT for d_expert=256)
- MLA: At A2 (splits=32 pending leaderboard). Next: A3 (MXFP4 KV cache)

## Pending Leaderboard Results
- MLA A2 (splits=32): background submission scheduled, check web
- MoE M1 (clean baseline): background submission scheduled, check web

## Files Ready for Next Session
- `amd-mxfp4-mm/submission_g6_bypass.py` — BYPASS (24.091µs, WORSE)
- `amd-mxfp4-mm/submission_g7_nt.py` — NT+BYPASS (BLOCKED by stream error)
- `amd-mixed-mla/submission_a2_splits.py` — splits=32 (pending leaderboard)
- `amd-moe-mxfp4/submission_m1_clean.py` — clean baseline (pending leaderboard)
| M2b | 05:55 | MoE | No AITER_USE_NT | N/A | N/A | BLOCKED — stream error without NT |
| M2 | 05:50 | MoE | KSPLIT=0 for d_expert<=512 + NT | PENDING | PENDING | Test passed 3/3, leaderboard pending |
| splitK | 05:35 | GEMM | Split-K v1 (sequential launches) | PENDING | PENDING | 4/4 pass, leaderboard pending |
| splitK2 | 05:45 | GEMM | Split-K v2 (parallel blockIdx.z) | 19.5-24.2µs bench | N/A | Slower than aiter (atomicAdd overhead) |
| G8 | 05:55 | GEMM | Lean aiter (pre-resolved refs) | 19.5-33.4µs bench | N/A | No improvement (bottleneck is GPU, not Python) |
| A3 | 05:40 | MLA | MXFP4 KV cache | PENDING | PENDING | 4/4 pass, leaderboard pending |

## New API Discoveries (Session 92 probes)
- `hipb_mm(mat1, mat2, solution_index, ...)` — hipBLASLt with selectable kernel
- `gemm_a16w16_asm(A, B, out, splitK=N)` — BF16 ASM GEMM with split-K
- `tl.dot_scaled` — Triton native FP4 scaled dot product
- `compute_gemm_SplitK(M,N,K,tile_m,tile_n,tile_k)` — split-K parameter calculator
- `deepgemm(XQ, WQ, Y, group_layout, x_scale, w_scale)` — DeepSeek GEMM
- `AITER_USE_NT=1` REQUIRED for MoE (causes stream error without it)
- `AITER_USE_NT=1` BLOCKED for GEMM (causes stream error WITH it)
| splitK1 | 06:33 | GEMM | Split-K v1 (sequential, M<=16) | 26.521µs | +97% WORSE | FAIL — atomicAdd+zero overhead exceeds occupancy gain |
| M2 | 09:29 | MoE | KSPLIT=0 for d_expert<=512 | 186.317µs | +21% WORSE | FAIL — KSPLIT=0 hurts ranked shapes |
| triton_bf16 | 06:50 | GEMM | BF16 torch.mm (skip quant) | FAIL | FAIL | 1% tolerance incompatible with BF16 |
| A2 | 09:38 | MLA | num_kv_splits=32 fixed | 77.723µs | +11% WORSE | FAIL — fixed splits=32 worse than adaptive |

## Session 92 Final Verdict

**10 attempts, 0 improvements.** Every API-level change scores worse on ranked:

| Count | Kernel | Approaches Tried | Best Ranked Impact |
|-------|--------|-----------------|-------------------|
| 6 | GEMM | G2 k_split, G6 BYPASS, G7 NT, split-K v1/v2, BF16 | All WORSE or BLOCKED |
| 2 | MoE | M2 KSPLIT=0, M2b no-NT | Both WORSE or BLOCKED |
| 2 | MLA | A2 splits=32, Triton BF16 | Both WORSE or incompatible |

**Conclusion:** API tuning and parameter variations are EXHAUSTED across all 3 kernels.
The aiter defaults are locally optimal for the ranked shape distributions.
Only custom load_inline kernels with MFMA intrinsics can close the gap.

**Next session must:** Build a complete custom kernel, not tweak parameters.
| custom_mla | 10:15 | MLA | Custom Split-K GEMV attention (BF16 KV) | PENDING | PENDING | 4/4 pass, leaderboard pending |
| custom_mla | 10:30 | MLA | Custom Split-K GEMV (BF16 KV, 256 threads) | ~16ms on large shapes | MUCH WORSE | FAIL — sync per KV entry is O(kv_len × sync) |

## Custom Kernel Architecture Learnings

### MLA Custom Kernel v1 (Split-K with thread-cooperative dot)
- WRONG: __syncthreads() per KV entry → O(kv_len × sync_overhead) → 16ms for large shapes
- Each KV entry requires full block reduction for the 576-dim dot product

### MLA Custom Kernel v2 (Per-thread independent KV processing)  
- Each thread does all 576 dims independently → no inter-thread sync during KV loop
- BUT: 576 scalar multiply-adds per KV entry per thread → no MFMA acceleration
- AND: reduction at end has thread 0 iterating 512×64 = 32K elements sequentially
- NEED: Split-D (576=512+64) with MFMA tiles for the sub-products

### Key Insight: Why ASM is fast
The ASM kernel uses MFMA hardware for Q@K^T, processing multiple KV entries
per MFMA tile. A competitive custom kernel MUST use MFMA, not scalar ops.
For MLA with head_dim=576: Split-D into 512+64, use MFMA 32×32 tiles for
the 512-dim sub-product, scalar for the 64-dim RoPE sub-product.
| compile | 10:50 | GEMM | torch.compile(mode=default) | CRASH | CRASH | internal error — aiter ops incompatible |
| compile_ro | 10:45 | GEMM | torch.compile(reduce-overhead) | CRASH | CRASH | internal error — CUDA graph conflict |
| mfma128 | 11:30 | GEMM | 128×128 8-wave LDS MFMA | >6min benchmark (TIMEOUT) | MUCH WORSE | FAIL — byte-by-byte LDS loading still dominates |
| hk_probe | 11:20 | GEMM | HipKittens availability | N/A | N/A | NOT INSTALLED on runner |

## Session 93 Cycles

| # | Time | Kernel | Approach | Benchmark Geomean | vs Baseline | Verdict |
|---|------|--------|----------|-------------------|-------------|---------|
| G9 | 15:30 | GEMM | per_1x32_f4_quant_hip | N/A | N/A | BLOCKED — stream error |
| G10 | 15:35 | GEMM | HIP_FORCE_DEV_KERNARG=1 | ~22.7µs | same | NO CHANGE |
| M6 | 15:25 | MoE | QuantType.per_tensor for d_expert≤512 | N/A | N/A | RISK — scales incompatible |
| M7 | 15:40 | MoE | HIP_FORCE_DEV_KERNARG=1 | ~185µs | same | NO CHANGE |
| M8 | 15:50 | MoE | doweight_stage1=True | FAIL | FAIL | FAIL — exceeds 5% tolerance |
| A5 | 15:25 | MLA | optimized num_kv_splits | ~same | same | NO CHANGE |
| A6 | 15:35 | MLA | HIP_FORCE_DEV_KERNARG=1 + splits | ~same | same | NO CHANGE |
| **A7** | **16:00** | **MLA** | **fast_mode=True** | **~63µs** | **-6% faster** | **PENDING leaderboard** |

## Key Session 93 Finding: MLA fast_mode=True

fast_mode=True in get_mla_metadata_v1 shows ~5% improvement across medium-large shapes:
- bs=32,kv=1024: 40.3→38.3µs (-5.0%)
- bs=32,kv=8192: 105→100µs (-4.8%)
- bs=64,kv=8192: 154→145µs (-5.8%)
- bs=256,kv=1024: 106→101µs (-4.7%)

Submitted to leaderboard. Current MLA best: 69.745µs.
