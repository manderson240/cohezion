# Custom Triton Kernels: 6-Day Optimization Plan

**Competition**: Luma AMD Speedrun  
**Hardware**: AMD MI355X (gfx950, ROCm 7.1)  
**Date**: March 24, 2026

---

## Executive Summary

All three kernels have exhausted Python-level API optimizations. The remaining path to
competitive scores requires custom kernels. Below is the prioritized research plan.

| Kernel | Current | Leader | Gap | Priority | Rationale |
|--------|---------|--------|-----|---------|-----------|
| **GEMM** | 13.4µs | 4.3µs | **3.1×** | **#1** | Largest gap; quantization bottleneck is architectural; fusion is the known solution |
| **MLA** | 69.7µs | 33.0µs | **2.1×** | #2 | 3-stage pipeline overhead is fundamental; leaders use single-fused kernel |
| **MoE** | 154µs | 110µs | **1.4×** | #3 | Smallest gap; JIT timeout is structural; parameter tuning already exhausted |

---

## 1. GEMM: Priority #1

### Problem Analysis

```
Quantization dispatch:  ~26µs (constant, all shapes)
GEMM compute (ASM):     ~7-10µs
─────────────────────────────────
Total:                 ~34-39µs before fusion
Leader:                ~4.3µs
```

**Root cause**: Quantization (`dynamic_mxfp4_quant` + `e8m0_shuffle`) dominates GEMM compute.
All Python-level GEMM APIs are exhausted:
- `gemm_afp4wfp4`: `float4_e2m1fn_x2` KeyError on runner (completely inaccessible)
- `gemm_a4w4_blockscale`: "This GEMM is not supported!" — JIT build times out
- Custom Triton `tl.dot_scaled`: 68% slower than pre-compiled ASM

### Technical Approach: Fused Quant+GEMM via HipKittens DSL

**Why HipKittens**: Paper (arxiv:2511.08083) shows tile-based DSL outperforms aiter's
hand-ASM on MI355X. 8-Wave Ping-Pong scheduling for GEMM.

**What to implement**:
1. Write MXFP4 GEMM using HipKittens tile primitives (NOT copying HK kernels — original work)
2. Fuse `dynamic_mxfp4_quant` + `e8m0_shuffle` + `gemm_a4w4` into single kernel
3. Handle E8M0 scale layout: RHS scale must be `[BLOCK_N, SCALE_PER_K]` (N-first, not transposed)
4. Use `tl.dot_scaled` with proper scale layout — B_scale_sh is shuffled (E8M0 format)
5. BLOCK_K >= 64 for uint8 packed bytes; pack fp4 nibbles via `sum-as-OR`

**Key constraints from `amd-gfx950-tl-dot-scaled-constraints`**:
- RHS scale must be `[BLOCK_N, SCALE_PER_K]` — N-first layout
- `lhs_scale` must be `[BLOCK_M, SCALE_PER_K]`
- `BLOCK_K >= 128` BF16 elements for `tl.dot_scaled`
- `fp4_max = 6.0` in E8M0 formula

**XCD Remapping Bug**: cdiv() creates non-bijective tile mapping for shapes where
`total_tiles % NUM_XCDS != 0`. Do NOT copy XCD remapping from `tritonblas.fp4_matmul`.

### Key Challenges

| Challenge | Mitigation |
|-----------|------------|
| E8M0 scale format is shuffled | Study `e8m0_shuffle` bit manipulation; replicate in kernel |
| `float4_e2m1fn_x2` dtype inaccessible | `.view(torch.uint8)` + manual nibble packing |
| 3D tensor integer indexing banned in Triton JIT | Use masked loads/stores; sum-as-OR packing |
| XCD remapping bug | Use group-M swizzle instead of XCD remapping |

### Breakthrough Definition

**< 5µs ranked geomean**: Would require ~6.6× speedup over current 13.4µs.
Fused quant eliminates 26µs quantization; new GEMM compute would be ~7-10µs.
Realistic target: **8-12µs** (2-3× improvement from quantization fusion alone).

---

## 2. MLA: Priority #2

### Problem Analysis

```
Python dispatch floor:     ~20-25µs per torch op
3-stage pipeline:         ~100-150µs overhead (metadata + stage1 + reduce)
────────────────────────────────────────────────────
Total:                    ~69.7µs (best hybrid)
Leader (single-fused CK): ~4.3µs
```

**Root cause**: aiter's 3-stage pipeline has fixed overhead that exceeds actual compute
for small batches. Leaders use one fused CK/ASM kernel.

**Why standard Flash Attention fails**:
- MLA has K≠V head dimension (K=576, V=512)
- Flash Attention kernels expect K_dim == V_dim
- `flash_attn_varlen_func` blocked by CK headdim ≤ 256 hard limit
- Custom Triton flash attention was 9-127× slower (GEMV pattern doesn't fill matrix cores)

### Technical Approach: FlashAttention-Style Single-Pass Kernel

**What to implement**:
1. Single-pass kernel that processes Q tiles (BLOCK_M) while iterating KV tiles (BLOCK_N)
2. Fuses score + softmax + value accumulation in one kernel
3. Handle K=576 for score computation, V=512 for value extraction
4. For K≠V: `tl.dot(q_tile, kv_tile[:, :512].T)` extracts V from fused KV buffer
5. Use persistent kernel with Origami scheduling for small batches

**Key insight from `deepseek-mla-decode-flash-attention-gap`**:
- Decode is GEMV (qseqlen=1): Q is single row per head
- `tl.dot` requires minimum 16×16 tiles — can't fill with 1 row
- Must use **vectorized GEMV** via hipBLAS (torch.einsum) for small batches
- The 3-stage aiter pipeline overhead dominates because compute is too fast

**Regime-based approach** (extend current three-regime routing):
- Small batch: Continue using torch.einsum (already optimal — hipBLAS GEMV)
- Medium batch: Direct ASM dispatch with `fast_mode=False`
- Large batch: Single-fused custom kernel (FlashAttention-style tiling)

**For the custom kernel**: Process multiple Q rows per thread block (BLOCK_M > 1)
to fill matrix cores. For bs=4, qseqlen=1: process all 4 queries in one kernel launch.

### Key Challenges

| Challenge | Mitigation |
|-----------|------------|
| K≠V head dimension (576 vs 512) | Slice KV buffer: `kv_tile[:, :512]` for V extraction |
| GEMV doesn't fill matrix cores | Process BLOCK_M > 1 Q rows; batch multiple queries |
| Persistent kernel + Origami scheduling | Use group-M swizzle; avoid XCD remapping bug |
| 576 NOT power-of-2 | Pad to 512+64 split-D (confirmed 3× slower than einsum — skip split-D) |

### Breakthrough Definition

**< 35µs ranked geomean**: Would require ~2× speedup. Current best is 69.7µs.
Single-fused kernel eliminates 3-stage overhead (~50-100µs). Realistic target: **40-50µs**.

---

## 3. MoE: Priority #3

### Problem Analysis

```
fused_moe (current best): ~154µs
Leader:                    ~110µs
Gap:                       1.4× (smallest)
```

**Root cause**: All API paths exhausted. Parameter tuning done (KSPLIT, BYPASS, block_m).
fmoe_g1u1 is dead (NaN for 32-expert). doweight_stage1 crashes/wrong results.
Custom Triton was 68% slower than CK ASM.

**Structural blocker**: JIT timeout (128-260s) exceeds 720s limit.

### Technical Approach: HipKittens MoE + JIT Cache Warming

**What to implement**:
1. Write MoE kernel using HipKittens tile primitives (2-stage: gate+up / down)
2. Use native `local_expert_mask` in `moe_sorting_fwd` to skip empty experts
3. Pre-warm JIT cache via `AITER_JIT_DIR=/tmp/aiter_jit_cache` to survive timeout
4. Persistent-tile scheduling for better SM utilization

**Key insight from `amd-moe-mxfp4-optimization`**:
- `moe_sorting_fwd(local_expert_mask=...)` is the correct masking path
- Previous attempts (Gate 2) crashed because they masked AFTER sorting, not at sort level
- Only 55/257 experts active for bs=8/topk=9 — 200 empty experts could be skipped
- KSPLIT=4 causes overflow for 32-expert shapes (K/4=128 < cktile minimum)

### Key Challenges

| Challenge | Mitigation |
|-----------|------------|
| JIT timeout (128-260s) | AITER_JIT_DIR persistence; submit KSPLIT=0 only (CK path, ~128s JIT) |
| KSPLIT=4 overflow (32-expert) | Never use split_k > 2 for dexp=512 |
| Stage 2 atomic_add serialization | Group-M swizzle; avoid O(E) overhead |
| Custom Triton 68% slower | Use HipKittens primitives; don't replicate aiter's approach |

### Breakthrough Definition

**< 120µs ranked geomean**: Would require ~1.3× speedup over current 154µs.
HipKittens could yield 10-20µs improvement via fused token permutation + persistent scheduling.
Realistic target: **130-145µs**.

---

## 4. Timeline (6 Days)

| Day | GEMM | MLA | MoE |
|-----|------|-----|-----|
| **1** | Study HipKittens DSL; probe CK-Tile flatmm patterns | Extend three-regime routing; probe for flashinfer/flash_attn | Verify JIT cache warming; test `local_expert_mask` |
| **2** | Write HipKittens MXFP4 GEMM prototype | Implement FlashAttention-style kernel (BLOCK_M > 1) | Write HipKittens MoE prototype |
| **3** | Debug scale layout; fix nibble packing | Debug K≠V extraction; benchmark | Debug expert masking; benchmark |
| **4** | Benchmark + iterate | Benchmark + iterate | Benchmark + iterate |
| **5** | Submit best to leaderboard | Submit best to leaderboard | Submit best to leaderboard |
| **6** | Final optimization pass | Final optimization pass | Final optimization pass |

**Submission budget**: ~10 submissions per kernel total. Use wisely.

---

## 5. Key Files to Reference

| File | Purpose |
|------|---------|
| `amd-gemm-mxfp4-optimization` | GEMM quant bottleneck details; E8M0 algorithm |
| `amd-gfx950-tl-dot-scaled-constraints` | Scale layout rules; BLOCK_K constraints |
| `triton-fp4-inline-quantization` | Triton JIT fp4 patterns; nibble packing |
| `tritonblas-origami-xcd-remapping-bug` | XCD bug (do NOT copy) |
| `amd-mla-decode-optimization` | MLA three-regime routing; direct ASM dispatch |
| `deepseek-mla-decode-flash-attention-gap` | Why Flash Attention fails; GEMV analysis |
| `amd-moe-mxfp4-optimization` | MoE API exhaustion; KSPLIT overflow bug |
| `k-search-llm-kernel-optimization` | K-Search strategies; world model approach |

---

## 6. Dead Ends (Do NOT Retry)

### GEMM
- `gemm_afp4wfp4` — `float4_e2m1fn_x2` KeyError (completely inaccessible)
- `tl.dot_scaled` with custom Triton — 68% slower
- HIP C++ quant kernel — 10% slower than wave64 `tl.max`
- Any parameter sweep of `gemm_a4w4`

### MLA
- Any MXFP4 KV cache path — blocked
- Split-D trick (Q padding) — 2-34× slower than einsum
- `torch.compile` on ROCm — universal anti-pattern for multi-shape
- `EINSUM_THRESHOLD` sweeps — already optimized

### MoE
- `fmoe_g1u1` — NaN for 32-expert, no perf gain for 256-expert
- `doweight_stage1=True` — crashes (cktile) or 82% mismatch (CK)
- `KSPLIT=4` for 32-expert shapes — overflow
- Direct CK dispatch — replicates fused_moe (no gain)

---

## 7. Research-Backed Approaches

| Approach | Source | Applicability |
|----------|--------|---------------|
| **HipKittens DSL** | arxiv:2511.08083 | All 3 kernels — highest potential |
| **GPU Kernel Scientist** | arxiv:2506.20807 | Use LLM as kernel writer with timing feedback |
| **CK-Tile flatmm** | composable_kernel/example/ck_tile/18_flatmm/ | GEMM: study MXFP4 patterns |
| **MAP-Elites + Meta-Prompt Evolution** | arxiv:2603.12440 | Prevent mode collapse in kernel search |
| **QiMeng-GEMM 5-Pattern** | github.com/QiMeng-Team | Structured meta-prompts: tiling, reordering, vectorization, layout, pipeline |

---

## 8. Success Metrics

| Kernel | Current | Day 3 Target | Day 6 Target | Leader |
|--------|---------|-------------|-------------|--------|
| GEMM | 13.4µs | 10-12µs | 8-10µs | 4.3µs |
| MLA | 69.7µs | 50-60µs | 40-50µs | 33.0µs |
| MoE | 154µs | 140-150µs | 130-145µs | 110µs |

**Aggregate points target**: Need ~2,250+ for top-10. Current ~1,212.
Required improvement: ~1,000 points across 3 kernels.
