---
title: AMD GPU Kernel Optimization Pattern
pattern_type: gpu_optimization
domain: amd_speedrun
applicability: [popcorn-cli, load_inline, hip_kernels]
cortex_weight: 0.95
---

# Pattern: AMD GPU Kernel Optimization

## Context
Optimizing GPU kernels for AMD MI355X (gfx950) using popcorn-cli and load_inline for maximum performance.

## Problem
- High-level Python APIs too slow for competitive kernel optimization
- Need direct GPU kernel programming for breakthrough performance
- Must follow specific submission format for popcorn-cli

## Solution

### Pattern 1: load_inline Native Kernel
```python
import os
os.environ['PYTORCH_ROCM_ARCH'] = 'gfx942'
os.environ['CXX'] = 'clang++'

import torch
from torch.utils.cpp_extension import load_inline
from task import input_t, output_t

HIP_SRC = r"""
#include <hip/amd_detail/amd_hip_bf16.h>

__global__ void optimized_kernel(...) {
    // Direct GPU kernel implementation
}

void launch_op(torch::Tensor input, ...) {
    // Launch configuration
}
"""

module = load_inline(
    name='native_module',
    cpp_sources=[...],
    cuda_sources=[HIP_SRC],
    functions=['launch_op'],
    extra_cuda_cflags=["--offload-arch=gfx942", "-O3"],
)

def custom_kernel(data: input_t) -> output_t:
    return module.launch_op(data)
```

### Pattern 2: 8-Wave Ping-Pong
Key for CDNA3/CDNA4 performance:
- 8 waves per block, 2 waves per SIMD
- Alternate compute/memory phases
- Direct global-to-LDS loads
- MFMA with block scaling

```cpp
// In HIP kernel
__global__ void gemm_8wave(...) {
    int wave_id = __builtin_amdgcn_mbcnt_hi(...);
    bool is_compute = (wave_id < 4);
    
    if (is_compute) {
        // Do MFMA computation
    } else {
        // Do global-to-LDS loads
    }
    __builtin_amdgcn_s_barrier();
}
```

### Pattern 3: Environment Setup
```python
# Order matters!
import os
os.environ['PYTORCH_ROCM_ARCH'] = 'gfx942'  # Before torch!
os.environ['CXX'] = 'clang++'

import torch  # After env setup
```

## Consequences

### Pros
- Native GPU performance (2-5x speedup)
- Direct hardware access (MFMA, LDS)
- Competitive with hand-written kernels

### Cons
- Requires C++/HIP knowledge
- Compilation overhead (cached after first run)
- Platform-specific (gfx942 for MI355X)

## Known Uses
- MoE optimization: 93.4μs (using load_inline)
- Future GEMM: Target 7.651μs (need 8-wave)
- Future MLA: Target 19.484μs

## Related Patterns
- [[8-wave-ping-pong]] - Scheduling pattern
- [[mfma-block-scaling]] - CDNA4 instruction usage
- [[global-to-lds]] - Memory optimization

## References
- /home/mike-anderson/dev/cohezion/amd_202602/*/.popcorn/skills/
- IMPLEMENTATION_8WAVE_PINGPONG.md

---
**Pattern Status**: Validated (MoE 93.4μs)  
**Platform**: Cohezion Cortex  
**Last Updated**: 2026-04-03
