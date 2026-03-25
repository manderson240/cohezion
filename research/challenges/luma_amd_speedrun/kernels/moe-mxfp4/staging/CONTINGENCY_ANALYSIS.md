# MoE Contingency Analysis: Beyond KSPLIT

## Problem Statement

Our entire MoE search tree varies `AITER_KSPLIT` (values 0-6). GPU expert review flagged
that KSPLIT may be dead code on the runner's aiter version. If so, we're exploring a null
space and need alternative optimization axes.

## Evidence from Results

| Experiment | Geomean | Notes |
|-----------|---------|-------|
| baseline (BYPASS=1, KSPLIT=0) | 155.2us | Reference |
| p18-exp2 (adaptive KSPLIT) | 155.0us | **Identical** -- strong evidence KSPLIT is inert |
| p18-exp1 (torch.compile) | 155.0us | Falls back to eager |
| p18-exp3 (expert_mask=bincount) | CRASH | GPU memory fault |
| exp2 (remove AITER_USE_NT) | parse_error | May have crashed or changed output format |

The 155.0us vs 155.2us difference (0.1%) is within noise. This is consistent with KSPLIT
being dead code.

## fused_moe Parameter Analysis

### Parameters Currently Used

| Parameter | Value | Notes |
|-----------|-------|-------|
| `expert_mask` | `None` | Required None -- bincount crashes |
| `activation` | `ActivationType.Silu` | Required for SwiGLU |
| `quant_type` | `QuantType.per_1x32` | MXFP4 block scaling |
| `doweight_stage1` | `False` | **Critical**: True causes 82% element mismatches |
| `w1_scale` / `w2_scale` | shuffled scales | Pre-shuffled e8m0 scales |
| `hidden_pad` / `intermediate_pad` | computed from config | Padding for 256-alignment |

### Parameters NOT Currently Used (from reference.py)

| Parameter | Default | Potential |
|-----------|---------|-----------|
| `a1_scale` | `None` | Activation scale for stage 1 -- could enable pre-quantized activation path |
| `a2_scale` | `None` | Activation scale for stage 2 -- skip intermediate requantization |

### Environment Variables

| Variable | Current | Notes |
|----------|---------|-------|
| `AITER_USE_NT` | "1" | Non-transposed weight layout. Removing caused parse_error |
| `AITER_BYPASS_TUNE_CONFIG` | "1" | Skip tuning DB lookup. Toggled with KSPLIT |
| `AITER_KSPLIT` | varies | **Possibly dead code** |
| `AITER_USE_OPUS_MOE_SORTING` | not set | Token reordering for better coalescing |
| `AITER_JIT_DIR` | not set | Crashed when set (internal error) |

## Contingency Strategies

### Strategy 1: OPUS Token Sorting (Medium Confidence)

Set `AITER_USE_OPUS_MOE_SORTING=1`. This reorders tokens by expert assignment before
the GEMM, improving memory coalescing. Never tested in isolation -- always combined with
KSPLIT changes. Worth testing as a standalone optimization.

**Risk**: Low. It's a sorting optimization, unlikely to crash.
**Expected gain**: 2-5% on E=257 shapes (many experts = more routing scatter).

### Strategy 2: Raw (Unshuffled) Weights (Low Confidence)

Use `w1` / `w2` (raw fp4x2) instead of `w1sh` / `w2sh` (pre-shuffled). Also use
`w1s` / `w2s` (raw e8m0 scales) instead of `w1ssh` / `w2ssh`.

**Risk**: High. The CK kernel expects (16,16) tile-coalesced layout. Raw weights will
either crash or produce wrong results. The `bpreshuffle=True` flag in gemm_a4w4 handles
this for GEMM, but fused_moe may not have an equivalent.

**Verdict**: Not viable unless fused_moe has an internal shuffle path.

### Strategy 3: quant_type Variations (Low Confidence)

Available QuantType values (from aiter):
- `per_1x32` (current) -- block scaling with block_size=32
- `per_128` -- per-128 scaling
- `per_token` -- per-token scaling
- Others unknown without runner introspection

**Risk**: Medium. Wrong quant_type will produce incorrect results (fail correctness).
The weights are quantized as per_1x32 MXFP4, so changing quant_type would require
re-quantization, which we can't do (weights are pre-computed).

**Verdict**: Not viable -- quant_type must match the quantization scheme used for weights.

### Strategy 4: Direct CK Kernel Bypass (High Potential, High Risk)

Call the underlying CK kernel directly via:
```python
from aiter.jit_build import module_moe_ck2stages_fp4x2_fp4x2_preshuffle_on_b16_silu_per_1x32_mulWeightStage2_
fn = module_moe_ck2stages_fp4x2_fp4x2_preshuffle_on_b16_silu_per_1x32_mulWeightStage2_.ck_moe_stage1
```

This bypasses fused_moe's Python overhead (token sorting, expert masking, padding
computation). If fused_moe does significant Python work per call, this could save 5-15us.

**Risk**: High. We don't know the exact signature. Need a recon probe first.
**Expected gain**: 5-15us if Python overhead is significant.

### Strategy 5: Activation Pre-quantization (Medium Potential)

Pass `a1_scale` and `a2_scale` to skip dynamic quantization inside the kernel.
Pre-quantize activations using `aiter.ops.triton.quant.dynamic_mxfp4_quant` and pass
the scales. This could eliminate redundant quantization if fused_moe re-quantizes
internally.

**Risk**: Medium. If fused_moe ignores these when `quant_type=per_1x32`, no effect.
**Expected gain**: 2-8us if activation quantization is a bottleneck.

### Strategy 6: BYPASS_TUNE_CONFIG=0 (Auto-tune) (Medium Confidence)

Remove `AITER_BYPASS_TUNE_CONFIG` entirely. Let aiter use its internal tuning database
to select optimal kernel parameters. The baseline used this (155.2us). If KSPLIT is
dead code, then BYPASS=1 with any KSPLIT is equivalent to BYPASS=0.

**Risk**: Low. This is the reference behavior.
**Expected gain**: 0% if KSPLIT is dead (already equivalent). Could be worse if tune
DB has stale entries.

### Strategy 7: Shared Expert Specialization (Medium Potential)

The shared expert (always weight=1.0) processes ALL tokens. Currently mixed with routed
experts in fused_moe. Could we:
1. Separate shared expert into a dense GEMM call (aiter.gemm_a4w4)
2. Run routed experts via fused_moe with top_k=8 (no shared)
3. Add results

**Risk**: Medium. Requires modifying topk_ids/weights, may break alignment.
**Expected gain**: 5-10% if shared expert is bottlenecking routing logic.

## Recommended Priority

1. **KSPLIT Probe** (validate dead-code hypothesis)
2. **OPUS Sorting** (low risk, moderate potential)
3. **Activation Pre-quantization** (medium risk, medium potential)
4. **Shared Expert Specialization** (medium risk, medium potential)
5. **Direct CK Bypass** (high risk, needs recon first)
6. **Auto-tune (BYPASS=0)** (low risk, likely no gain)

## Key Insight

The leader at 145us is ~7% faster. That's ~10us over 7 benchmark shapes (geomean).
This is achievable through:
- OPUS sorting: ~3-5us on high-expert shapes
- Activation pre-quant: ~2-5us
- Shared expert split: ~3-5us
Any ONE of these hitting could close the gap.
