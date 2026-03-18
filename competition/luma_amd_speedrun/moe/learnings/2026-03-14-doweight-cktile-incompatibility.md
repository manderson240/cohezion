---
title: "doweight_stage1=True Broken on CK and cktile Paths"
date: 2026-03-14
status: complete
tags: [gpu-optimization, moe, aiter, cktile, amd-mi355x, bug-discovery]
aspect: thinker
severity: critical
---

# doweight_stage1=True is COMPLETELY BROKEN (Both Paths)

## Discovery (Phase 12, March 14 2026)

**CRITICAL**: `doweight_stage1=True` is broken on BOTH the cktile AND CK paths.
**NEVER use doweight_stage1=True for MXFP4 MoE.**

### Failure Mode 1: cktile path (KSPLIT>0) — GPU Memory Fault
- `Memory access fault by GPU node-2 on address (nil). Reason: Unknown.`
- Kernel crashes immediately on first test shape
- Root cause: cktile kernel dereferences topk_weight as null pointer

### Failure Mode 2: CK path (KSPLIT=0) — Wrong Results
- Builds `module_moe_ck2stages_fp4x2_fp4x2_preshuffle_on_b16_silu_per_1x32_mulWeightStage1_`
- Produces 82% element mismatches (3,010,657 / ~3,670,016 elements wrong)
- Errors are LARGE (not just tolerance violations): e.g., -0.447 vs -0.547
- Discovered on E=33, bs=512, d_expert=512 and d_expert=2048 benchmark shapes
- The mulWeightStage1 CK kernel has a correctness bug for MXFP4 quant

### Complete Safety Table
| Path | KSPLIT | doweight_stage1 | Result |
|------|--------|-----------------|--------|
| CK (CSV-tuned) | 0 | True | **WRONG RESULTS (82% mismatch)** |
| CK (CSV-tuned) | 0 | False | SAFE |
| cktile | >0 | False | SAFE |
| cktile | >0 | True | **GPU MEMORY FAULT** |

### Fix
**Always use `doweight_stage1=False`.** No conditional logic needed — it's broken everywhere.

### Benchmark Data (ALL 7 shapes, Phase 12j — doweight=False)
| Shape | Our Time | Reference | Improvement |
|-------|----------|-----------|-------------|
| E=257, bs=16, d=256 | 90.8 µs | 152.7 µs | 40% faster |
| E=257, bs=128, d=256 | 171 µs | 239.0 µs | 28% faster |
| E=257, bs=512, d=256 | 285 µs | 336.5 µs | 15% faster |
| E=33, bs=16, d=512 | 60.1 µs | 106.2 µs | 43% faster |
| E=33, bs=128, d=512 | 108 µs | 141.1 µs | 23% faster |
| E=33, bs=512, d=512 | 214 µs | — | NEW (was broken) |
| E=33, bs=512, d=2048 | 353 µs | — | NEW (was broken) |
| **Geomean** | **~155 µs** | | Rank 13/58 → submitted |

### 1-stage Path: BLOCKED by fc2_smooth_scale
- `fused_moe_1stage` internally calls `fmoe_int8_g1u0`
- `fmoe_int8_g1u0` requires `fc2_smooth_scale` as a Tensor (SmoothQuant)
- `fc2_smooth_scale` is NOT a parameter of `fused_moe_1stage()` — error: "unexpected keyword argument"
- The scale is needed internally but not exposed via API
- **1-stage path is dead** unless we monkey-patch or call fmoe_int8_g1u0 directly

### get_2stage_cfgs CSV Lookup (from probe source)
- CSV index columns: `cu_num, token, model_dim, inter_dim, expert, topk, act_type, dtype, q_dtype_a, q_dtype_w, q_type, use_g1u1, doweight_stage1`
- `doweight_stage1` is part of the index key — different CSV entries for True vs False
- Competition shapes have NO CSV matches → always falls back to "using 2stage default"
- This means CSV tuning provides zero benefit over cktile for our shapes

### Available Functions (from module probe)
- `asm_stage1` — ASM-based stage 1, calls `moe_stage1_g1u1`. **bf16 only, NOT MXFP4 compatible**
- `fused_dynamic_mxfp4_quant_moe_sort` — fused quant+sort kernel
- `cktile_moe_gemm1`, `cktile_moe_gemm2` — direct cktile kernels (block_m, split_k tunable)
- `ck_moe_stage1`, `ck_moe_stage2` — CK MXFP4 kernels (block_m, splitk, non_temporal_load)
- `fused_moe_` is a JIT wrapper via `torch.ops.aiter` (no Python source)

### asm_stage1: Dead End for MXFP4 (Phase 13, March 14 2026)
- Full signature probed: `asm_stage1(input, w1, w2, sorted_ids, sorted_expert_ids, num_valid_ids, out, topk, block_m, kernelName='', ksplit=0, activation=Silu, quant_type=No, a1_scale=None, w1_scale=None, sorted_weights=None)`
- Internally calls `aiter.moe_stage1_g1u1` (ASM kernel)
- Source comment: `dtype = dtypes.bf16  # out.dtype, asm only support bf16`
- **Cannot be used for MXFP4 MoE** — would require dequantizing weights first (slower)

### fused_moe_1stage: fc2_smooth_scale Confirmed Internal-Only
- Probed source: `fc2_smooth_scale=None` at lines 121 and 140 (hardcoded internally)
- NOT exposed as API parameter — `fused_moe_1stage()` signature confirmed, no fc2_smooth_scale kwarg
- Passing it externally: `TypeError: unexpected keyword argument 'fc2_smooth_scale'`
- **1-stage path is permanently dead for MXFP4**

### KSPLIT Routing Optimization (Phase 13 Comparison)

| Variant | E=257 bs=16 | E=257 bs=128 | E=257 bs=512 | E=33 bs=16 | E=33 bs=128 | E=33 bs=512 d=512 | E=33 bs=512 d=2048 | Geomean |
|---------|-------------|-------------|-------------|-----------|------------|-----------------|-------------------|---------|
| Phase 12j (best) | 90.8 | 172 | 285 | 60.1 | **108** | 214 | 353 | **~155.6** |
| KSPLIT-tuned (4-tier) | 90.0 | 168 | 275 | 60.7 | 125 | 210 | 343 | ~156.4 |
| All-cktile | 91.0 | 173 | 284 | 60.6 | 129 | 214 | 355 | ~159.5 |

**Key findings:**
- KSPLIT=1 for est_m=31 (E=33 bs=128) is 16% SLOWER than KSPLIT=2 (125 vs 108 µs)
- CK path and cktile KSPLIT=1 are identical for dense shapes (~214 µs, ~355 µs)
- No CSV-tuned entries exist — both paths use "2stage default" and perform equally
- block_m is auto-selected optimally: 32 for sparse, 64 for moderate, 128 for dense
- Phase 12j routing remains the best overall variant

## Related
- [[2026-03-14-moe-optimization-state|MoE optimization state]] — full optimization context and exhausted paths
- [[machine-learning-optimization]] — quantization and kernel optimization context
