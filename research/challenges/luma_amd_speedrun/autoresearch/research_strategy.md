# Research Strategy (Human-Editable)

This file guides the LLM world model's optimization direction.
Edit priorities and dead ends to steer overnight runs.
The autoresearch loop reads this before each LLM call.

## BREAKTHROUGH: load_inline Custom HIP Kernels

**DISCOVERED 2026-03-29**: Official `template-hip.py` shows `load_inline` WORKS on runners!

This is how rank 1 achieves 1µs on GEMM - NOT using Python API at all!

```python
from torch.utils.cpp_extension import load_inline

module = load_inline(
    name='fp8_mm',
    cpp_sources=[CPP_WRAPPER],
    cuda_sources=[HIP_SRC],  # AMD auto-converts CUDA→HIP!
    functions=['fp8_mm'],
    extra_cuda_cflags=["--offload-arch=gfx950", "-std=c++20"],
)
```

### Key Patterns from Official Templates

1. **Block-wise GEMM with lifted scales**: Scales OUTSIDE inner loop
2. **Pre-allocated output**: Write directly to `c` parameter
3. **Native HIP types**: `__hip_fp8_e4m3_fnuz*`, `__hip_bfloat16*`
4. **MFMA instructions**: AMD native INT8/FP8 matrix multiply

## Current Focus

- **GEMM** (HIGHEST PRIORITY): `load_inline` custom HIP kernel
  - Target: 1-5µs (rank 1 is 1.000µs!)
  - Use block-wise GEMM with lifted scales
  
- **MLA** (HIGH PRIORITY): `load_inline` custom HIP kernel  
  - Target: 26-40µs (rank 1 is 26.812µs)
  - FlashAttention-style single-pass
  
- **MoE** (MAINTENANCE): Already competitive at ~110µs (rank 1 is 109.793µs)

## Dead Ends (Do NOT retry)

- ~~Custom HIP compilation: BLOCKED~~ - **FALSE: load_inline works!**
- `gemm_afp4wfp4`: KeyError 'float4_e2m1fn_x2' — MXFP4 not supported in this API
- `mla_decode_fwd` with MXFP4 KV cache: "only support head_size == KV.size(3) for now"
- `get_torch_quant` as drop-in for `get_triton_quant`: produces wrong GEMM results
- `fmoe_g1u1` for 32-expert shapes: produces NaN
- `torch.compile` on ROCm 7.1: blocked by `auto_functionalized_v2`
- `fast_mode=True` for MLA metadata: SLOWER on MI355X (verified Phase 17)
- Origami XCD remapping for non-divisible tiles: silent wrong results

## Leaderboard Targets

| Kernel | Our Best | Rank 1 | Gap | Path Forward |
|--------|----------|---------|-----|--------------|
| GEMM | ~21.9µs | 1.000µs | 22× | **load_inline custom HIP** |
| MLA | ~70µs | 26.812µs | 2.6× | **load_inline custom HIP** |
| MoE | ~110µs | 109.793µs | ~1× | Maintenance only |

## load_inline Template Structure

```python
from torch.utils.cpp_extension import load_inline

CPP_WRAPPER = """
void custom_kernel(torch::Tensor a, torch::Tensor b, torch::Tensor c, ...);
"""

HIP_SRC = """
#include <hip/amd_detail/amd_hip_fp8.h>
#include <hip/amd_detail/amd_hip_bf16.h>

__global__ void kernel(...) {
    // Your implementation
}
"""

module = load_inline(
    name='custom_kernel',
    cpp_sources=[CPP_WRAPPER],
    cuda_sources=[HIP_SRC],
    functions=['custom_kernel'],
    extra_cuda_cflags=["--offload-arch=gfx950", "-std=c++20"],
)

def custom_kernel(data):
    a, b, c = data
    module.custom_kernel(a, b, c)
    return c
```

## Reference: AMD MI355X (gfx950) Resources

- MFMA instruction set: Native INT8/FP8 matrix multiply
- Block size: 128 threads/wavefront
- 8 XCD (compute dies) topology

## Exploration Priorities

1. **GEMM load_inline**: Block-wise with lifted scales (HIGHEST)
2. **MLA load_inline**: FlashAttention-style single-pass (HIGH)
3. **MoE load_inline**: Fused permutation + persistent tiles (MAINTENANCE)
