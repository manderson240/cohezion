# Session 90 — Comprehensive Findings (April 3, 2026)

## Summary

14+ submission attempts. 7 dead ends confirmed. 1 key probe discovery (runner API map).
No leaderboard improvement achieved. Scores remain at 13.4µs / 154µs / 69.7µs.

## Confirmed Dead Ends

| # | Approach | Error | Status |
|---|----------|-------|--------|
| 1 | `asm_moe()` API | ImportError: doesn't exist on runner | DEAD |
| 2 | `hipModuleLaunchKernel` from load_inline C++ | HTTP 500 "work on another stream" | DEAD |
| 3 | `hipModuleLaunchKernel` from ctypes | HTTP 500 "work on another stream" | DEAD (prior session) |
| 4 | Native FP4 MFMA `__builtin_amdgcn_mfma_scale_f32_32x32x64_f8f6f4` | Compiles, wrong results (register layout) | BLOCKED |
| 5 | BF16 MFMA `__builtin_amdgcn_mfma_f32_16x16x16bf16_1k` | Compiles, wrong results (register layout) | BLOCKED |
| 6 | Per-scale-group LDS tiling (16x16 blocks) | 15x slower (sync overhead) | DEAD |
| 7 | `fmha_v3_varlen_fwd` for MLA | "CK only supports head dimension at most 256" (MLA needs 576) | DEAD |
| 8 | `gemm_a4w4_blockscale` for competition shapes | "This GEMM is not supported" (shapes not in tuning CSV) | DEAD for these shapes |

## Confirmed Working

| # | Finding | Detail |
|---|---------|--------|
| 1 | `load_inline` with `<<<grid, block>>>` dispatch | Custom HIP kernels work. Do NOT use explicit stream. |
| 2 | `at::BFloat16` is NOT compatible with `__hip_bfloat16` | Use `(__hip_bfloat16)` cast, NOT `__float2bfloat16` |
| 3 | `ext_vector_type(32)` and `ext_vector_type(16)` compile on gfx950 | |
| 4 | Both MFMA builtins compile on gfx950 | FP4 and BF16 variants exist and run |
| 5 | `mla_decode_stage1_asm_fwd` is at `aiter.` top-level, NOT `aiter.mla.` | |
| 6 | `__syncthreads()` with early thread exit = UB | Guard writes with `bool valid`, don't return early |

## Runner API Discovery (Probe v2)

### GEMM APIs Available
- `aiter.gemm_a4w4(*args, **kwargs)` — main API, uses .co ASM kernels
- `aiter.gemm_a4w4_asm(A, B, A_scale, B_scale, out, kernelName, ...)` — direct ASM with log2_k_split
- `aiter.gemm_a4w4_blockscale(XQ, WQ, x_scale, w_scale, Out, splitK=0)` — tuned CK, needs Out pre-alloc
- `aiter.deepgemm_ck(...)` — CK DeepGEMM (untested, may need different input format)
- `aiter.per_1x32_f4_quant_hip(...)` — HIP-native FP4 quant (might be faster than Triton)

### MLA APIs Available
- `aiter.mla_decode_stage1_asm_fwd(...)` — stage 1 ASM (current)
- `aiter.mla_reduce_v1(...)` — reduce (current)
- `aiter.mla_prefill_asm_fwd(...)` — prefill variant
- `aiter.mla_prefill_ps_asm_fwd(...)` — persistent prefill
- `aiter.pa_ps_fwd_asm(...)` — persistent paged attention
- `aiter.fmha_v3_varlen_fwd(...)` — FlashMHA v3 (max head_dim=256, DEAD for MLA 576)

### MoE APIs Available
- `aiter.fused_moe.fused_moe(...)` — main API (current)
- `aiter.fmoe(...)` — direct fmoe variant
- `aiter.fmoe_fp8_blockscale_g1u1(...)` — FP8 blockscale variant
- `aiter.fmoe_g1u1(...)` — g1u1 variant (known NaN for 32-expert, may work for 257-expert)
- `aiter.fmoe_g1u1_a16(...)` — a16 variant of g1u1
- `aiter.ck_moe_stage1(...)` / `aiter.ck_moe_stage2(...)` — direct CK dispatch

### Tuning CSVs on Runner
- `a4w4_blockscale_tuned_gemm.csv` — 1471 rows, shape-specific kernel selection
- `a8w8_blockscale_bpreshuffle_tuned_gemm.csv` — 121 rows
- `a8w8_bpreshuffle_tuned_gemm.csv` — 734 rows

### .co Kernel Files
- GEMM: 35 files at `/home/runner/aiter/hsa/gfx950/f4gemm/`
- MLA: 27 files at `/home/runner/aiter/hsa/gfx950/mla/`
- MoE: 182 files at `/home/runner/aiter/hsa/gfx950/fmoe_2stages/`

## Untested Paths (For Pi Agent / Next Session)

1. **`gemm_a4w4_asm` with explicit kernelName and log2_k_split**
   - Can select specific .co kernel by name
   - `log2_k_split` might improve tall-skinny shapes

2. **`per_1x32_f4_quant_hip`** — HIP-native quant might be faster than Triton

3. **`fmoe_fp8_blockscale_g1u1` / `fmoe_g1u1_a16`** — untested MoE variants

4. **`ck_moe_stage1` / `ck_moe_stage2`** — direct CK MoE dispatch

5. **`pa_ps_fwd_asm`** — persistent paged attention (different from MLA decode)

6. **MFMA register layout** — needs gfx950 ISA manual or local GPU testing

## Files Created This Session

| File | Status |
|------|--------|
| `submission_mfma_v5.py` | GEMM FP4 MFMA — compiles, wrong results |
| `submission_bf16mfma.py` | GEMM BF16 MFMA — compiles, wrong results |
| `submission_dequant_mfma.py` | GEMM LDS-tiled — correct but 15x slower |
| `submission_blockscale_v2.py` | GEMM blockscale — shapes "not supported" |
| `submission_probe.py` | Runner environment probe — SUCCESS |
| `submission_co_test.py` | MLA .co dispatch — stream blocked |
| `submission_fmhav3.py` | MLA fmha_v3 — head_dim 256 limit |
| `submission_asm_combined.py` | MoE asm_moe — ImportError |
| `FINDINGS_SESSION_90.md` | This document |
