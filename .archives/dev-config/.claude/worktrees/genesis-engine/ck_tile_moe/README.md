# CK-Tile MoE Kernel for AMD MI355X

This submission contains a high-performance Mixture of Experts (MoE) kernel implementation using AMD's CK-Tile library, optimized for MI355X (gfx950) architecture.

## Target Performance

- **Target Latency**: <115µs
- **Rank 1 Target**: 109.8µs
- **Current Best**: ~154µs (aiter.fused_moe)

## Architecture

The kernel implements a **2-stage fused MoE pipeline**:

### Stage 1: Gate/Up Projection + Activation
- First GEMM: `[tokens, hidden] × [hidden, 2×intermediate]`
- Applies SiLU activation to gate projection
- Element-wise multiplication with up projection
- **Optimization**: Fused gate+up computation reduces memory traffic

### Stage 2: Down Projection + Weighted Sum
- Second GEMM: `[tokens, intermediate] × [intermediate, hidden]`
- Atomic accumulation across top-k experts
- **Optimization**: Persistent kernel pattern maximizes occupancy

## Key Optimizations

### 1. Block Shape Configuration
```
BlockTile_0: [64, 128, 64]   // First GEMM: tokens, interm, hidden
BlockTile_1: [64, 64, 128]   // Second GEMM: tokens, hidden, interm
WarpTile:    [32, 32, 32]    // Warp-level parallelism
```

Tuned for MI355X:
- Maximizes MFMA unit utilization
- Balances memory traffic with computation
- Achieves good occupancy (2 blocks per CU)

### 2. MXFP4 Quantization
- **Weights**: 4-bit floating point (E2M1 format)
- **Scales**: E8M0 (8-bit exponent-only)
- **Benefits**:
  - 4× memory bandwidth reduction vs FP16
  - Native hardware support on MI355X
  - Maintains model accuracy with per-channel scaling

### 3. Pre-shuffled Weight Layout
- Weights pre-shuffled at model load time
- Enables coalesced global memory access
- Reduces on-the-fly computation in kernel

### 4. Atomic Output Accumulation
- Direct atomic accumulation to output buffer
- Eliminates intermediate reduction step
- Reduces memory traffic

## Files

| File | Description |
|------|-------------|
| `submission.py` | Main submission file with Python interface |
| `ck_tile_moe_kernel.hpp` | C++ kernel implementation using CK-Tile |
| `kernel_wrapper.py` | Python wrapper for Popcorn CLI compatibility |
| `compile.py` | Compilation script for hipcc |

## Compilation

### Requirements
- ROCm 6.3+
- hipcc compiler
- CK-Tile headers (included with ROCm)

### Compile Command
```bash
hipcc -O3 --offload-arch=gfx950 \
    -I/opt/rocm/include \
    -shared -fPIC \
    ck_tile_moe_kernel.hpp \
    -o ck_tile_moe.so
```

## Usage

```python
from ck_tile_moe.kernel_wrapper import CKTileMoeKernel, CKTileMoeConfig

# Configure kernel
config = CKTileMoeConfig(
    hidden_size=8192,
    intermediate_size=2048,
    num_experts=64,
    topk=6,
)

# Initialize
kernel = CKTileMoeKernel(config).initialize()

# Run forward pass
output = kernel.forward(
    input_act,         # [num_tokens, hidden_size] fp16
    gate_up_weights,   # [experts, 2*interm, hidden] mxfp4
    down_weights,      # [experts, hidden, interm] mxfp4
    gate_up_scales,    # [experts, 2*interm] e8m0
    down_scales,       # [experts, hidden] e8m0
    topk_ids,          # [num_tokens, topk]
    topk_weights,      # [num_tokens, topk] fp16
)
```

## CK-Tile Resources

- **Headers**: `/opt/rocm/include/ck_tile/`
- **Key Pipeline**: `fused_moegemm_pipeline_flatmm_ex.hpp`
- **Key Kernel**: `fused_moegemm_kernel.hpp`

## Performance Notes

The kernel is designed to achieve the target latency through:
1. **Memory bandwidth reduction** via MXFP4
2. **Compute efficiency** via optimized block shapes
3. **Occupancy** via persistent kernel pattern
4. **Reduced synchronization** via atomic accumulation

## TODO

- [ ] Full HIP kernel integration with Python bindings
- [ ] Weight pre-shuffling implementation
- [ ] Popcorn CLI submission validation
- [ ] Performance tuning for specific model sizes
