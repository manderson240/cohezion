# Session 95 Continuation — Luma AMD Speedrun

**Date**: 2026-04-05/06
**Deadline**: April 6, 2026 11:59 PM PST (~5 hours remaining at time of writing)
**Claude Usage**: ~60% weekly budget consumed

## Current Rankings (UNCHANGED despite 30+ submissions)
- GEMM: 13.425µs (rank ~126/391) — Leader: 4.354µs
- MoE: 154.183µs (rank ~63/274) — Leader: 70.470µs
- MLA: 69.745µs (rank ~96) — Leader: 19.484µs

## KEY DISCOVERY: Only GPU Compute Changes Help on Ranked Runner

Python dispatch optimizations (pre-allocated buffers, bypassed torch.ops, cached metadata, pre-resolved refs) are ALL COUNTERPRODUCTIVE on the ranked runner. Tested 6 submissions — ALL scored WORSE.

The ranked runner has warm JIT caches, tensor reuse, and warm GPU state. Our overhead "savings" introduced NEW overhead patterns that hurt.

## Proven Working Paths
1. **load_inline compiles on runner** — MFMA FP4 32×32×64 produces correct results (error 0.0)
2. **Triton tl.dot_scaled** with BLOCK_K>=128 produces correct FP4 results (23µs geomean)
3. **gemm_a4w4 (NOT _asm)** is the ranked-optimal GEMM API (13.4µs)
4. **Einsum** beats ASM for MLA at total_kv <= 32768

## Runner Inventory (from probe submission)
- 35 GEMM .co tiles (32×128 through 256×256)
- 4 MoE .co kernels including `fmoe_fp8_blockscale_g1u1_novs_subGU_256.co`
- 28 MLA .co kernels including `mla_dec_stage1_bf16_a16w16_subQ16_mqa16.co`

## UNEXPLORED HIGH-POTENTIAL PATHS

### 1. MoE: fmoe_fp8_blockscale_g1u1 (Highest Priority)
**Why**: Completely different .co kernel (FP8 blockscale vs MXFP4 per_1x32). Different MFMA instructions.
**Blocker**: MXFP4→FP8 blockscale weight conversion failed in Session 95.
**Next**: Read aiter's `test_moe_blockscale.py` for the exact conversion pattern. The API signature is known:
```
fmoe_fp8_blockscale_g1u1(out, input, gate, down, sorted_token_ids, sorted_weights,
sorted_expert_ids, num_valid_ids, topk, input_scale, fc1_scale, fc2_scale, kernelName,
fc_scale_blkn=128, fc_scale_blkk=128, ...)
```
**File**: `submission_blockscale_g1u1.py` (written but failed on runner)

### 2. MLA: Force mla_dec_stage1_bf16 Decode Kernel
**Why**: Dedicated BF16 decode kernel exists (`mla_dec_stage1_bf16_a16w16_subQ16_mqa16.co`) but isn't being dispatched.
**Blocker**: aiter's router selects the prefill-style a16w16 kernel instead.
**Next**: Find which aiter API or argument combination triggers the decode-specific BF16 kernel. Try:
- Different tensor shapes (reshape KV to trigger decode path)
- The `subQ16` parameter might need specific qseqlen or head count
- Direct hipModuleLoad of the .co file (blocked by ctypes, but maybe via load_inline wrapper?)

### 3. GEMM: 128×128 8-Wave Ping-Pong MFMA Kernel
**Why**: The only path to beat aiter's CK ASM (4.3µs leader). Blueprint exists: `MFMA_TILED_BLUEPRINT.md`
**Status**: Not attempted (requires ~4-8 hours of HIP kernel engineering)
**Architecture**:
- 512 threads = 8 waves of 64
- Output tile: 128×128 (4×4 grid of 32×32 MFMA tiles)
- Double-buffered LDS with XOR swizzle
- Cooperative loading with 128-bit global loads
- Wave scheduling with `__builtin_amdgcn_s_setprio`

## Tools Installed (Ready to Use)
- **GEAK**: `/home/mike-anderson/dev/geak/` — AMD-AGI kernel optimization agent with Ollama backend
- **Ollama cloud**: 12+ models configured (deepseek-v3.2, kimi-k2.5, qwen3.5:397b, gemma4:31b, etc.)
- **popcorn-cli**: v1.3.6, verified working
- **Iteration script**: `ollama_kernel_iterate.sh` for automated test→benchmark→leaderboard

## Skills Created/Updated (4)
1. `amd-load-inline-hip-kernel` v2.0.0 — load_inline NOT blocked
2. `amd-gfx950-tl-dot-scaled-constraints` v1.0.0 — BLOCK_K>=128 mandatory
3. `multi-model-kernel-optimization` v1.0.0 — team orchestration pattern
4. `popcorn-benchmark-vs-ranked-scoring` v2.0.0 — only GPU compute helps

## Anti-Patterns (DO NOT RETRY)
- AITER_KSPLIT env var (ignored by kernel)
- HIP_FORCE_DEV_KERNARG (hurts aiter)
- Python dispatch optimization (hurts ranked)
- Pre-allocated buffers (hurts ranked)
- Bypassing torch.ops (hurts ranked)
- Fused BF16→FP4 quant in MFMA kernel (10-45x slower — needs parallel reduction)
- gemm_a4w4_asm explicit kernel (22µs vs gemm_a4w4 baseline 13.4µs)
- LDS for small M shapes (sync overhead > benefit)

## Files Changed
All in `/home/mike-anderson/dev/cohezion/luma_speedrun/`:
- `amd-mxfp4-mm/submission_mfma_v1.py` — CORRECT MFMA FP4 kernel (26µs)
- `amd-mxfp4-mm/submission_triton_dotscaled.py` — CORRECT Triton FP4 (23µs)
- `amd-mxfp4-mm/submission_asm_grid_search.py` — tile grid search (22.8µs)
- `amd-mixed-mla/submission_a16w16.py` — BF16 decode (100µs, wrong kernel dispatched)
- `amd-moe-mxfp4/submission_blockscale_g1u1.py` — FP8 blockscale (failed conversion)
- `RUNNER_INVENTORY.md` — complete .co and API inventory
- `SESSION_95_CONTINUATION.md` — this file

## Additional Anti-Pattern: per_1x32_f4_quant_hip
per_1x32_f4_quant_hip(shuffle=True) produces WRONG results — silent failure, no exception.
Its shuffle format is INCOMPATIBLE with gemm_a4w4. CANNOT be used as a drop-in replacement.
