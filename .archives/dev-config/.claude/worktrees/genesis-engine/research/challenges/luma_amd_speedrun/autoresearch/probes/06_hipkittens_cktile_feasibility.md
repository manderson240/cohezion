# HipKittens vs CK-Tile Feasibility Report

**Date:** 2026-03-27
**Focus:** MoE inter-stage fusion on AMD MI355X (gfx950)
**Objective:** Determine viable path for closing 1.4x gap (154µs → 109.8µs)

---

## Executive Summary

| Framework | MXFP4 Support | MoE Viability | Recommendation |
|-----------|---------------|---------------|----------------|
| **HipKittens** | Not explicitly | Requires custom implementation | Research further |
| **CK-Tile** | Yes (flatmm) | Via 2-stage GEMM fusion | **Primary path** |
| **aiter fused_moe** | Yes (current) | At API ceiling | Baseline only |

**Conclusion:** CK-Tile flatmm is the most viable path for MoE optimization. HipKittens lacks explicit MXFP4 support but may provide scheduling primitives.

---

## HipKittens Analysis

### What HipKittens Provides

From [HipKittens GitHub](https://github.com/HazyResearch/HipKittens) and [paper](https://arxiv.org/abs/2511.08083):

**Available Kernels:**
- BF16 GEMM (99% peak on MI355X)
- FP8 GEMM (100% peak on MI355X)
- Attention forward/backward (MHA, GQA)
- Memory-bound kernels (RoPE, LayerNorm)
- Fused operations (dropout-residual-layernorm)

**Tile Primitives:**
```cpp
// Register tiles mapping to MFMA instructions
rt<Dtype, M, TK, Layout, Shape>  // Register tile
st<Dtype, TileRows, TileCols, Shape>  // Shared memory tile

// Bulk operations
mma(A, B, C)  // Matrix multiply-accumulate
load/store    // Async memory movement
exp2, add, sum // Elementwise ops
```

**Scheduling Patterns:**
1. **8-wave ping-pong:** Two waves alternate compute/memory - ideal for balanced workloads
2. **4-wave interleave:** Fine-grained compute/memory overlap - for memory-heavy kernels

### MXFP4 Support Assessment

**Finding:** HipKittens does NOT explicitly list MXFP4 support.

**Evidence:**
- README lists: BF16, FP8 GEMM implementations
- No mention of fp4, e2m1, or MXFP4 dtypes
- No quantized kernel examples beyond FP8

**Potential Path:**
HipKittens is a C++ embedded DSL. If we can express MXFP4 dequantization as elementwise ops:

```cpp
// Hypothetical MXFP4 tile handling
// Step 1: Load fp4x2 packed values
auto fp4_tile = load<st<uint8_t, M, K/2>>(A_ptr);

// Step 2: Extract nibbles (custom unpacking)
auto val1 = (fp4_tile >> 4) & 0x0F;  // High nibble
auto val2 = fp4_tile & 0x0F;          // Low nibble

// Step 3: Lookup table for E2M1 → bf16
auto bf16_vals = e2m1_to_bf16_table(val1, val2);

// Step 4: Apply E8M0 scale
auto scale = load<e8m0_tile>(scale_ptr);
auto dequantized = bf16_vals * e8m0_to_f32(scale);

// Step 5: Regular GEMM with dequantized bf16
mma(dequantized, B, C);
```

**Verdict:** Possible but requires significant custom implementation. HipKittens' value is in scheduling primitives, not MXFP4 primitives.

### MoE Implementation Potential

**Finding:** No dedicated MoE kernel in HipKittens.

**COMET Reference:** HipKittens paper cites COMET (MLSys 2025) for MoE on NVIDIA. Could theoretically adapt wave specialization patterns.

**2-Stage Fusion Challenge:**
```cpp
// MoE requires:
// 1. Token routing (sorting)
// 2. Gate+Up GEMM (with SiLU)
// 3. Down GEMM
// 4. Weight accumulation

// HipKittens can handle #2 and #3 if we:
// - Implement MXFP4 dequantization
// - Manage expert routing in host code
// - Launch separate kernels per expert (not fused)
```

**Verdict:** HipKittens alone is insufficient. Would need to implement:
1. MXFP4 tile primitives (dequantization)
2. 2-stage fusion pattern
3. Token routing integration

---

## CK-Tile Analysis

### What CK-Tile Provides

From ROCm blogs and composable_kernel examples:

**FlatMM (Flattened Batched GEMM):**
- Example: `composable_kernel/example/ck_tile/18_flatmm/`
- Supports MXFP4 mixed precision
- Uses `mfma_f32_32x32x64_f8f6f4` instruction

**MXFP4 Support:**
```cpp
// From CK-Tile flatmm example:
// A: MXFP4 [M, K/2] packed
// B: MXFP4 [N, K/2] packed (transposed)
// C: bf16/fp32 [M, N]
// Scales: E8M0 [M, K/32], [N, K/32]

// Tile pipeline:
// 1. Load A, B tiles from global → LDS
// 2. Load scales → registers
// 3. MFMA with scale application
// 4. Accumulate → store to global
```

### Availability on Runner

**Expected Location:**
```bash
# CK-Tile may be available via:
/opt/rocm/include/ck_tile/           # Headers
/opt/rocm/lib/libck_tile.so          # Library
/opt/rocm/bin/ckprofiler              # Profiling tool

# Or via aiter's internal CK:
~/.local/lib/python3.x/site-packages/aiter/ck_tile/
```

**Verification Steps:**
```python
# Check if CK-Tile is importable via aiter
try:
    from aiter import ck_tile_gemm
    print("CK-Tile available via aiter")
except ImportError:
    print("CK-Tile not directly accessible")

# Check ROCm installation
import subprocess
result = subprocess.run(['ls', '/opt/rocm/include/ck_tile/'],
                       capture_output=True, text=True)
print(result.stdout)
```

### MXFP4 MFMA Instruction

**`mfma_f32_32x32x64_f8f6f4`:**
- 32x32 output tile
- 64-element K reduction
- Supports fp8, fp6, fp4 mixed precision
- Scale application via separate MFMA

**Tile Configuration:**
```cpp
// From CK-Tile MXFP4 examples:
using TileGemm = TileGemmShape<32, 32, 64>;  // M, N, K
using ScaleBlock = 32;  // One scale per 32 fp4 elements

// Pipeline stages:
// - Load A, B tiles
// - Unpack fp4 → f32
// - Multiply by E8M0 scale
// - MFMA accumulate
```

### MoE 2-Stage Fusion

**CK-Tile Approach:**
```cpp
// Stage 1: Gate+Up GEMM + SiLU
// Stage 2: Down GEMM

// Fusion opportunity:
// Keep intermediate in LDS, not HBM
// Custom tile pipeline:
template <typename AType, typename BType, typename CType>
void fused_moe_kernel(
    const AType* hidden,      // [M, K] bf16
    const BType* w1,          // [E, 2*N, K/2] fp4x2
    const BType* w2,          // [E, K, N/2] fp4x2
    CType* output             // [M, K] bf16
) {
    // Per-expert loop (or parallel across experts)
    for (int e = 0; e < num_experts; ++e) {
        // Stage 1: Load hidden, w1 tiles
        // Dequantize MXFP4 → bf16 in LDS
        // GEMM(hidden, w1_gate) → gate_out
        // GEMM(hidden, w1_up)   → up_out
        // SiLU(gate_out) * up_out → intermediate (LDS)

        // Stage 2: Load w2 tiles
        // GEMM(intermediate, w2) → output
        // Accumulate with topk_weights
    }
}
```

**Verdict:** CK-Tile has the primitives for MXFP4 and GEMM fusion. The challenge is integrating with token routing.

---

## Comparison Summary

| Aspect | HipKittens | CK-Tile | aiter fused_moe |
|--------|-----------|---------|-----------------|
| **MXFP4 Primitives** | ❌ Not explicit | ✅ Yes (flatmm) | ✅ Yes (fused_moe) |
| **Scheduling Control** | ✅ Wave-level | ⚠️ Tile-level | ❌ Black box |
| **2-Stage Fusion** | ⚠️ Manual | ⚠️ Manual | ❌ Separate kernels |
| **Token Routing** | ❌ Host-side | ❌ Host-side | ✅ Built-in |
| **JIT Overhead** | ❌ Compilation | ❌ Compilation | ⚠️ ~128-260s |
| **Python API** | ❌ C++ only | ⚠️ Via aiter | ✅ Python |
| **Runner Availability** | ❌ Needs install | ⚠️ Via ROCm | ✅ Pre-installed |

---

## Recommended Approach

### Path 1: CK-Tile Extension (Primary)

**Strategy:** Extend flatmm example for 2-stage MoE fusion.

**Steps:**
1. Study `/opt/rocm/share/ck_tile/examples/flatmm/`
2. Understand MXFP4 tile pipeline
3. Create custom 2-stage kernel:
   - Input: hidden (bf16), w1/w2 (MXFP4), topk_ids/weights
   - Output: fused result
4. Compile with `hipcc` (if runner permits)
5. Dispatch via `torch.utils.cpp_extension.load_inline` (test if blocked)

**Risk:** Runner static scanning may block custom kernel dispatch.

### Path 2: aiter + CK Bridge (Lower Risk)

**Strategy:** Use aiter's internal CK dispatch.

```python
# aiter already uses CK internally
# Investigate if we can:
# 1. Access lower-level CK APIs via aiter
# 2. Create custom kernel that reuses aiter's sorting
# 3. Replace 2-stage with fused kernel
```

**Implementation:**
```python
from aiter import fused_moe

# Current: fused_moe handles sorting + 2-stage
# Idea: Direct CK dispatch with custom kernel name

# Check available in aiter:
import aiter
print(dir(aiter))  # Look for ck_tile, ck_moe, etc.
```

### Path 3: HipKittens Hybrid (Research)

**Strategy:** Use HipKittens for scheduling, custom MXFP4 dequant.

**Steps:**
1. Install HipKittens locally
2. Implement MXFP4 tile primitives
3. Prototype 2-stage kernel
4. Compare performance vs CK-Tile

**Risk:** High development effort, no guarantee of success.

---

## Immediate Actions

### For MoE (Priority 1)

1. **Check CK-Tile availability:**
   ```bash
   ls -la /opt/rocm/include/ck_tile/ 2>/dev/null || echo "Not in standard location"
   python3 -c "import aiter; print([x for x in dir(aiter) if 'ck' in x.lower()])"
   ```

2. **Study flatmm example:**
   - Find ROCm composable_kernel examples
   - Understand MXFP4 tile pipeline

3. **Test custom kernel dispatch:**
   - Try `torch.utils.cpp_extension.load_inline` with simple CK code
   - Verify if runner blocks this pattern

### For MLA (Priority 2)

1. **HipKittens attention study:**
   - Clone repo: `git clone https://github.com/HazyResearch/HipKittens`
   - Study attention kernel patterns
   - Assess adaptation to MLA (K=576, V=512)

### For Infrastructure

1. **TRITON_CACHE_DIR:**
   ```bash
   export AITER_JIT_DIR=/tmp/aiter_jit_cache
   export TRITON_CACHE_DIR=/tmp/triton_cache
   ```

---

## Open Questions

1. Is CK-Tile available on Popcorn runners via ROCm?
2. Can we dispatch custom CK kernels without `hipModuleLaunchKernel`?
3. What's the minimal CK-Tile kernel that can be integrated?
4. Does HipKittens have hidden MXFP4 support in development branch?

---

## References

- HipKittens: [GitHub](https://github.com/HazyResearch/HipKittens), [Paper](https://arxiv.org/abs/2511.08083)
- CK-Tile: [ROCm Blog](https://rocm.blogs.amd.com/building-efficient-gemm-kernels-with-ck-tile)
- COMET MoE: MLSys 2025
- `amd-moe-mxfp4-optimization` SKILL.md
- `aiter-kernel-parameter-semantics` SKILL.md

---

*Report prepared by:* AMD Speedrun Specialist
*Status:* Ready for implementation phase
