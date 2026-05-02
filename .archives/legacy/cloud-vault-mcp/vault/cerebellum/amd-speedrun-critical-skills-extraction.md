---
title: AMD Speedrun - Critical Skills and Guardrails Extraction
status: extracted
date: 2026-04-03
tags: [amd, speedrun, popcorn-cli, load_inline, skills, guardrails, gpu, optimization]
cortex_nexus: true
manifold_ready: true
---

# AMD Speedrun - Critical Skills Extraction

**Source**: popcorn-cli setup project directories (amd_202602/*/)  
**Extraction Date**: 2026-04-03  
**Status**: Critical knowledge for Cohezion platform

---

## 🎯 CRITICAL GUARDRAILS (MUST FOLLOW)

### Guardrail 1: Function Signature
```python
def custom_kernel(data: input_t) -> output_t:
```
**Critical**: Must match exactly or submission fails with ImportError

### Guardrail 2: load_inline Location
- **MUST** be at module level (outside custom_kernel)
- **MUST NOT** be inside custom_kernel (causes recompilation every call)

### Guardrail 3: Environment Variables (Order Critical!)
```python
import os
os.environ['PYTORCH_ROCM_ARCH'] = 'gfx942'  # MUST be before torch import
os.environ['CXX'] = 'clang++'               # MUST be before torch import

import torch  # ONLY after env vars set!
```

### Guardrail 4: POPCORN Directives (Recommended)
```python
#!POPCORN leaderboard amd-moe-mxfp4
#!POPCORN gpu MI355X
```

---

## 🔥 CRITICAL SKILL: Load Inline Native Code

### FULL WORKING TEMPLATE

```python
import os
os.environ['PYTORCH_ROCM_ARCH'] = 'gfx942'
os.environ['CXX'] = 'clang++'

import torch
from torch.utils.cpp_extension import load_inline
from task import input_t, output_t

HIP_SRC = r"""
#include <hip/amd_detail/amd_hip_bf16.h>

__global__ void my_kernel(const float* input, float* output, int N) {
    int idx = blockIdx.x * blockDim.x + threadIdx.x;
    if (idx < N) {
        output[idx] = input[idx];
    }
}

void my_op(torch::Tensor input, torch::Tensor output) {
    int N = input.numel();
    const int threads = 256;
    const int blocks = (N + threads - 1) / threads;
    my_kernel<<<blocks, threads>>>(
        input.data_ptr<float>(),
        output.data_ptr<float>(),
        N
    );
}
"""

CPP_SRC = """
void my_op(torch::Tensor input, torch::Tensor output);
"""

# Module-level compilation (CRITICAL!)
module = load_inline(
    name='my_module',
    cpp_sources=[CPP_SRC],
    cuda_sources=[HIP_SRC],
    functions=['my_op'],
    verbose=True,
    extra_cuda_cflags=["--offload-arch=gfx942", "-std=c++20"],
)

def custom_kernel(data: input_t) -> output_t:
    input, output = data
    module.my_op(input, output)
    return output
```

### Key Parameters
- `name`: Unique module name per submission
- `cpp_sources`: C++ headers (function declarations)
- `cuda_sources`: CUDA/HIP kernel code
- `functions`: Exposed function names (must match C++ signatures)
- `verbose=True`: Essential for debugging
- `extra_cuda_cflags`: `--offload-arch=gfx942` for MI355X

---

## 📊 SKILL USAGE ANALYSIS

### MoE (93.4μs)
- ✅ **Using load_inline** for input prep
- ✅ **Has correct signature** custom_kernel(data: input_t) -> output_t
- ✅ **Module-level compilation**
- **Result**: Working submission

### MLA/GEMM (Broken)
- ❌ **Missing correct signature** (had class.forward instead)
- ❌ **Not using load_inline** fully
- ❌ **ImportError**: cannot import name 'custom_kernel'

---

## 🎯 REAL RANK 1 TARGETS (Verified)

| Kernel | Rank 1 | Our Best | Gap |
|--------|--------|----------|-----|
| MoE | 70.470μs | 93.4μs | +23μs (32%) |
| GEMM | 7.651μs | ~18.4μs | +11μs (140%) |
| MLA | 19.484μs | Unknown | Unknown |

**Critical Insight**: 93.4μs is NOT Rank 1 - we are 32% behind!

---

## 🚀 RECOMMENDED WORKFLOW

1. **Ensure POPCORN directives** at top of submission.py
2. **Set env vars** before any torch import
3. **Implement custom_kernel** with exact signature
4. **Use load_inline at module level** for native code
5. **Test mode**: Verify correctness
6. **Benchmark mode**: Get timing
7. **Leaderboard mode**: Submit if benchmark improves

---

## 📁 FILE LOCATIONS

**Source Templates**:
- `amd_202602/moe-mxfp4/submission.py` - Working MoE (93.4μs)
- `amd_202602/mxfp4-mm/submission.py` - GEMM template
- `amd_202602/mixed-mla/submission.py` - MLA template

**Skills**:
- `.popcorn/skills/popcorn-submission-workflow/SKILL.md`
- `.popcorn/skills/load-inline-native-code/SKILL.md`

---

## 🔗 RELATED PATTERNS

- [[amd-speedrun-strategy]] - Overall strategy
- [[IMPLEMENTATION_8WAVE_PINGPONG]] - 8-wave optimization
- [[popcorn-cli-setup]] - Setup process

---

**Extracted for Cohezion Platform Learning**  
**Status**: cortex_nexus ready | manifold_ready
