# CK-Tile Fused MoE Optimization Implementation Spec

**Target**: <115µs for MoE FFN (Current: ~154µs, Leader: 109.8µs)
**Hardware**: AMD MI355X (gfx950, CDNA 4)
**Library**: CK-Tile (pre-installed at `/opt/rocm/include/ck_tile/`)

---

## 1. Executive Summary

CK-Tile provides production-ready fused MoE kernels with native MXFP4 support. This spec outlines the implementation path to achieve <115µs using:

1. **Fused MoE pipeline** (Gate+Up+Activation+Down in single kernel)
2. **MXFP4 precision** (2x memory bandwidth reduction)
3. **Optimized tile configuration** for CDNA 4
4. **Persistent kernel mode** for better occupancy

---

## 2. CK-Tile Architecture Analysis

### 2.1 Fused MoE Pipeline Structure

```
File: /opt/rocm/include/ck_tile/ops/fused_moe/pipeline/fused_moegemm_pipeline_flatmm_ex.hpp

Pipeline Flow:
  ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
  │  Tokens (A) │────→│  Gate/Up    │────→│   Bridge    │
  │  HBM Load   │     │   GEMM0     │     │    LDS      │
  └─────────────┘     └─────────────┘     └──────┬──────┘
                                                  │
  ┌─────────────┐     ┌─────────────┐            │
  │   Output    │←────│    Down     │←───────────┘
  │   Atomic    │     │   GEMM1     │  SiLU/SwiGLU
  │    Add      │     │             │  Activation
  └─────────────┘     └─────────────┘
```

**Key Components**:
- `FusedMoeGemmPipeline_FlatmmEx`: 2-stage fused pipeline
- Bridge LDS eliminates intermediate HBM write/read
- Async global→shared loads with double buffering
- Token routing via sorted indices

### 2.2 MXFP4 Data Type Support

```cpp
// File: /opt/rocm/include/ck_tile/core/numeric/pk_fp4.hpp

struct pk_float4_e2m1_t {
    using raw_type = uint8_t;  // 2 FP4 values per byte
    type data;

    // Device conversion enabled for gfx950
    #if defined(__gfx950__)
    #define CK_TILE_FP4_CVT_DEVICE 1
    #endif
};

// Scale granularity: K=32 (E8M0 scale per 32 values)
// Layout: MXdlPack=2, NXdlPack=2, KXdlPack=2
// Vector load: 32 bytes fixed for FP4 shuffle layout
```

### 2.3 MoE Flatmm Kernel

```cpp
// File: /opt/rocm/include/ck_tile/ops/flatmm/kernel/moe_flatmm_kernel.hpp

template <typename TilePartitioner_,
          typename FlatmmPipeline_,
          typename EpiloguePipeline_,
          MoeFlatmmKind kind,
          typename FusedActivation = moe::MoeSilu>
struct MoeFlatmmKernel;

enum class MoeFlatmmKind {
    kFFN_gemm1_gate_only,  // Gate only (g1u0)
    kFFN_gemm1_gate_up,  // Fused Gate+Up (g1u1)
    kFFN_gemm2           // Down projection
};

// MXFP4 detection
static constexpr bool MXFP4_Pipeline = std::is_same_v<BDataType, pk_fp4_t>;
static constexpr int MXFP4N_Pack = 2;
static constexpr int MXFP4K_Pack = 2;
```

---

## 3. Implementation Path to <115µs

### 3.1 Performance Gap Analysis

| Component | Current | Leader | Gap |
|-----------|---------|--------|-----|
| MoE FFN | ~154µs | 109.8µs | ~29% |

**Root Cause**: Separate kernels for Gate, Up, Down with HBM round-trips
**Solution**: Single fused kernel with Bridge LDS

### 3.2 Optimization Strategy

#### Phase 1: Fused Pipeline (Target: ~130µs)
Replace separate kernels with `fused_moegemm`:
```cpp
using Pipeline = FusedMoeGemmPipeline_FlatmmEx<
    Problem,
    Policy,
    BlockShape<kM, kN, kK>  // Optimized for CDNA 4
>;
```

**Key tile parameters**:
- `Block_M`: 16 (minimum for CDNA 4 MFMA)
- `Block_K`: 64-128 (packed bytes for MXFP4)
- `Block_N`: 256-512 (expert hidden dim)

#### Phase 2: MXFP4 Precision (Target: ~115µs)
Use `pk_fp4_t` for weights:
```cpp
using ADataType = bf16_t;      // Activations
using BDataType = pk_fp4_t;    // Weights (MXFP4)
using CDataType = float;       // Accumulation
using ODataType = bf16_t;      // Output
```

**Scale handling**:
```cpp
// E8M0 scale per 32 K values
static constexpr int ScaleGranularityK = 32;
// Scale load pattern: NXdlPack * KXdlPack = 4
static constexpr int ScaleBload_K1 = 4;
```

#### Phase 3: Persistent Kernel (Target: <115µs)
Enable persistent mode for better occupancy:
```cpp
static constexpr bool UsePersistentKernel = true;
// Grid size calculated from device properties
auto grid = MoeFlatmmKernel::GridSize(kargs);
```

### 3.3 CDNA 4-Specific Optimizations

**MFMA Instruction**: `mfma_f32_32x32x64_f8f6f4`
**Wave Size**: 64 lanes
**XCD Topology**: 8 chiplets (304 CUs total)

**Tile constraints**:
```cpp
// CK-Tile policy from fused_moegemm_pipeline_flatmm_policy.hpp
static constexpr index_t Block_M = 16;   // Minimum for CDNA 4
static constexpr index_t Block_K = 64;   // Packed bytes for MXFP4
static constexpr index_t WarpSize = 64;  // CDNA 4 wave size

// Alignment requirements
static constexpr index_t kAlignmentA = 16 / sizeof(ADataType);
static constexpr index_t kAlignmentG = 16 / sizeof(GDataType);
static constexpr index_t kAlignmentD = 16 / sizeof(DDataType);
```

**Sequencer Pattern**:
```cpp
// From fused_moegemm_pipeline_flatmm_ex.hpp
enum class FusedMoeGemmPipelineSequencerEnum {
    SLD_A = 1,  // Shared load A
    GLD_A = 2,  // Global load A
    GLD_B = 4,  // Global load B (Gate/Up/Down)
    GST_O = 8   // Global store Output
};
```

---

## 4. Python API Bindings

### 4.1 PyTorch Extension Structure

```python
# kernels/moe_fused_ck_tile/submission.py
import torch
from torch.utils.cpp_extension import load_inline

# CK-Tile header paths
CK_TILE_INCLUDE = "/opt/rocm/include"

ck_moe_source = """
#include <ck_tile/core.hpp>
#include <ck_tile/ops/fused_moe.hpp>
#include <ck_tile/ops/flatmm.hpp>

torch::Tensor fused_moe_fwd(
    torch::Tensor tokens,           // [num_tokens, hidden_dim]
    torch::Tensor gate_up_weight, // [num_experts, intermediate_dim*2, hidden_dim]
    torch::Tensor down_weight,      // [num_experts, hidden_dim, intermediate_dim]
    torch::Tensor topk_ids,         // [num_tokens, topk]
    torch::Tensor topk_weights,     // [num_tokens, topk]
    torch::Tensor sorted_token_ids,
    torch::Tensor sorted_expert_ids,
    torch::Tensor sorted_weights,
    int num_experts,
    int topk
) {
    using namespace ck_tile;

    // Define problem type
    using ADataType = bf16_t;
    using BDataType = pk_fp4_t;  // MXFP4
    using CDataType = float;
    using ODataType = bf16_t;

    // Instantiate fused MoE kernel
    // ... (template instantiation)
}
"""
```

### 4.2 Token Routing Setup

```python
def prepare_moe_routing(topk_ids: torch.Tensor, topk_weights: torch.Tensor):
    """
    Prepare sorted indices for CK-Tile fused MoE.

    Args:
        topk_ids: [num_tokens, topk] - expert indices per token
        topk_weights: [num_tokens, topk] - routing weights

    Returns:
        sorted_token_ids: flattened token indices
        sorted_expert_ids: expert index per token slice
        sorted_weights: corresponding weights
        max_token_id: max tokens per expert
    """
    num_tokens, topk = topk_ids.shape

    # Flatten and sort by expert
    flat_tokens = torch.arange(num_tokens, device=topk_ids.device).repeat_interleave(topk)
    flat_experts = topk_ids.view(-1)
    flat_weights = topk_weights.view(-1)

    # Sort by expert ID
    sorted_indices = torch.argsort(flat_experts)
    sorted_token_ids = flat_tokens[sorted_indices]
    sorted_expert_ids = flat_experts[sorted_indices]
    sorted_weights = flat_weights[sorted_indices]

    # Compute max tokens per expert for padding
    expert_counts = torch.bincount(sorted_expert_ids, minlength=num_experts)
    max_token_id = expert_counts.max().item()

    return sorted_token_ids, sorted_expert_ids, sorted_weights, max_token_id
```

### 4.3 Weight Formatting for MXFP4

```python
def quantize_to_mxfp4(weight: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
    """
    Quantize fp16/bf16 weights to MXFP4 format.

    Args:
        weight: [..., K] where K % 32 == 0

    Returns:
        weight_fp4: packed fp4 values (2 per uint8)
        scales: E8M0 scales per 32 values
    """
    # MXFP4 format: fp4x2 values + E8M0 scale per 32 values
    K = weight.shape[-1]
    assert K % 32 == 0, "K must be multiple of 32 for MXFP4"

    # Reshape to [..., K//32, 32]
    weight_reshaped = weight.reshape(*weight.shape[:-1], K // 32, 32)

    # Compute E8M0 scale per group
    max_vals = weight_reshaped.abs().amax(dim=-1, keepdim=True)
    scales = max_vals / 6.0  # FP4 max value is 6.0

    # Quantize to FP4 (E2M1 format)
    weight_normalized = weight_reshaped / scales
    # ... pack 2 FP4 values into uint8

    return weight_fp4_packed, scales_e8m0
```

---

## 5. Tile Configuration Recommendations

### 5.1 DeepSeek-R1 MoE Configuration

```python
# DeepSeek-R1 MoE parameters
HIDDEN_DIM = 7168
INTERMEDIATE_DIM = 18432  # MLP dim
NUM_EXPERTS = 256
TOPK = 8

# Recommended tile sizes for CDNA 4
TILE_CONFIG = {
    "Block_M": 16,        # Minimum for MFMA
    "Block_Nr0": 256,     # Gate/Up projection
    "Block_Kr0": 64,      # Hidden dim packing
    "Block_N1": 512,      # Down projection
    "Block_Kr0_scale": 4, # Scale packing
    "WarpPerBlock_M0": 1,
    "Repeat_M0": 1,
    "Repeat_N0": 4,
    "Repeat_K0": 4,
}
```

### 5.2 Performance Projections

| Configuration | Expected Latency | vs Target |
|--------------|------------------|-----------|
| Baseline (separate kernels) | ~154µs | +40% |
| + Fused pipeline | ~130µs | +18% |
| + MXFP4 precision | ~115µs | +5% |
| + Persistent kernel | <110µs | **-1%** |

---

## 6. Integration with Popcorn CLI

### 6.1 Submission Structure

```python
# luma_speedrun/amd-moe-mxfp4-fused/submission.py

import torch
import torch.nn.functional as F
from pathlib import Path

# Load CK-Tile fused kernel
from ck_tile_fused_moe import fused_moe_fwd

def fused_moe_ck_tile(
    tokens: torch.Tensor,
    gate_up_weight: torch.Tensor,
    down_weight: torch.Tensor,
    topk_ids: torch.Tensor,
    topk_weights: torch.Tensor,
) -> torch.Tensor:
    """
    Fused MoE FFN using CK-Tile.

    Args:
        tokens: [num_tokens, hidden_dim]
        gate_up_weight: [num_experts, intermediate_dim*2, hidden_dim]
        down_weight: [num_experts, hidden_dim, intermediate_dim]
        topk_ids: [num_tokens, topk]
        topk_weights: [num_tokens, topk]

    Returns:
        output: [num_tokens, hidden_dim]
    """
    # Prepare routing
    sorted_token_ids, sorted_expert_ids, sorted_weights, max_tokens = \
        prepare_moe_routing(topk_ids, topk_weights)

    # Call CK-Tile fused kernel
    output = fused_moe_fwd(
        tokens,
        gate_up_weight,
        down_weight,
        topk_ids,
        topk_weights,
        sorted_token_ids,
        sorted_expert_ids,
        sorted_weights,
        max_tokens,
    )

    return output
```

### 6.2 Benchmark Command

```bash
# Run via Popcorn CLI
popcorn submit \
  --challenge amd-moe-mxfp4-fused \
  --runtime rocm-6.3 \
  --gpus 1 \
  --variant gfx950 \
  python submission.py
```

---

## 7. Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| CK-Tile version mismatch | Medium | High | Check version at `/opt/rocm/include/ck_tile/version.hpp` |
| MXFP4 precision issues | Low | Medium | Compare vs bf16 reference |
| Tile size mismatch | Medium | Medium | Use CK-Tile auto-tuner |
| Token routing overhead | Low | Low | Pre-compute sorted indices |

---

## 8. Next Steps

1. **Immediate**: Implement CK-Tile fused MoE Python bindings
2. **Day 1**: Benchmark tile configurations (Block_M/N/K sweep)
3. **Day 2**: Integrate MXFP4 weight quantization
4. **Day 3**: Enable persistent kernel mode
5. **Day 4**: Submit to leaderboard and verify <115µs

---

## 9. References

- CK-Tile source: `/opt/rocm/include/ck_tile/`
- Fused MoE pipeline: `ops/fused_moe/pipeline/fused_moegemm_pipeline_flatmm_ex.hpp`
- MXFP4 types: `core/numeric/pk_fp4.hpp`
- MoE kernel: `ops/flatmm/kernel/moe_flatmm_kernel.hpp`
- FlatMM blocks: `ops/flatmm/block/flatmm_*.hpp`

---

**Author**: amd-speedrun-specialist
**Date**: 2026-03-27
**Status**: Implementation Ready
