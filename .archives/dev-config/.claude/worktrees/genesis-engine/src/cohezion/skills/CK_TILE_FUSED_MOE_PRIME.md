---
name: ck-tile-fused-moe
description: CK-Tile Fused MoE kernel implementation using Composable Kernel Tile API for 2-stage Mixture-of-Experts with MXFP4 quantization on AMD GPUs. Use when implementing high-performance MoE kernels, working with CK-Tile library, or optimizing for MI300X/MI355X GPUs.
metadata:
  version: "1.0"
  legacy-name: CK_TILE_FUSED_MOE
  category: amd_optimization
  source_worktree: luma_amd_speedrun
  source_session: "Session 77-79"
---

# SKILL: CK_TILE_FUSED_MOE

## DOMAIN EXPERTISE
You are a specialist in **CK-Tile (Composable Kernel Tile) fused MoE kernel implementation** for AMD GPUs. You understand the 2-stage MoE pipeline, MXFP4 quantization formats, and how to leverage CK-Tile's header-only C++ API for maximum performance.

## KEY FINDINGS

### CK-Tile Installation
- CK-Tile is **pre-installed** at `/opt/rocm/include/ck_tile/`
- Header-only library - no separate compilation needed
- Part of ROCm 6.x+ distribution

### Fused MoE Pipeline
- Primary header: `fused_moegemm_pipeline_flatmm_ex.hpp`
- Implements **2-stage MoE** pipeline for optimal throughput
- Fuses expert routing with GEMM operations to reduce memory traffic

### MXFP4 Quantization Support
- Data type: `pk_fp4_t` (packed FP4)
- Scale format: `E8M0` (8-bit exponent, 0-bit mantissa)
- Significantly higher throughput than FP16/BF16 on CDNA3/CDNA4

### Performance Path to <115µs
The optimal path to reach leaderboard-leading performance (~109.8µs):
1. **Fused Pipeline** - Eliminate intermediate memory copies
2. **MXFP4 quantization** - Maximize arithmetic intensity
3. **Persistent Kernel** - Keep weights resident in cache across iterations

## BLOCKERS & LIMITATIONS

### Current Blockers
1. **aiter not installed on runner** - Cannot use AITER's fused_moe backend directly
2. **PyTorch C++ Extension requires hipcc** - Must compile extensions with AMD's HIP compiler
3. **No Python bindings available** - CK-Tile is C++ only; requires PyTorch C++ integration

### Workarounds
- Use `torch.utils.cpp_extension.load` with `hipcc` as compiler
- Pre-compile kernels and load as shared objects
- ~~Consider Triton-based fallback~~ **BLOCKED**: Triton `float4_e2m1fn_x2` KeyError on AMD (see BLOCKER_REGISTRY.md #004)
- CK-Tile is the primary FP4 path when Triton blocked

## USAGE

### Compiling CK-Tile MoE Kernel
```cpp
#include <ck_tile/fused_moegemm_pipeline_flatmm_ex.hpp>
#include <ck_tile/core.hpp>

// Define tile shapes for CDNA3/CDNA4
using BlockTile = ck_tile::sequence<128, 128, 64>;
using WarpTile = ck_tile::sequence<64, 64, 32>;

// MXFP4 types
using ADataType = ck_tile::pk_fp4_t;      // FP4 packed
using BDataType = ck_tile::pk_fp4_t;
using AccDataType = float;
using CDataType = ck_tile::bf16_t;

// E8M0 scale type
using AScaleDataType = ck_tile::e8m0_t;
using BScaleDataType = ck_tile::e8m0_t;
```

### PyTorch C++ Extension Integration
```python
import torch
from torch.utils.cpp_extension import load

# Load CK-Tile kernel as PyTorch extension
ck_tile_moe = load(
    name="ck_tile_moe",
    sources=["ck_tile_moe_kernel.cpp"],
    extra_include_paths=["/opt/rocm/include"],
    extra_cflags=["-O3", "-DCK_TILE_FMHA_FWD_FAST_EXP=1"],
    extra_ldflags=["-L/opt/rocm/lib", "-lamdhip64"],
    verbose=True
)

# Call fused MoE
output = ck_tile_moe.fused_moe_fwd(
    input_activation,      # [tokens, hidden_dim]
    expert_weights,          # [num_experts, hidden_dim, ffn_dim]
    routing_weights,       # [tokens, top_k]
    routing_indices,       # [tokens, top_k]
    scale_a,               # E8M0 scales for activations
    scale_b                # E8M0 scales for weights
)
```

### Performance Checklist
- [ ] Use `pk_fp4_t` for weights and activations
- [ ] Configure `BlockTile` based on target GPU (128x128x64 for MI300X)
- [ ] Enable `CK_TILE_FMHA_FWD_FAST_EXP` for faster exponential
- [ ] Pre-allocate output buffers to avoid malloc in hot path
- [ ] Use persistent kernel pattern for iterative workloads

## REFERENCES

- CK-Tile headers: `/opt/rocm/include/ck_tile/`
- Source: Session 77-79 AMD Speedrun Research
- Related: `AMD_MOE_MXFP4_OPTIMIZATION`, `ROCM_GFX950_SUPPORT_PRIME`

## VERSION

v1.0 (Extracted from unified registry)
