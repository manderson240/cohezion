# 8-Wave Ping-Pong Implementation Guide
**Source**: HipKittens Paper (arXiv 2511.08083) + AMD ROCm CDNA4 Blog
**Target**: 2680 TFLOPS/s on MI355X (near hipBLASLt 2750)

---

## 🎯 WHY 8-WAVE PING-PONG?

### Problem: Memory vs Compute Imbalance
```
Standard GEMM:
- Compute: MFMA instructions (fast)
- Memory: Global loads (slow, ~HBM bandwidth limited)
- Result: ~500 TFLOPS/s (bottlenecked on memory)

8-Wave Ping-Pong:
- Compute waves and memory waves alternate
- While compute executes, memory loads next tile
- Result: 2680 TFLOPS/s (5× faster!)
```

---

## 📐 WAVE ORGANIZATION (CDNA4)

### Thread Block Structure
```
Waves per block: 8 (launch_bounds(8*64))
Threads per wave: 64 (wavefront size)
Total threads: 512

SIMD lanes: 4 SIMDs, 16 lanes each (V0-V15 per SIMD)
Waves per SIMD: 2 (8 waves / 4 SIMDs)
```

### Ping-Pong Pattern
```
Waves 0-3: COMPUTE WAVES
- Execute MFMA while memory waves load
- Higher priority during compute phase

Waves 4-7: MEMORY WAVES  
- Load global→LDS while compute waves execute
- Stall on barrier while compute works

Within each SIMD:
- Wave 0+4: SIMD 0 (alternate compute/memory)
- Wave 1+5: SIMD 1
- Wave 2+6: SIMD 2
- Wave 3+7: SIMD 3
```

---

## 💻 KERNEL CODE STRUCTURE

```cpp
__global__ __launch_bounds__(512) void gemm_8wave(
    float* A, float* B, float* C,
    int M, int N, int K
) {
    // Wave ID
    int wave_id = __builtin_amdgcn_mbcnt_hi(~0u, 
                    __builtin_amdgcn_mbcnt_lo(~0u, 0));
    int lane_id = threadIdx.x % 64;
    
    // Split compute vs memory
    bool is_compute = (wave_id < 4);
    
    // LDS double buffer (CDNA4: 160KB available)
    __shared__ float A_lds[2][BLOCK_M][BLOCK_K];
    __shared__ float B_lds[2][BLOCK_K][BLOCK_N];
    
    int cur = 0, nxt = 1;
    
    // Prologue: First tile
    if (!is_compute) {
        load_global_to_LDS(A, B, nxt);
    }
    __builtin_amdgcn_s_barrier();  // All sync
    
    // Hot loop
    for (int k = 0; k < K; k += BLOCK_K) {
        // Memory waves start next load
        if (!is_compute && k + BLOCK_K < K) {
            load_global_to_LDS(A + offset, B + offset, nxt);
        }
        
        // Compute waves execute MFMA
        if (is_compute) {
            __builtin_amdgcn_s_setprio(1);  // Boost priority
            
            // 4 16x16 blocks per wave
            #pragma unroll
            for (int block = 0; block < 4; block++) {
                float4 acc = __builtin_amdgcn_mfma_f32_16x16x16f32(
                    A_reg, B_reg, acc
                );
            }
            
            __builtin_amdgcn_s_setprio(0);  // Reset
        }
        
        // Swap roles
        __builtin_amdgcn_s_barrier();
        cur ^= 1; nxt ^= 1;
    }
    
    // Write results
    store_C_to_global(C, accumulators);
}
```

---

## 🔥 KEY INSTRUCTIONS

### 1. Global-to-LDS Direct Load
```cpp
// Bypass register file - direct HBM to shared memory
llvm_amdgcn_raw_buffer_load_lds(
    buffer_resource,   // int4 rsrc
    lds_address,       // uint* lds_ptr
    size_bytes,        // int size
    voffset, soffset,  // Offsets
    immediate_offset,  // int offset
    aux_data           // int aux
);

// Performance: 506.70 TFLOPS/s vs 336.88 for vectorized
```

### 2. MFMA with Block Scaling (CDNA4)
```cpp
// New in CDNA4: FP4/FP6/FP8 with E8M0 scaling
float4 c = __builtin_amdgcn_mfma_scale_f32_16x16x128_f8f6f4(
    a_data,      // FP8/FP6/FP4 packed data
    b_data,      // FP8/FP6/FP4 packed data
    c_acc,       // FP32 accumulator
    atype,       // 0=E4M3, 1=E5M2, 2=FP6, 4=FP4
    btype,
    opsel_a,     // Operand select
    scale_a,     // E8M0 scale (uint8)
    opsel_b,
    scale_b      // E8M0 scale
);

// 64× throughput vs FP32 for FP4
```

### 3. Wave Priorities
```cpp
__builtin_amdgcn_s_setprio(1);  // High priority
// ... compute ...
__builtin_amdgcn_s_setprio(0);  // Normal priority

// Ensures compute waves get priority during compute phases
```

### 4. Barrier with Role Swapping
```cpp
__builtin_amdgcn_s_barrier();  // All waves sync
// After barrier: compute↔memory swap double buffer indices
```

---

## ⚡ PERFORMANCE COMPARISON

| Optimization | TFLOPS/s | vs Baseline |
|-------------|----------|------------|
| Naive | 1.15 | 1× |
| LDS Tiling | 4.80 | 4.2× |
| Matrix Cores | 30.05 | 26× |
| Vectorized | 336.88 | 293× |
| Global→LDS | 506.70 | 440× |
| Double Buffer | 1166.41 | 1014× |
| Multi-wave | 2288.53 | 1990× |
| **8-Wave Ping-Pong** | **2680.33** | **2331×** |

**Gap to hipBLASLt: Only 2.5%!**

---

## 🚀 IMPLEMENTATION STEPS

### Step 1: Setup Thread Block
```cpp
constexpr int BLOCK_M = 128;
constexpr int BLOCK_N = 128;
constexpr int BLOCK_K = 128;
constexpr int WAVES = 8;

dim3 block(WAVES * 64);  // 512 threads
dim3 grid(M / BLOCK_M, N / BLOCK_N);
```

### Step 2: Allocate LDS
```cpp
// CDNA4: 160KB LDS per CU
// Double buffer: 2 × 128 × 128 × sizeof(float) = 128KB
// Leaves 32KB for other data
__shared__ float A_lds[2][BLOCK_M][BLOCK_K];
__shared__ float B_lds[2][BLOCK_K][BLOCK_N];
```

### Step 3: Implement Ping-Pong Loop
```cpp
int cur = 0, nxt = 1;

// Prologue
if (is_memory_wave) load_first_tile();
__builtin_amdgcn_s_barrier();

// Hot loop
for (int k = 0; k < K; k += BLOCK_K) {
    if (is_memory_wave && has_more_tiles()) {
        load_next_tile(nxt);
    }
    if (is_compute_wave) {
        __builtin_amdgcn_s_setprio(1);
        compute_current_tile(cur);
        __builtin_amdgcn_s_setprio(0);
    }
    __builtin_amdgcn_s_barrier();
    cur ^= 1; nxt ^= 1;
}
```

### Step 4: Handle Remainder Tiles
```cpp
// Last tiles may be partial
if (k + BLOCK_K >= K) {
    int remaining = K - k;
    load_partial_tile(remaining);
}
```

---

## 🎯 TUNING PARAMETERS

### Block Size Tradeoffs
```
128×128: 128KB LDS, good occupancy
256×128: 256KB LDS, higher arithmetic intensity but lower occupancy
64×64:  32KB LDS, higher occupancy but lower arithmetic intensity
```

### Wave Count
```
8 waves: Balanced (our target)
16 waves: More memory parallelism but lower per-wave resources
4 waves: Not enough to hide latency
```

### LDS Bank Conflicts
```cpp
// Caused by threads accessing same bank
// Solution: Swizzle addressing
int swizzle = (row >> 1) & 7;
int perm = swizzle ^ (((swizzle >> 1) ^ (swizzle >> 2)) & 1);
int col_swizzled = col ^ (perm << 4);

// +10% performance when applied
```

---

## 📊 EXPECTED RESULTS

### GEMM Shape: 4096×4096×4096
- hipBLASLt: ~1.5 ms (2750 TFLOPS/s)
- Our 8-wave: ~1.6 ms (2680 TFLOPS/s)
- Current: ~18.4 µs (different scale - this is microsecond benchmark)

### CDNA4 MI355X Specifics
- Peak: 10 PFLOPs FP4, 5 PFLOPs FP8, 2.5 PFLOPs FP16
- 8-wave gets us to ~1.07 PFLOPs (10.7% of FP8 peak)

---

## 📝 COMPILATION FLAGS

```bash
hipcc -O3 \
  --offload-arch=gfx950 \
  -ffast-math \
  -ffp-contract=fast \
  -mllvm -amdgpu-early-inline-all=true \
  -Xarch_gfx950 -mwavefrontsize64 \
  -o kernel.hsaco kernel.cpp
```

Key flags:
- `-mwavefrontsize64`: Enable 64-thread wavefronts
- `-ffp-contract=fast`: Allow FMA fusion
- `-amdgpu-early-inline-all`: Inline everything for register optimization

---

## 🔄 NEXT STEPS

1. ✅ Research complete (hipKittens, ROCm, CDNA4)
2. ⏳ Compile test kernel (working on this)
3. ⏳ Benchmark vs aiter baseline
4. ⏳ Integrate into submission.py
5. ⏳ Submit to leaderboard

**Estimated time to Rank 1**: 2-3 days of focused implementation

---

## 📚 REFERENCES

1. HipKittens Paper: arXiv 2511.08083
2. ROCm Blog: CDNA4 FP8 GEMM (March 2026)
3. AMD CDNA4 Whitepaper
4. Composable Kernel Examples (ROCm)

**Status**: Implementation in progress...
