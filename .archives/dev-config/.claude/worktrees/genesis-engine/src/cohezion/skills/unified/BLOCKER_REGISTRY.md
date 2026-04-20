# AMD Research Blocker Registry

**Registry Version:** 2.0.1
**Last Updated:** 2026-03-28
**Source:** Session 77-79 AMD Speedrun Research

## Overview

This registry documents blockers and limitations encountered during AMD GPU kernel optimization research. These blockers are tracked to facilitate resolution and prevent duplicate investigation.

## Current Blockers

### 1. AITER Installation Blocker

| Field | Value |
|-------|-------|
| **ID** | BLOCKER-001 |
| **Name** | AITER Not Installed on Runner |
| **Category** | Dependency/Environment |
| **Severity** | High |
| **Status** | Open |

**Description:**
AITER (AI Tensor Engine for ROCm) is not pre-installed on the runner environment, preventing direct usage of `aiter.fused_moe` and other optimized kernels.

**Impact:**
- Cannot use AITER's `fused_moe` backend directly
- Must fall back to CK-Tile or Triton implementations
- Performance disadvantage vs competitors using AITER

**Workarounds:**
1. Install AITER from source: `pip install git+https://github.com/ROCm/aiter.git`
2. Use CK-Tile as alternative: `/opt/rocm/include/ck_tile/`
3. Use Triton-based MoE implementation

**Resolution Path:**
- Requires ROCm 6.x+ compatible environment
- May need sudo access for system-wide installation
- Alternative: Use containerized ROCm environment

---

### 2. PyTorch C++ Extension Compiler

| Field | Value |
|-------|-------|
| **ID** | BLOCKER-002 |
| **Name** | PyTorch C++ Extension Requires hipcc |
| **Category** | Build/Compilation |
| **Severity** | High |
| **Status** | Open |

**Description:**
Compiling PyTorch C++ extensions for AMD GPUs requires `hipcc` (HIP Compiler), not standard GCC/Clang. This is a hard requirement for CK-Tile integration.

**Impact:**
- Cannot use `torch.utils.cpp_extension.load` with default compiler
- CK-Tile headers require HIP-specific intrinsics
- Build scripts must be modified for AMD targets

**Workarounds:**
```python
from torch.utils.cpp_extension import load

ck_tile_moe = load(
    name="ck_tile_moe",
    sources=["ck_tile_moe_kernel.cpp"],
    extra_cflags=["-O3"],
    extra_include_paths=["/opt/rocm/include"],
    extra_ldflags=["-L/opt/rocm/lib", "-lamdhip64"],
    verbose=True
)
```

**Resolution Path:**
- Ensure `hipcc` is in PATH: `export PATH=/opt/rocm/bin:$PATH`
- Set `CXX` environment variable: `export CXX=hipcc`
- Use `torch.utils.cpp_extension.CppExtension` with explicit compiler flags

---

### 3. CK-Tile Python Bindings

| Field | Value |
|-------|-------|
| **ID** | BLOCKER-003 |
| **Name** | No Python Bindings for CK-Tile |
| **Category** | API/Interface |
| **Severity** | Medium |
| **Status** | Open |

**Description:**
CK-Tile is a C++ header-only library with no native Python bindings. Direct usage from Python requires wrapping via PyTorch C++ extensions.

**Impact:**
- Cannot directly import and use CK-Tile from Python
- Requires C++ wrapper code for each kernel
- Increases development iteration time

**Workarounds:**
1. Write thin C++ wrappers using PyTorch C++ extension API
2. Use pre-compiled shared objects
3. Use Triton for rapid prototyping, CK-Tile for final optimization

**Resolution Path:**
- Community Python bindings may be developed
- Use torch.compile with inductor backend for automatic kernel selection

---

### 4. Triton JIT Type Registry FP4

| Field | Value |
|-------|-------|
| **ID** | BLOCKER-004 |
| **Name** | `float4_e2m1fn_x2` KeyError in Triton JIT |
| **Category** | API/Interface |
| **Severity** | Critical |
| **Status** | Open |
| **Discovered** | Competition team - Session 80 |

**Description:**
Triton's JIT type registry throws a `KeyError` when attempting to use `float4_e2m1fn_x2` (FP4 packed type) in custom kernels on AMD GPUs. This type is required for MXFP4 operations but is not properly registered in the AMD Triton backend.

**Impact:**
- Cannot write custom Triton kernels using FP4/MXFP4 on AMD
- Blocks alternative implementation path when CK-Tile/AITER unavailable
- Forces dependency on pre-built kernels only

**Error:**
```
KeyError: 'float4_e2m1fn_x2'
  File "triton/compiler/compiler.py", line ..., in make_ir
    ty = types[key]  # <-- fails here
```

**Workarounds:**
1. Use `uint8` and manually pack/unpack FP4 (2 values per byte)
2. Use Triton 3.0+ with experimental FP4 support flag
3. Fall back to CK-Tile C++ kernels instead of Triton
4. Use `float8_e4m3fn` as alternative (2x memory, compatible)

**Example Workaround:**
```python
import triton
import triton.language as tl

# Pack FP4 manually - 2 values per byte
@triton.jit
def pack_fp4(val1, val2):
    # Pack two FP4 values into one byte
    return ((val1 & 0xF) << 4) | (val2 & 0xF)

@triton.jit
def unpack_fp4(packed, idx):
    # Unpack byte at idx (0 or 1)
    return (packed >> (4 * (1 - idx))) & 0xF

@triton.jit
def fp4_gemm_kernel(a_ptr, b_ptr, c_ptr, M, N, K):
    # Use uint8 instead of float4_e2m1fn_x2
    a_byte = tl.load(a_ptr + offset)
    # Manually extract FP4 values
    val_low = unpack_fp4(a_byte, 0)
    val_high = unpack_fp4(a_byte, 1)
```

**Resolution Path:**
- Report to Triton/ROCm maintainers
- May require Triton PR to add FP4 type registration for AMD backend
- Track: https://github.com/triton-lang/triton/issues (search FP4 AMD)

---

## Resolved Blockers

None currently documented.

## Blocker Metrics

| Category | Open | Resolved |
|----------|------|----------|
| Dependency/Environment | 1 | 0 |
| Build/Compilation | 1 | 0 |
| API/Interface | 2 | 0 |
| **Total** | **4** | **0** |

## Related Skills

- `CK_TILE_FUSED_MOE_PRIME.md` - CK-Tile implementation guide
- `ROCM_GFX950_SUPPORT_PRIME.md` - CDNA4 architecture support
- `AMD_HIPKITTENS_INTEGRATION_PRIME.md` - Profiling and debugging
- `AITER_KERNEL_PARAMETER_SEMANTICS_PRIME.md` - AITER parameter tuning

## Notes

- Blockers are tracked per-session for context preservation
- Workarounds should be documented in corresponding PRIME skills
- Resolution status should be updated when blockers are cleared
