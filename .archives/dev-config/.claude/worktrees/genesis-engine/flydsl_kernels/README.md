# FlyDSL GPU Kernel Test

This directory contains FlyDSL kernel implementations for AMD MI355X (gfx950).

## What is FlyDSL?

FlyDSL is a Python DSL and MLIR stack for authoring high-performance GPU kernels with explicit layouts and tiling. It serves as the Python front-end for the Fly dialect, an end-to-end MLIR-native compiler stack.

**Key Features:**
- `@kernel` decorator for GPU kernel definition
- JIT compilation with disk caching
- Layout algebra (Shape, Stride, Layout, Coord)
- Hierarchical control across block, warp, thread, instruction scopes
- MFMA instruction support for CDNA4 (MI355X)
- MXFP4 quantization support

## Files

| File | Description |
|------|-------------|
| `trivial_kernel.py` | Basic vector add and MFMA test kernels |
| `fused_moe_kernel.py` | 2-stage fused MoE implementation |
| `submission.py` | Popcorn CLI submission format |
| `README.md` | This file |

## Kernel Implementations

### 1. Trivial Vector Add Kernel

```python
@flyc.kernel
def vector_add_kernel(A: fx.Tensor, B: fx.Tensor, C: fx.Tensor, n: fx.Constexpr[int]):
    gid = fx.block_idx.x * 256 + fx.thread_idx.x
    if gid < n:
        C[gid] = A[gid] + B[gid]
```

### 2. MFMA Test Kernel

Uses `mfma_f32_32x32x64_f8f6f4` for matrix multiplication on MI355X.

### 3. Fused MoE Kernel

Two-stage fused kernel:
1. **Stage 1**: Gate+Up projection with MFMA
2. **Bridge**: SiLU(Gate) * Up in registers
3. **Stage 2**: Down projection with atomic accumulation

**Optimizations:**
- Bridge LDS eliminates intermediate HBM writes
- MXFP4 weights reduce memory bandwidth
- Expert parallelism via 3D grid
- Atomic accumulation for top-k fusion

## Compilation

FlyDSL compiles kernels using JIT with MLIR backend:

```python
compiled = flyc.compile(
    kernel_func,
    grid_dim=(128, 8),
    block_dim=(256,),
    arch="gfx950",
    features=["mxfp4", "mfma_f32_32x32x64"]
)
```

## Requirements

- ROCm 6.x+
- FlyDSL v0.0.1.dev (pre-installed on MI355X runner)
- Python 3.10+

## Testing

On the MI355X runner:

```bash
python3 trivial_kernel.py    # Test basic kernel
python3 fused_moe_kernel.py  # Test fused MoE
python3 submission.py        # Popcorn CLI submission
```

## Target Performance

For DeepSeek-R1 MoE (E=256, TopK=8, H=7168, I=18432):
- Target: <115µs
- Strategy: Bridge LDS + MXFP4 + MFMA

## References

- FlyDSL GitHub: https://github.com/ROCm/FlyDSL
- FlyDSL Blog: https://rocm.blogs.amd.com/artificial-intelligence/kimi-k2.5-optimize/
- MLIR: https://mlir.llvm.org/
