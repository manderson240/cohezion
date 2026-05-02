# HipKittens MoE Kernel for AMD MI355X

**Target:** <110µs latency for MoE forward pass (Rank 1: 109.8µs)

## Overview

This kernel implements a highly optimized 2-stage fused MoE pipeline using HipKittens for AMD MI355X (gfx950 / CDNA4).

### Key Optimizations

1. **2-Stage Inter-Kernel Fusion**
   - Gate+Up projection → SiLU activation → Down projection in single kernel launch
   - Eliminates intermediate activation writeback to HBM
   - Register-resident intermediate activations

2. **MXFP4 Dequantization**
   - On-the-fly dequantization of 4-bit packed weights
   - E8M0 scale application per 32-element block
   - Custom device function for efficient MXFP4->float conversion

3. **CDNA4 Architecture Optimizations**
   - 256 threads per block (4 warps)
   - Launch bounds: `__launch_bounds__(256, 2)` for 2 blocks per CU
   - Warp-level parallelism: 2x2 warp arrangement (64 tokens × 128 dims)
   - MFMA-friendly tile sizes (32×32)

4. **Memory Access Patterns**
   - Double-buffered shared memory for input activations
   - Coalesced global memory access for weights
   - Atomic accumulation for multi-expert output

## Kernel Specifications

### Template Parameters
- `HIDDEN_SIZE = 7168` (DeepSeek-R1 configuration)
- `INTERMEDIATE_SIZE = 256` (per expert)
- `BLOCK_M = 64` (tokens per tile)
- `BLOCK_N = 128` (dimensions per tile)
- `BLOCK_K = 64` (K-dimension tiles)

### Thread Organization
- Grid: `[num_tiles]` blocks
- Block: 256 threads (4 warps)
- Warp arrangement: 2×2 (warp_m × warp_n)
- Each warp handles 32 tokens × 32 dimensions

### Shared Memory Layout
- Input buffer: 2×(64×64) bf16 elements (double buffered)
- Stage 1 output: 512 floats (256 gate + 256 up)
- Activated buffer: 256 floats (after SiLU×Up)

## File Structure

```
hipkittens_moe/
├── submission_compact.py    # Main submission file (Popcorn CLI)
├── hipkittens_moe_kernel.hpp  # Full kernel header
├── submission.py            # Extended Python wrapper
└── README.md               # This file
```

## Usage

### Compile Kernel
```bash
cd hipkittens_moe
python3 submission_compact.py --compile --arch gfx950
```

### Run Benchmark
```bash
python3 submission_compact.py --benchmark
```

### Popcorn Submission
```bash
# Kernel is embedded in submission_compact.py
python3 submission_compact.py --submit
```

## Expected Performance

| Metric | Value |
|--------|-------|
| Target Latency | <110µs |
| Rank 1 Target | 109.8µs |
| Current aiter.fused_moe | ~154µs |
| **Gap to Close** | **~44µs (28%)** |

### Speedup Sources

1. **Inter-stage fusion**: ~20-30µs saved by eliminating intermediate writeback
2. **Register-resident tiles**: ~5-10µs from LDS vs HBM access
3. **Optimized MXFP4 paths**: ~5-10µs from efficient dequantization
4. **Kernel launch overhead**: ~10-15µs saved from single launch vs 2 launches

## Technical Details

### MXFP4 Format

MXFP4 uses 4-bit floating-point with:
- 1 sign bit
- 2 exponent bits
- 1 mantissa bit

Values: `{0, ±0.5, ±1.0, ±1.5, ±2.0, ±4.0}`

Scale: E8M0 (exponent-only 8-bit float)

### SiLU Activation

```cpp
float silu(float x) {
    return x / (1.0f + expf(-x));
}
```

Fused with element-wise multiply: `silu(gate) * up`

### Weight Layout

Gate+Up weights: `[num_experts, 2*INTERMEDIATE_SIZE, HIDDEN_SIZE/2]` (packed MXFP4)
- 4 bits per weight element
- 2 weights per byte
- Scale per 32 output elements

Down weights: `[num_experts, HIDDEN_SIZE, INTERMEDIATE_SIZE/2]` (packed MXFP4)

## Dependencies

- ROCm 6.3+
- HipKittens (installed at `/opt/rocm/include/hipkittens`)
- MI355X GPU (gfx950)
- Python 3.8+

## References

- HipKittens Paper: arxiv.org/abs/2511.08083
- DeepSeek MoE: https://huggingface.co/deepseek-ai/DeepSeek-R1-0528
- AMD CDNA4 Architecture Guide
- CK-Tile: github.com/ROCm/composable_kernel

## License

MIT License - See SPDX-License-Identifier in source files
