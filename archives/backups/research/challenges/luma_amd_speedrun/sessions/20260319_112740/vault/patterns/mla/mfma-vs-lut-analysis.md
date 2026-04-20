# MLA Pattern: MFMA vs LUT Analysis

## Date: 2026-03-19
## Session: 20260319_112740

## Current State
- Best MLA: 72µs (FP4 LUT approach)
- Leader MLA: 4.3µs
- Gap: 16.7×

## Key Architectural Insight

### Why LUT Approach is Slow

The FP4 LUT dequantization approach (`mla_top10.hip`) processes each Q×K element individually:

```cpp
float d_fp4(unsigned char v, unsigned char s) {
    return FP4_LUT[v] * __uint_as_float((unsigned int)s << 23);
}

// Called 36,864 times per (batch, head, kv_step):
// - 576 Q elements × 64 V elements = 36,864 LUT lookups
// - Plus: 512/64 = 8 wave-level V accumulation passes
// - Plus: bf16→float→bf16 conversions throughout
```

### CDNA 3 Native: MFMA

CDNA 3 (MI355X) provides `__builtin_amdgcn_mfma_scale_f32_16x16x128_f8f6f4`:

```cpp
// Input: Two int8_v (32 bytes = 8×FP8 elements)
// Accumulator: float4_v (4×FP32)
// Fused: FP8 dequant + dot product in ONE instruction

float4_v result = __builtin_amdgcn_mfma_scale_f32_16x16x128_f8f6f4(
    q_reg, k_reg, acc,     // registers
    q_scale, k_scale,      // E8M0 scales (fused!)
    0, 0, 0, 0             // flags
);
```

**Per block: 1 instruction = 16×16×128 = 256 FMA ops with fused scale**

### Performance Comparison

| Operation | LUT Approach | MFMA Approach |
|-----------|-------------|--------------|
| Q×K ops | 36,864 | 36,864 (same) |
| Instructions | 36,864 LUT + 8 wave passes | 18 MFMA + 16 MFMA V |
| Scale ops | Per-element (36,864) | Fused per block (34) |
| bf16 conversions | Every step | None (FP8 native) |

### Expected Speedup: 3-5×

The MFMA approach should be 3-5× faster because:
1. **Fused scale application** — no per-element scale multiplication
2. **No LUT pressure** — constant LUT avoided
3. **FP8 native** — no bf16↔float conversions
4. **Wave-level SIMD** — MFMA is SIMD-native on CDNA 3

## What Leader Likely Does

The 4.3µs leaderboard time suggests:
1. **MFMA-based score computation** — use native MFMA for Q×K^T
2. **Persistent kernel mode** — KV stays in L2 cache
3. **FP8 KV cache throughout** — no FP4 dequantization needed
4. **Minimal wave-level reductions** — exploit MFMA accumulator directly

## Action Items

- [x] Generate `mla_mfma_pure.py` — pure MFMA approach
- [x] Generate `mla_aiter_max_tuned.py` — AITER baseline comparison
- [ ] Submit to MI355X and measure actual speedup
- [ ] If MFMA works, iterate on V accumulation strategy
