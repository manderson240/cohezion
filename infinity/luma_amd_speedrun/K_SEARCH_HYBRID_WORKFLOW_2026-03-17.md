# K-Search Hybrid Workflow

**Created:** 2026-03-17  
**Status:** READY FOR USE  
**Mode:** LLM planning + manual HIP implementation

---

## Overview

Hybrid K-Search combines:
- **K-Search planning:** Intent selection, evaluation, tree updates
- **Manual HIP implementation:** You write the kernel code
- **Popcorn CLI evaluation:** Automated testing + benchmarking

**Best for:**
- Complex optimizations requiring expert knowledge
- CDNA4-specific tuning (MFMA, LDS, wave64)
- When LLM code generation quality is insufficient

---

## Workflow

### Iteration Loop

```
┌─────────────────────────────────────────────────────────────┐
│ 1. K-Search Selects Intent                                  │
│    - From frontier: highest priority                        │
│    - Example: "8-wave ping-pong scheduling"                 │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│ 2. Human Implements HIP Kernel                              │
│    - Edit fused_mxfp4_gemm.hip                              │
│    - Add 8-wave ping-pong pattern                           │
│    - Save as gemm_8wave_pingpong.hip                        │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│ 3. K-Search Evaluates                                       │
│    - Compile (hiprtc/hipcc)                                 │
│    - Correctness test (4/4 pass)                            │
│    - Benchmark (geomean µs)                                 │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│ 4. World Model Updates Tree                                 │
│    - Insert child refinements                               │
│    - Update priorities                                      │
│    - Prune failed branches                                  │
└─────────────────────────────────────────────────────────────┘
```

---

## Usage

### Initialize Search Tree
```bash
cd /home/mike-anderson/dev/cohezion
python3 -m k_search.search_tree
# Creates 5 initial GEMM hypotheses
```

### Run Hybrid Optimization
```bash
python3 -m k_search.hybrid_run \
  --kernel gemm \
  --budget 10 \
  --hip-dir kernels/mxfp4-mm
```

### Manual Implementation Workflow

**Iteration 1:**
1. K-Search selects: `gemm_fused_quant` (p=0.9)
2. You provide: `fused_mxfp4_gemm.hip` (already implemented)
3. K-Search evaluates: Popcorn CLI test + benchmark
4. Result: ~14.1 µs
5. Tree updates: Insert children (`gemm_fused_quant_8wave`, etc.)

**Iteration 2:**
1. K-Search selects: `gemm_8wave_pingpong` (p=0.85)
2. You implement: Add 8-wave pattern to HIP kernel
3. Save as: `kernels/mxfp4-mm/gemm_8wave_pingpong.hip`
4. K-Search evaluates
5. Result: ~12.5 µs (12% improvement)
6. Tree updates: Boost priority, insert refinements

**Continue until:**
- Budget exhausted (10 iterations)
- Target achieved (<10 µs)
- Frontier empty

---

## Search Tree State

### Initial Frontier (GEMM)
| Node ID | Intent | Priority | Status |
|---------|--------|----------|--------|
| `gemm_fused_quant` | Fused quant+GEMM | 0.9 | OPEN |
| `gemm_8wave_pingpong` | 8-wave ping-pong | 0.8 | OPEN |
| `gemm_lds_swizzle` | LDS swizzle XOR | 0.75 | OPEN |
| `gemm_direct_lds` | Direct global→LDS | 0.7 | OPEN |
| `gemm_mfma_tuned` | MFMA tile tuning | 0.65 | OPEN |

### After Iteration 1 (Example)
| Node ID | Status | Latency | Children |
|---------|--------|---------|----------|
| `gemm_fused_quant` | CLOSED | 14.1 µs | `gemm_fused_quant_8wave`, `gemm_fused_quant_lds` |
| `gemm_8wave_pingpong` | OPEN | — | — |
| `gemm_lds_swizzle` | OPEN | — | — |
| ... | ... | ... | ... |

---

## HIP Implementation Templates

### Optimization Intents

#### 1. Fused Quant+GEMM (Already Implemented)
```cpp
// fused_mxfp4_gemm.hip
__global__ void fused_mxfp4_gemm(...) {
    // Inline FP4 quantization
    quantize_bf16_to_fp4(A[idx], scale_exp, fp4_val);
    
    // MFMA compute
    exec_mfma_fp4(c_frag, a_reg, b_reg);
}
```

#### 2. 8-Wave Ping-Pong (To Implement)
```cpp
// gemm_8wave_pingpong.hip
__global__ void fused_mxfp4_gemm_v2(...) {
    const int wave_id = threadIdx.x / 64;
    const int wave_m = wave_id / 4;
    const int wave_n = wave_id % 4;
    
    // Alternate memory waves (0-3) with compute waves (4-7)
    if (wave_id < 4) {
        // Memory wave: Load LDS
        load_a_fragment(...);
    } else {
        // Compute wave: MFMA
        exec_mfma_fp4(...);
    }
    
    __builtin_amdgcn_s_barrier();
    __builtin_amdgcn_sched_barrier(0);
}
```

#### 3. LDS Swizzle (To Implement)
```cpp
// gemm_lds_swizzle.hip
__device__ __forceinline__ int swizzle_col(int row, int col) {
    const int pair = (row >> 1) & 7;
    const int perm = pair ^ (((pair >> 1) ^ (pair >> 2)) & 1);
    const int mask = perm << 4;
    return col ^ mask;  // XOR remap
}

// Usage in kernel
int swizzled_idx = swizzle_col(row, col);
value = lds[swizzled_idx];
```

#### 4. Direct Global→LDS (To Implement)
```cpp
// gemm_direct_lds.hip
using i32x4 = int32_t __attribute__((ext_vector_type(4)));

extern "C" __device__ void llvm_amdgcn_raw_buffer_load_lds(
    i32x4 rsrc, uint32_t __attribute__((address_space(3))) * lds_ptr,
    int size, int voffset, int soffset, int offset, int aux
) __asm("llvm.amdgcn.raw.buffer.load.lds");

// Usage
i32x4 srsrc = make_srsrc(global_ptr, range_bytes);
llvm_amdgcn_raw_buffer_load_lds(srsrc, lds_ptr, 16, tid*4, 0, 0, 0);
```

---

## Expected Performance

### K-Search Projections (GEMM)
| Iteration | Intent | Expected Latency | Improvement |
|-----------|--------|-----------------|-------------|
| 1 | Fused quant+GEMM | 14.1 µs | Baseline |
| 2 | +8-wave ping-pong | 12.5 µs | -11% |
| 3 | +LDS swizzle | 11.8 µs | -6% |
| 4 | +Direct LDS | 11.2 µs | -5% |
| 5 | +MFMA tuning | 10.8 µs | -4% |
| **Final** | **Combined** | **~10 µs** | **-29%** |

**Target:** 9.7 µs (leader: 9.671 µs)

---

## Files

| Path | Purpose |
|------|---------|
| `k_search/hybrid_run.py` | Hybrid workflow orchestrator |
| `k_search/search_tree.py` | Search tree data structures |
| `k_search/world_model.py` | LLM prompts (CDNA4 knowledge) |
| `k_search/evaluator_rocm.py` | Popcorn CLI backend |
| `k_search/programs/` | Generated HIP kernels |
| `k_search/search_state.json` | Persisted search state |
| `kernels/mxfp4-mm/*.hip` | Manual HIP implementations |

---

## Troubleshooting

### Issue: "Frontier empty"
**Cause:** All nodes pruned (failed evaluation)
**Fix:** Add new intents via `tree.insert_child()`

### Issue: "Compilation failed"
**Cause:** HIP syntax error or missing includes
**Fix:** Verify `#include <hip/hip_runtime.h>` present

### Issue: "Correctness failed"
**Cause:** Kernel output mismatch vs reference
**Fix:** Check FP4 e2m1 encoding, E8M0 scale computation

### Issue: "Benchmark timeout"
**Cause:** Popcorn CLI exceeded 300s limit
**Fix:** Retry during off-peak hours (queue pressure)

---

## Integration with Existing HIP Code

### Current Files
- `fused_mxfp4_gemm.hip` → `gemm_fused_quant` parent
- `submission_hip_fused.py` → Evaluator wrapper
- `HIP_CPP_FUSED_GEMM_2026-03-17.md` → Documentation

### Next Steps
1. **Implement 8-wave ping-pong** in `gemm_8wave_pingpong.hip`
2. **Test via Popcorn CLI:** `--mode test` then `--mode benchmark`
3. **Run hybrid iteration:** `python3 -m k_search.hybrid_run --budget 1`
4. **Review tree updates:** Check `search_state.json`

---

## References

1. **K-Search Paper:** arxiv 2602.19128
2. **AMD FP8 GEMM Blog:** https://rocm.blogs.amd.com/software-tools-optimization/cdna4-gemm-kernels/README.html
3. **CDNA4 ISA:** https://www.amd.com/content/dam/amd/en/documents/instinct-tech-docs/instruction-set-architectures/amd-instinct-cdna4-instruction-set-architecture.pdf

---

**Status:** READY FOR EXECUTION

**Next:** Run first hybrid iteration with existing `fused_mxfp4_gemm.hip`.
