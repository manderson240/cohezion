---
title: "MoE Custom HIP Kernel Design for MI355X"
date: 2026-03-14
status: in-progress
tags: [gpu-optimization, moe, hip-kernel, deepseek-r1, mxfp4, amd-mi355x, kernel-design]
aspect: thinker
---

# MoE Custom HIP Kernel - Research Summary

## Date: 2026-03-14
## Team: MoE Kernel Architect (Lead)

## Current Status
- **Rank**: 13/58 on amd-moe-mxfp4 leaderboard
- **Score**: 1.55e-04 (~155 µs)
- **Target**: ~115 µs (40 µs improvement for Top 10)

## Architecture Analysis

### DeepSeek-R1 MoE Configuration
- Hidden dimension: 7168
- Expert intermediate: 2048 (EP-on) or 256 (EP-off)
- Routed experts: 256 (EP-off) or 32 (EP-on, 8-way split)
- Shared experts: 1 (always selected)
- Top-k: 8 routed + 1 shared = 9 total

### Current Bottleneck
The aiter.fused_moe path:
```
Python → fused_moe → C++ → ASM
         ↓
    ~10 Python function calls
    lru_cache lookups
    env var re-reads
    3-stage pipeline overhead
```

### Custom Kernel Strategy
Bypass Python overhead with direct HIP:
```
Python → Custom HIP Kernel → ASM
         ↓
    Single kernel launch
    Fused Stage 1 + Stage 2
    No intermediate buffers
```

## MXFP4 Format Details

### FP4 (E2M1) Values
```
Index | Binary | Value
------|--------|------
  0   |  000   | 0.0
  1   |  001   | 0.5
  2   |  010   | 1.0
  3   |  011   | 1.5
  4   |  100   | 2.0
  5   |  101   | 3.0
  6   |  110   | 4.0
  7   |  111   | 6.0
```

### E8M0 Scale Format
- Exponent-only 8-bit
- scale = 2^(e - 127)
- One scale per 32 elements

### Memory Layout
- FP4x2: 2 values per byte (low/high nibble)
- Block size: 32 elements
- Padding: 256-alignment for CK kernel

## Kernel Design

### Tiling Strategy
```
TILE_M = 64      (tokens per block)
TILE_N = 128     (output features per block)
TILE_K = 128     (input features per iteration)
WARP_SIZE = 64   (AMD wavefront)
```

### Stage 1: Gate-Up + SwiGLU
```
For each token:
  For each expert in top_k:
    gate = hidden @ W_gate.T
    up   = hidden @ W_up.T
    intermediate = SiLU(gate) * up
```

### Stage 2: Down + Accumulate
```
For each token:
  output = 0
  For each expert in top_k:
    expert_out = intermediate @ W_down.T
    output += topk_weight * expert_out
```

## Files Created

### Source Code
- `src/custom_moe.hip` - Main kernel implementation
- `src/moe_kernels.h` - Header with device functions
- `src/moe_custom.py` - Python ctypes wrapper

### Build System
- `build/Makefile` - hipcc compilation

### Testing
- `tests/test_correctness.py` - Correctness validation
- `tests/submission.py` - Leaderboard submission wrapper

### Documentation
- `docs/interface_spec.md` - Kernel interface specification

## Key Optimizations

1. **Fused Kernel**: Combine Stage 1 + Stage 2 into single launch
2. **Shared Memory**: Use shared mem for intermediate results
3. **MFMA Instructions**: Use AMD matrix multiply instructions
4. **Work Distribution**: Balance tokens across CUs
5. **Memory Coalescing**: Ensure coalesced global memory access

## Next Steps

1. Compile kernel with hipcc
2. Test correctness against reference
3. Profile with rocprof
4. Iterate on tile sizes
5. Submit to leaderboard

## References

- AITER fused_moe: `/kernels/moe-mxfp4/reference.py`
- Task specification: `/kernels/moe-mxfp4/README.md`
- Custom dispatch: `/kernels/moe-mxfp4/submission_custom_dispatch.py`

## Related
- [[2026-03-14-moe-optimization-state|MoE optimization state]] — current rank and bottleneck analysis
- [[2026-03-14-doweight-cktile-incompatibility|doweight bug]] — critical API constraint
- [[machine-learning-optimization]] — quantization and inference optimization