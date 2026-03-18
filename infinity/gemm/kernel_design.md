---
title: "GEMM Kernel Design: Fused MXFP4 Quant + GEMM for MI355X"
date: 2026-03-14
status: in-progress
tags: [gpu-optimization, gemm, mxfp4, hip-kernel, amd-mi355x, kernel-design]
aspect: thinker
---

# GEMM Kernel Design - Fused MXFP4 Quant + GEMM

## Mission
Design and implement a custom HIP kernel to bypass Python API limitations and achieve ~10µs performance for MXFP4 GEMM on MI355X.

## Current State Analysis

### Performance Gap
- **Current**: 20.6 µs (Rank 74/92)
- **Target**: 10.7 µs (Top 20)
- **Gap**: ~10 µs to eliminate

### Root Cause
Current implementation uses two separate operations:
1. `dynamic_mxfp4_quant` (~10 µs) - Triton JIT quantization
2. `gemm_a4w4` (~10 µs) - ASM GEMM kernel

**Total**: ~20 µs with Python dispatch overhead

### Solution: Kernel Fusion
Fuse quantization + GEMM into single kernel to:
1. Eliminate intermediate memory writes
2. Reduce kernel launch overhead
3. Enable better memory coalescing
4. Keep data in shared memory/registers

## Kernel Architecture

### Tile Configuration
```
BLOCK_M = 16    # Rows per block
BLOCK_N = 64    # Columns per block  
BLOCK_K = 128   # K dimension tile
NUM_WARPS = 4   # Warps per block
NUM_THREADS = 256
```

### Memory Layout
- **A**: [M, K] bf16 (row-major)
- **B_q**: [N, K/2] uint8 (packed fp4)
- **B_scale**: [N, K/32] uint8 (e8m0)
- **C**: [M, N] bf16 (row-major)

### Execution Flow
```
1. Load A tile [BLOCK_M, BLOCK_K] to shared memory
2. Quantize A to MXFP4 in-place:
   - Compute amax per 32-element group
   - Calculate E8M0 scale
   - Quantize to FP4, pack 2 values per byte
3. Load B tile from global memory
4. GEMM computation with dequantization:
   - Dequantize A on-the-fly using scales
   - Dequantize B on-the-fly using scales
   - Accumulate in registers
5. Write C tile to global memory
```

## FP4/E8M0 Details

### FP4 (E2M1) Format
- 1 sign bit, 2 exponent bits, 1 mantissa bit
- Values: ±{0, 0.5, 1.0, 1.5, 2.0, 3.0, 4.0, 6.0}

### E8M0 Scale Format
- 8-bit exponent-only (no mantissa)
- Scale = 2^(e8m0 - 127)
- Range: 2^-127 to 2^128

### Quantization Formula
```cpp
amax = max(|x_i|) for group of 32
scale = 2^ceil(log2(amax))
e8m0 = round(log2(scale)) + 127
x_quant = x / scale
fp4_code = encode_fp4(x_quant)
```

## Implementation Files

### Core Kernel
- `src/fused_quant_gemm.hip` - Main kernel implementation
- `src/quant_kernels.h` - Quantization utilities

### Build & Test
- `build/Makefile` - Build configuration
- `tests/test_correctness.py` - Test suite
- `docs/interface_spec.md` - API documentation

### Integration
- `src/submission_wrapper.py` - Competition wrapper
- `README.md` - Quick start guide

## Build Instructions

```bash
cd build
make clean && make
```

Compile flags:
- `hipcc -O3 --offload-arch=gfx950 -fPIC -shared`
- Target: AMD MI355X (gfx950)

## Testing

```bash
cd tests
python test_correctness.py
```

Tests include:
1. Basic shape validation
2. Correctness against reference (rtol=1e-2)
3. Multiple shapes from competition
4. Performance benchmarking

## Performance Targets

| Shape (M,N,K) | Current | Target | Leader |
|---------------|---------|--------|--------|
| 16, 2112, 7168 | 34.4 µs | 15 µs | 9.67 µs |
| 64, 7168, 2048 | 24.4 µs | 12 µs | 9.67 µs |
| 256, 3072, 1536 | 23.3 µs | 12 µs | 9.67 µs |

## Future Optimizations

1. **MFMA Instructions**: Use native MI355X matrix multiply
2. **Async Copy**: Async global-to-shared transfers
3. **Double Buffering**: Overlap compute and memory
4. **XCD Remapping**: Optimize for 8 XCDs
5. **Persistent Kernels**: For batch processing

## References

- AITER reference: `/kernels/mxfp4-mm/reference.py`
- Competition task: `/kernels/mxfp4-mm/task.yml`
- Results: `/results.md`
- Technical analysis: `/technical_analysis.md`

## Status

**Phase**: Implementation Complete  
**Next**: Build and test on MI355X hardware  
**Blockers**: None  

---
Created: 2026-03-14  
Team: Opencode Infinity - GEMM Squad

## Related
- [[2026-03-14-gemm-api-ceiling|GEMM API ceiling]] — why this kernel is needed (API bottleneck analysis)
- [[machine-learning-optimization]] — quantization and inference optimization
