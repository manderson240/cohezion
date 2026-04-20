---
name: amd-load-inline-hip-kernel
description: |
  AMD GPU load_inline Kernel Development Skill for MI355X (gfx950).
  Use when: (1) writing custom HIP kernels via load_inline for Popcorn CLI competitions,
  (2) the aiter API ceiling is reached and custom MFMA intrinsics are needed,
  (3) someone says "load_inline is blocked" — it is NOT (ctypes dispatch is, load_inline works).
  VERIFIED Session 95: load_inline compiles and runs on Popcorn runners with MFMA FP4 intrinsics.
  CRITICAL: Use B_q (standard packed), NOT B_shuffle (CK-specific format).
author: Claude Code
version: 2.0.0
---

# AMD GPU load_inline Kernel Development Skill

## Purpose
Develop custom HIP kernels using `torch.utils.cpp_extension.load_inline` for AMD MI355X (gfx950) GPU competitions.

## When to Use
- Developing custom GEMM kernels for MXFP4/MXF8 formats
- Optimizing kernels beyond library API ceilings
- Target is rank 1 or near-rank-1 performance

## CRITICAL CORRECTION (Session 95, 2026-04-05)

**load_inline IS NOT BLOCKED on Popcorn runners.**

Previous sessions (89-90) declared it "blocked" but they tested `ctypes` HIP dispatch
(hipModuleLaunchKernel) which IS blocked by stream isolation. `torch.utils.cpp_extension.load_inline()`
is a completely different mechanism — it uses PyTorch's ROCm compilation pipeline.

**Verified evidence:**
- MFMA v1 kernel: 4/4 tests passed, max error 0.0
- Compilation time: ~60-90s on runner (fits in benchmark timeout)
- MFMA FP4 32x32x64 intrinsic produces correct results

## Key Insights (Session 95)

1. **Use B_q, NOT B_shuffle** — B_shuffle is CK-tile-coalesced (16x16 permutation), incompatible with MFMA lane mapping
2. **Unshuffle B_scale** — Use `e8m0_unshuffle()` to convert B_scale_sh to linear [N, K/32]
3. **Don't shuffle A_scale** — `dynamic_mxfp4_quant()` returns linear scales, no shuffle needed
4. **LDS hurts for small M** — sync overhead dominates when M<32 (30.9µs vs 26.4µs without LDS)
5. **Ollama can't write these** — 0/4 Ollama-generated MFMA kernels passed correctness

## Pattern

```python
from torch.utils.cpp_extension import load_inline
from task import input_t, output_t

CPP_WRAPPER = """
void my_kernel(
    torch::Tensor A,
    torch::Tensor B,
    torch::Tensor C
);
"""

HIP_SRC = r"""
#include <hip/hip_runtime.h>
#include <hip/amd_detail/amd_hip_bf16.h>

__global__ void my_kernel(
    const __hip_bfloat16* A,
    const __hip_bfloat16* B,
    __hip_bfloat16* C,
    int M, int N, int K
) {
    // Your kernel code here
}

void my_kernel(torch::Tensor A, torch::Tensor B, torch::Tensor C) {
    int M = A.size(0);
    int N = B.size(0);
    int K = A.size(1);
    
    dim3 blocks((M + 15) / 16, (N + 15) / 16);
    dim3 threads(16, 16);
    
    my_kernel<<<blocks, threads>>>(
        (const __hip_bfloat16*)A.data_ptr(),
        (const __hip_bfloat16*)B.data_ptr(),
        (__hip_bfloat16*)C.data_ptr(),
        M, N, K
    );
}
"""

os.environ["CXX"] = "clang++"

module = load_inline(
    name="my_kernel",
    cpp_sources=[CPP_WRAPPER],
    cuda_sources=[HIP_SRC],  # AMD auto-converts CUDA to HIP!
    functions=["my_kernel"],
    extra_cuda_cflags=["--offload-arch=gfx950", "-std=c++20", "-O3"],
)

def custom_kernel(data: input_t) -> output_t:
    A, B = data
    C = torch.empty((A.size(0), B.size(0)), dtype=torch.bfloat16, device=A.device)
    module.my_kernel(A, B, C)
    return C
```

## FP4 E2M1 Format

```python
# Values: 0, 0.5, 1.0, 1.5, 2.0, 3.0, 4.0, 6.0 (positive and negative)
fp4_vals = [0.0, 0.5, 1.0, 1.5, 2.0, 3.0, 4.0, 6.0,  # positive
           -0.0, -0.5, -1.0, -1.5, -2.0, -3.0, -4.0, -6.0]  # negative

# In HIP:
__device__ inline float fp4_to_f32(uint8_t fp4) {
    float vals[16] = {0.0f, 0.5f, 1.0f, 1.5f, 2.0f, 3.0f, 4.0f, 6.0f,
                      -0.0f, -0.5f, -1.0f, -1.5f, -2.0f, -3.0f, -4.0f, -6.0f};
    return vals[fp4 & 0xF];
}

__device__ inline float unpack_fp4(uint8_t packed, int idx) {
    uint8_t nibble = (idx == 0) ? (packed & 0xF) : ((packed >> 4) & 0xF);
    return fp4_to_f32(nibble);
}
```

## E8M0 Scale Format

```python
# E8M0: f32 = 2^(e8m0 - 127)
__device__ inline float e8m0_to_f32(uint8_t e8m0) {
    if (e8m0 == 0) return 0.0f;
    if (e8m0 == 255) return 0.0f;
    return exp2f((float)((int)e8m0 - 127));
}
```

## Official Reference Templates
- GEMM: https://github.com/gpu-mode/reference-kernels/blob/main/problems/amd/fp8-mm/template-hip.py
- MLA: https://github.com/gpu-mode/reference-kernels/blob/main/problems/amd/mla-decode/submission.py
- MoE: https://github.com/gpu-mode/reference-kernels/blob/main/problems/amd/moe/submission.py

## Key Optimizations

### Lifted Scales
Apply scale ONCE per block, not per element:
```cpp
for (int kb = 0; kb < k_blocks; kb++) {
    float block_result = 0.0f;
    for (int kk = 0; kk < 32; kk++) {
        // No scale here!
        block_result += a_val * b_val;
    }
    // Scale ONCE per block
    result += block_result * a_scale * b_scale;
}
```

### ROCWMMA for MFMA
```cpp
#include <rocwmma/rocwmma.hpp>
using namespace rocwmma;
// Use native MFMA instructions for MI355X
```

## Common Issues

1. **Compilation fails**: Check `--offload-arch=gfx950` flag
2. **Wrong results**: Verify FP4 unpacking and E8M0 conversion
3. **Slow performance**: Ensure scales are lifted outside inner loop

## Files
- `kernels/mxfp4-mm/submission_loadinline_direct.py` - Working load_inline GEMM
- `kernels/mxfp4-mm/submission_loadinline_rocwmma.py` - ROCWMMA version
