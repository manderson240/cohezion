---
name: popcorn-runner-api-inventory
description: |
  Complete API inventory for AMD MI355X Popcorn runner (Luma AMD Speedrun 2026).
  Use when: (1) looking for untested aiter APIs, (2) planning kernel optimization
  strategies, (3) checking which .co kernel files exist on runner, (4) checking
  tuning CSV availability. Verified via live runner probe April 4, 2026.
author: Claude Code (Session 90)
version: 1.0.0
---

# Popcorn Runner API Inventory (MI355X, April 2026)

## Runner Environment
- torch: 2.10.0+rocm7.1
- hip: 7.1.25424
- aiter: /home/runner/aiter/aiter/__init__.py
- GPU: AMD Instinct MI355X (gfx950)
- 256 CUs, wave64

## GEMM APIs (5 variants)

| API | Signature | Status |
|-----|-----------|--------|
| `aiter.gemm_a4w4` | `(*args, **kwargs)` — main API with auto kernel selection | WORKING (13.4µs baseline) |
| `aiter.gemm_a4w4_asm` | `(A, B, A_scale, B_scale, out, kernelName, bias=None, alpha=1.0, beta=0.0, bpreshuffle=True, log2_k_split=None)` | UNTESTED with explicit params |
| `aiter.gemm_a4w4_blockscale` | `(XQ, WQ, x_scale, w_scale, Out, splitK=0)` — needs pre-alloc Out | "This GEMM is not supported" for competition shapes |
| `aiter.deepgemm_ck` | `(...)` — CK DeepGEMM | UNTESTED |
| `aiter.per_1x32_f4_quant_hip` | HIP-native FP4 quant | **BROKEN**: produces wrong values with gemm_a4w4 (both shuffle=True and shuffle=False). Silent failure — no exception raised. See skill: aiter-hip-quant-gemm-incompatibility |

## MLA APIs (7 variants)

| API | Status |
|-----|--------|
| `aiter.mla_decode_stage1_asm_fwd` | WORKING (current, top-level NOT in aiter.mla) |
| `aiter.mla_reduce_v1` | WORKING (current) |
| `aiter.mla_prefill_asm_fwd` | UNTESTED |
| `aiter.mla_prefill_ps_asm_fwd` | UNTESTED (persistent prefill) |
| `aiter.pa_ps_fwd_asm` | UNTESTED (persistent paged attention) |
| `aiter.fmha_v3_varlen_fwd` | DEAD: "CK only supports head dimension at most 256" (MLA needs 576) |
| `mla.mla_decode_fwd` | Wrapper for stage1+reduce (1 dispatch vs 2) |

**CRITICAL:** `mla_decode_stage1_asm_fwd` is at `aiter.` top-level, NOT `aiter.mla.`

## MoE APIs (6 variants)

| API | Status |
|-----|--------|
| `aiter.fused_moe.fused_moe` | WORKING (154µs baseline) |
| `aiter.fmoe` | UNTESTED (direct fmoe) |
| `aiter.fmoe_fp8_blockscale_g1u1` | UNTESTED |
| `aiter.fmoe_g1u1_a16` | Needs pre-sorted inputs (sorted_token_ids, sorted_weights, sorted_expert_ids, num_valid_ids) |
| `aiter.ck_moe_stage1` / `aiter.ck_moe_stage2` | UNTESTED (direct CK dispatch) |
| `aiter.fused_moe.asm_moe` | DEAD: ImportError (doesn't exist on runner) |

## .co Kernel Files

| Directory | Count | Example |
|-----------|-------|---------|
| `/home/runner/aiter/hsa/gfx950/f4gemm/` | 35 | `f4gemm_bf16_per1x32Fp4_BpreShuffle_128x128.co` |
| `/home/runner/aiter/hsa/gfx950/mla/` | 27 | `mla_a8w8_qh16_qseqlen1_gqaratio16_ps.co` |
| `/home/runner/aiter/hsa/gfx950/fmoe_2stages/` | 182 | `fmoe_stage1_bf16_pertokenFp8_blockscale_g1u1_128x128_pf2.co` |
| `/home/runner/aiter/hsa/gfx950/` | 4 | `f8_block_scale_mi350_x128.co` |

## Tuning CSVs

| File | Rows | Header |
|------|------|--------|
| `a4w4_blockscale_tuned_gemm.csv` | 1471 | cu_num,M,N,K,kernelId,splitK,us,kernelName,tflops,bw,errRatio |
| `a4w4_blockscale_untuned_gemm.csv` | 197 | M,N,K |
| `a8w8_blockscale_bpreshuffle_tuned_gemm.csv` | 121 | cu_num,M,N,K,libtype,kernelId,splitK,us... |
| `a8w8_bpreshuffle_tuned_gemm.csv` | 734 | cu_num,M,N,K,q_dtype_w,libtype... |
| `tuned_fmoe.csv` + `dsv3_fp4_tuned_fmoe.csv` | merged | MoE shape-specific tuning |

## Confirmed Dead Ends

| Approach | Error | Status |
|----------|-------|--------|
| `asm_moe()` | ImportError: doesn't exist | DEAD |
| `hipModuleLaunchKernel` (ctypes OR load_inline) | HTTP 500 "work on another stream" | DEAD |
| `fmha_v3_varlen_fwd` for MLA | "CK only supports head dimension at most 256" | DEAD |
| `gemm_a4w4_blockscale` for competition shapes | "This GEMM is not supported" | DEAD for these shapes |
| Per-scale-group LDS tiling | 15× slower (sync overhead) | DEAD |
| Native FP4 MFMA (blog output mapping) | Wrong results (register layout unknown) | BLOCKED |
| BF16 MFMA kernel | Correct but 24.7µs (slower than 13.4µs naive) | NOT COMPETITIVE |
