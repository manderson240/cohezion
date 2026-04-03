# 🔥 CRITICAL FILE EXTRACTION - Skills & Agent Definitions
**Source**: amd_202602/*/ (.popcorn/skills/ and AGENTS.md)

---

## 🎯 CRITICAL GUARDRAILS (From Skills)

### Guardrail 1: Function Signature
**CRITICAL**: Must match exactly:
```python
def custom_kernel(data: input_t) -> output_t:
```

**Our MoE has this** ✅ → Works (93.4μs)

**Our MLA/GEMM didn't have this** ❌ → Failed

---

### Guardrail 2: load_inline Location
**CRITICAL**: Must be at **module level** (outside custom_kernel)

**Wrong**:
```python
def custom_kernel(data):
    module = load_inline(...)  # ❌ Compiles every call!
```

**Right**:
```python
module = load_inline(...)  # ✅ Compiles once at import

def custom_kernel(data):
    module.my_op(...)
```

---

### Guardrail 3: Environment Variables
**CRITICAL**: Set BEFORE importing torch

```python
import os
os.environ['PYTORCH_ROCM_ARCH'] = 'gfx942'  # MI355X
os.environ['CXX'] = 'clang++'

import torch  # Only AFTER setting env vars!
```

---

### Guardrail 4: POPCORN Directives
**Recommended** (not required, but helps):
```python
#!POPCORN leaderboard amd-moe-mxfp4
#!POPCORN gpu MI355X
```

Our MoE is **missing these but still works**.

---

## 🔥 CRITICAL SKILL: Load Inline Native Code

### FULL TEMPLATE (From SKILL.md)

```python
import os
# MUST set BEFORE importing torch
os.environ['PYTORCH_ROCM_ARCH'] = 'gfx942'
os.environ['CXX'] = 'clang++'

import torch
from torch.utils.cpp_extension import load_inline
from task import input_t, output_t

# HIP kernel source
HIP_SRC = """
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

# C++ bindings
CPP_SRC = """
void my_op(torch::Tensor input, torch::Tensor output);
"""

# Compile at module level
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

| Parameter | Purpose | Value |
|-----------|---------|-------|
| `name` | Module name | Unique per submission |
| `cpp_sources` | C++ headers | Function declarations |
| `cuda_sources` | HIP/CUDA code | Actual kernel |
| `functions` | Exposed functions | Must match C++ signatures |
| `verbose` | Debug output | True for debugging |
| `extra_cuda_cflags` | Compiler flags | `--offload-arch=gfx942` |

---

## 📋 AGENT DEFINITIONS

### Agent Capabilities

From `AGENTS.md`:

1. **Skill: popcorn-submission-workflow**
   - Registration (`popcorn register`)
   - Submission modes (test/benchmark/leaderboard)
   - File directives
   - Submission inspection (`submissions list/show`)

2. **Skill: load-inline-native-code**
   - Writing CUDA kernels
   - Writing HIP kernels
   - Using `torch.utils.cpp_extension.load_inline()`

### How Agents Should Use These Skills

1. **Progressive disclosure**: Read only relevant parts as needed
2. **Keep workspace aligned**: Use `popcorn setup` structure
3. **Follow guardrails**: Check all critical requirements

---

## 🎯 APPLYING TO OUR KERNELS

### MoE (93.4μs → Need 70.47μs)

**Current**: Uses load_inline for input prep only
**Gap**: Need custom kernel for full MoE computation

**Optimization path**:
1. Keep current load_inline for input prep
2. Add second load_inline for optimized GEMM (8-wave)
3. Or: Use load_inline to call pre-compiled CK kernels directly

**Template to extend**:
```python
# Already have:
_module = load_inline(name="moe_prep_v1", ...)

# Add:
_module_gemm = load_inline(name="moe_gemm_8wave", ...)
```

---

### GEMM (Unknown → Need 7.651μs)

**Current**: using high-level aiter API
**Gap**: Need custom kernel

**Implementation path**:
1. Use HIP template from skill
2. Implement 8-wave ping-pong pattern
3. Direct global-to-LDS loads
4. MFMA with block scaling

**Template to start from**:
```python
import os
os.environ['PYTORCH_ROCM_ARCH'] = 'gfx942'
os.environ['CXX'] = 'clang++'

import torch
from torch.utils.cpp_extension import load_inline
from task import input_t, output_t

HIP_SRC = r"""
#include <hip/amd_detail/amd_hip_bf16.h>

// 8-wave ping-pong GEMM kernel
__global__ void gemm_8wave(
    const at::BFloat16* A,
    const at::BFloat16* B,
    at::BFloat16* C,
    int M, int N, int K
) {
    // Implementation from our research:
    // - 8 waves (2 per SIMD)
    // - Direct global-to-LDS
    // - MFMA with block scaling
    // - Double buffering
}

void gemm_op(torch::Tensor A, torch::Tensor B, torch::Tensor C, ...) {
    // Launch configuration
}
"""

# ... rest of template ...
```

---

### MLA (Unknown → Need 19.484μs)

**Current**: Not working
**Gap**: Need working submission first

**Implementation path**:
1. Use template from amd_202602/mixed-mla/submission.py
2. May need load_inline for optimization
3. Focus on attention kernel efficiency

**Template to start from**:
```python
# From amd_202602/mixed-mla/submission.py
def custom_kernel(data: input_t) -> output_t:
    q, kv_data, qo_indptr, kv_indptr, config = data
    # Use aiter.mla_decode_fwd
    # May optimize with load_inline later
```

---

## 🚀 IMMEDIATE ACTIONS

### Step 1: Apply Templates

Copy the **official templates** from popcorn setup:

```bash
cp /home/mike-anderson/dev/cohezion/amd_202602/mixed-mla/submission.py \
   /home/mike-anderson/dev/cohezion/.worktrees/luma-breakthrough-sprint/luma_speedrun/amd-mixed-mla/

cp /home/mike-anderson/dev/cohezion/amd_202602/mxfp4-mm/submission.py \
   /home/mike-anderson/dev/cohezion/.worktrees/luma-breakthrough-sprint/luma_speedrun/amd-mxfp4-mm/
```

### Step 2: Test Immediately

```bash
# MLA
cd /home/mike-anderson/dev/cohezion/amd_202602/mixed-mla
popcorn submit submission.py --mode test --gpu MI355X --leaderboard amd-mixed-mla

# GEMM
cd /home/mike-anderson/dev/cohezion/amd_202602/mxfp4-mm  
popcorn submit submission.py --mode test --gpu MI355X --leaderboard amd-mxfp4-mm
```

### Step 3: Optimize with Skills

1. **Read skill files** when implementing (progressive disclosure)
2. **Follow guardrails** (env vars, function signatures, etc.)
3. **Use load_inline** for breakthrough performance
4. **Test → Benchmark → Leaderboard** (workflow skill)

---

## 📚 COMPLETE FILE MAP

### Critical Source Files
```
amd_202602/
├── moe-mxfp4/
│   ├── submission.py                    ← Current MoE (93.4μs) - using load_inline ✓
│   ├── AGENTS.md                        ← Agent instructions
│   └── .popcorn/
│       ├── setup.json                   ← Configuration
│       └── skills/
│           ├── popcorn-submission-workflow/SKILL.md  ← Submission process
│           └── load-inline-native-code/SKILL.md        ← Native kernel template
├── mxfp4-mm/
│   ├── submission.py                    ← GEMM template
│   └── .popcorn/skills/...              ← Same skills
└── mixed-mla/
    ├── submission.py                    ← MLA template
    └── .popcorn/skills/...              ← Same skills
```

### Our Working Directories
```
luma_speedrun/
├── amd-moe-mxfp4/
│   └── submission.py                    ← Uses load_inline ✓
├── amd-mxfp4-mm/
│   ├── submission.py                    ← Broken ❌
│   └── submission_template.py           ← From popcorn ✓
└── amd-mixed-mla/
    ├── submission.py                    ← Broken ❌
    └── submission_template.py           ← From popcorn ✓
```

---

## ✅ SKILL USAGE CHECKLIST

- [ ] Read `popcorn-submission-workflow/SKILL.md` → Understand workflow
- [ ] Read `load-inline-native-code/SKILL.md` → Get HIP templates
- [ ] Set `PYTORCH_ROCM_ARCH=gfx942` before torch import
- [ ] Set `CXX=clang++` before torch import
- [ ] Use `custom_kernel(data: input_t) -> output_t` signature
- [ ] Call `load_inline` at module level (not inside custom_kernel)
- [ ] Test → Benchmark → Leaderboard submission order
- [ ] Check submissions with `popcorn submissions list/show`

---

**Conclusion**: 
- **We HAVE the skills** (in amd_202602/)
- **We ARE using workflow skill** ✓
- **We ARE using load_inline for MoE** ✓
- **We NEED to use skills for MLA/GEMM** → Copy templates and optimize

**Next step**: Copy templates and test immediately!
