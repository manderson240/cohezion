# HipKittens Study Notes for MoE Implementation

**Paper:** HipKittens: Fast and Furious AMD Kernels (arXiv:2511.08083)
**Source:** https://github.com/HazyResearch/HipKittens
**Date:** 2026-03-27

---

## Key Findings

### 1. Tile Primitives

HipKittens uses C++ template-based tile abstractions:

```cpp
// Register tile (in registers, for MFMA)
// Parameters: dtype, rows, cols, layout, matrix_core_shape
rt_bf<16, 32, row_l, rt_16x32_s> A_tile;  // BF16, 16x32, row-major

// Shared memory tile (in LDS/cache)
// Parameters: dtype, rows, cols, swizzle_pattern
st_bf<256, 256, swizzle_16x32> A_smem;    // 256x256 with bank-conflict-free access
```

**Available types:** BF16, FP16, FP8, FP6, FP32
**Note:** No explicit MXFP4 (fp4x2 + E8M0 scale) support listed

### 2. 8-Wave Ping-Pong Scheduling

**Pattern for balanced compute/memory:**
```cpp
#pragma unroll
for (int tile = 0; tile < num_tiles - 2; ++tile, tic ^= 1, toc ^= 1) {
    // Cluster 0: Memory (Wave group 0)
    load(B_tile_0, st_subtile_b);
    load(A_tile, st_subtile_a);
    G::load(As[toc][1], g.a, {...});  // Preload next to shared mem
    asm volatile("s_waitcnt lgkmcnt(8)");
    __builtin_amdgcn_s_barrier();

    // Cluster 1: Compute (Wave group 1)
    asm volatile("s_waitcnt lgkmcnt(0)");
    __builtin_amdgcn_s_setprio(1);     // High priority for compute
    mma_ABt(C_accum, A_tile, B_tile_0, C_accum);
    __builtin_amdgcn_s_setprio(0);
    __builtin_amdgcn_s_barrier();

    // Cluster 2: Memory (Wave group 0)
    load(B_tile_1, st_subtile_b);
    G::load(Bs[tic][0], g.b, {...});
    __builtin_amdgcn_s_barrier();

    // Cluster 3: Compute (Wave group 1)
    asm volatile("s_waitcnt lgkmcnt(0)");
    __builtin_amdgcn_s_setprio(1);
    mma_ABt(C_accum, A_tile, B_tile_1, C_accum);
    __builtin_amdgcn_s_setprio(0);
    __builtin_amdgdn_s_barrier();
}
```

**Key elements:**
- `__builtin_amdgcn_s_barrier()` - Wave synchronization
- `__builtin_amdgcn_s_setprio(1)` - Boost compute wave priority
- `s_waitcnt lgkmcnt(N)` - Wait for memory operations
- Alternating compute/memory clusters

### 3. GEMM Hot Loop Structure

```cpp
// BF16 GEMM achieving 1610 TFLOPS (99% peak on MI355X)
// Key: Large tiles, ping-pong scheduling

// Tile dimensions (tuned for MI355X)
constexpr int REG_BLOCK_M = 128;  // Register tile M
constexpr int REG_BLOCK_N = 128;  // Register tile N
constexpr int K_STEP = 64;          // K dimension step

// Load from global to shared
G::load(As[0][0], g.a, {...});
G::load(Bs[0][0], g.b, {...});
__builtin_amdgcn_s_barrier();

// Main loop with ping-pong
for (int tile = 0; tile < num_tiles; ++tile) {
    // Load next tiles to shared mem (in background)
    G::load(As[toc][0], g.a, {...});

    // Compute current tiles
    mma_ABt(C_accum, A_tile, B_tile, C_accum);
}
```

### 4. Performance Benchmarks

| Kernel | HipKittens | AITER ASM | Speedup |
|--------|-----------|-----------|---------|
| BF16 GEMM 8192³ | 1610 TFLOPS | 1610 TFLOPS | 1.0× |
| FP8 GEMM 8192³ | 3327 TFLOPS | 3300 TFLOPS | 1.01× |
| GQA Attn Bwd | 1091 TFLOPS | 472 TFLOPS | 2.3× |

### 5. Critical Gap: No MoE or MXFP4

**Missing from HipKittens:**
- No MoE-specific kernels
- No MXFP4 (fp4x2 + E8M0) primitives
- No multi-GEMM fusion examples

**What we'd need to implement:**
1. MXFP4 tile unpacking (custom)
2. E8M0 scale application (custom)
3. 2-stage GEMM→SiLU→GEMM (custom pipeline)
4. Token routing integration (host-side)

---

## MoE Adaptation Strategy

### Proposed Structure

```cpp
// MoE 2-Stage Fusion Kernel
// Input: hidden [M, d_hidden] bf16
// Weights: w1 [E, 2*N, K], w2 [E, K, N] (in MXFP4, dequantize in kernel)
// Output: [M, d_hidden]

template <int E, int d_hidden, int d_expert>
__global__ void moe_fused_kernel(
    bf16_t* hidden,
    fp4x2_t* w1_packed,    // [E, 2*d_expert, d_hidden/2]
    e8m0_t* w1_scale,      // [E, 2*d_expert, d_hidden/32]
    fp4x2_t* w2_packed,    // [E, d_hidden, d_expert/2]
    e8m0_t* w2_scale,      // [E, d_hidden, d_expert/32]
    int* topk_ids,         // [M, topk]
    float* topk_weights,   // [M, topk]
    bf16_t* output
) {
    // Tile setup
    rt_bf<64, 64, row_l> hidden_tile;      // Loaded hidden
    rt_bf<64, 64, row_l> gate_up_tile;     // Stage 1 output
    rt_bf<64, 64, row_l> output_tile;      // Stage 2 output

    // Per-token loop
    int m = blockIdx.x * blockDim.x + threadIdx.x;
    if (m >= M) return;

    // Load hidden for this token
    load(hidden_tile, hidden + m * d_hidden);

    // Accumulator for output
    rt_bf<1, d_hidden, row_l> accum;
    zero(accum);

    // Process each expert
    for (int k = 0; k < topk; ++k) {
        int eid = topk_ids[m * topk + k];
        float weight = topk_weights[m * topk + k];

        // Stage 1: Gate+Up GEMM
        // Load w1 tiles, dequantize MXFP4 on-the-fly
        for (int n1 = 0; n1 < 2*d_expert; n1 += 64) {
            // Custom: load fp4x2, unpack, scale
            auto w1_tile = load_mxfp4_tile(w1_packed, eid, n1);
            auto s1_tile = load_scale_tile(w1_scale, eid, n1);
            auto w1_bf16 = mxfp4_to_bf16(w1_tile, s1_tile);

            mma_AB(gate_up_tile, hidden_tile, w1_bf16, gate_up_tile);
        }

        // SiLU + Mul in registers
        auto gate = slice(gate_up_tile, 0, d_expert);
        auto up = slice(gate_up_tile, d_expert, 2*d_expert);
        auto activated = silu(gate) * up;

        // Stage 2: Down GEMM
        for (int n2 = 0; n2 < d_hidden; n2 += 64) {
            auto w2_tile = load_mxfp4_tile(w2_packed, eid, n2);
            auto s2_tile = load_scale_tile(w2_scale, eid, n2);
            auto w2_bf16 = mxfp4_to_bf16(w2_tile, s2_tile);

            mma_ABt(output_tile, activated, w2_bf16, output_tile);
        }

        // Accumulate with weight
        accum = accum + output_tile * weight;
    }

    // Write output
    store(output + m * d_hidden, accum);
}
```

**Challenges:**
1. `load_mxfp4_tile()` - Need custom implementation
2. `mxfp4_to_bf16()` - Need custom tile dequantization
3. Variable topk per token - complicates warp scheduling
4. Expert-specific weight loading - divergence

---

## MXFP4 Implementation Challenge

HipKittens doesn't have built-in MXFP4. We'd need:

```cpp
// Custom MXFP4 tile handling
struct mxfp4_tile {
    uint8_t packed[32];  // 64 values, 2 per byte
};

// Unpack E2M1 to BF16
rt_bf<16, 64> mxfp4_to_bf16(mxfp4_tile packed, e8m0_t scale) {
    rt_bf<16, 64> result;

    // Each thread unpacks subset
    for (int i = threadIdx.x; i < 64; i += blockDim.x) {
        uint8_t byte = packed.packed[i / 2];
        uint8_t nibble = (i % 2 == 0) ? (byte >> 4) : (byte & 0x0F);

        // E2M1 to float: sign(1) + exp(2) + mantissa(1)
        // Lookup table for conversion
        float val = e2m1_to_float(nibble);

        // Apply E8M0 scale
        float scaled = val * e8m0_to_float(scale);

        result[i] = float_to_bf16(scaled);
    }

    return result;
}
```

---

## Conclusion

**HipKittens capabilities:**
- ✅ Excellent tile primitives for AMD
- ✅ 8-wave ping-pong scheduling
- ✅ Peak GEMM performance
- ✅ Easy to write/read kernels

**Gaps for MoE:**
- ❌ No MXFP4 support
- ❌ No MoE kernels
- ❌ No multi-stage fusion examples
- ❌ Requires custom dequantization

**Alternative:** CK-Tile has `fused_moe`, `moe_flatmm`, `MXFP4_Pipeline` - more production-ready.

**Decision:** Proceed with HipKittens prototype for learning, but CK-Tile may be faster path to <115µs.

---

*Study completed: 2026-03-27*
*Ready for environment setup*
