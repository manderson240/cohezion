---
type: skill
name: amd-hip-kernel-development
description: "Develop custom HIP C++ kernels for AMD MI355X (gfx950) GPU optimization"
triggers:
  - "custom HIP kernel"
  - "gfx950"
  - "MI355X"
  - "MFMA instructions"
  - "ROCm kernel"
version: 1.0.0
created: 2026-03-17
title: "AMD HIP Kernel Development for MI355X"
date: 2026-03-17
tags: [cerebellum, amd, hip, gfx950, mi355x, gpu-optimization, competition, luma-speedrun]
aspect: thinker
---

# AMD HIP Kernel Development for MI355X

## Architecture: gfx950 (CDNA4)

### Key Features
- **MFMA Instructions**: Native FP8 and FP4 matrix operations
- **Wavefront Size**: 64 threads
- **LDS Banks**: 64 banks, 32-bit wide
- **Compute Units**: 304 CUs on MI355X
- **Memory**: HBM3 with 128-bit global→LDS transfers

### Critical Instructions

```cpp
// FP8 MFMA (32x32 output tile)
__builtin_amdgcn_mfma_f32_32x32x16_fp8_fp8(A, B, C, 0, 0, 0);

// FP8 MFMA (16x16 output tile)  
__builtin_amdgcn_mfma_f32_16x16x32_fp8_fp8(A, B, C, 0, 0, 0);

// MXFP4/FP6/FP8 with scaling (CDNA4 only)
__builtin_amdgcn_mfma_scale_f32_32x32x64_f8f6f4(A, B, C, scale, 0, 0, 0);
__builtin_amdgcn_mfma_scale_f32_16x16x128_f8f6f4(A, B, C, scale, 0, 0, 0);
```

## Build Configuration

### Makefile Template
```makefile
HIPCC = hipcc
ARCH = gfx950
CXXFLAGS = -O3 -fPIC --offload-arch=$(ARCH) -D__HIP_PLATFORM_AMD__

%.so: %.hip
	$(HIPCC) $(CXXFLAGS) -shared -o $@ $<
```

### Python Integration
```python
import ctypes
import torch

# Load compiled kernel
lib = ctypes.CDLL("./libkernel.so")

# Define function signature
lib.custom_kernel.argtypes = [
    ctypes.c_void_p,  # A
    ctypes.c_void_p,  # B
    ctypes.c_void_p,  # C
    ctypes.c_int,     # M
    ctypes.c_int,     # N
    ctypes.c_int,     # K
]

# Call from PyTorch
lib.custom_kernel(
    A.data_ptr(),
    B.data_ptr(),
    C.data_ptr(),
    M, N, K
)
```

## Optimization Patterns

### 1. 8-Wave Ping-Pong
```cpp
// 4 waves for memory, 4 waves for compute
__builtin_amdgcn_sched_barrier(0);  // Memory barrier
__builtin_amdgcn_s_setprio(1);       // High priority for compute
```

### 2. LDS Swizzle Pattern
```cpp
// XOR pattern for 64-bank conflict avoidance
int lds_offset = (threadIdx.x ^ (threadIdx.x >> 4)) * 4;
```

### 3. Direct Global→LDS
```cpp
// 128-bit transfer bypassing VGPR
extern "C" __device__ void llvm_amdgcn_raw_buffer_load_lds(
    u32x4 rsrc, as3_uint32_ptr lds_ptr, int size, 
    int voffset, int soffset, int offset, int aux
) __asm("llvm.amdgcn.raw.buffer.load.lds");
```

## Tile Size Selection

| Shape | BLOCK_M | BLOCK_N | BLOCK_K | Split-K |
|-------|---------|---------|---------|---------|
| M≤16  | 64      | 64      | 128     | 4       |
| M≤64  | 128     | 128     | 128     | 2       |
| M>64  | 256     | 256     | 128     | 1       |

## Common Pitfalls

1. **Bank Conflicts**: Always use swizzle patterns
2. **Occupancy**: Target 8 waves (4+4 ping-pong)
3. **Memory Coalescing**: Ensure 128-bit aligned accesses
4. **Register Pressure**: Monitor VGPR usage

## References

- [[mi355x-mfma-instructions]]
- [[lds-swizzle-patterns]]
- [[wave-scheduling-optimal]]
- [[mxfp4-quantization-theory]]

## Vault Navigation

- [[luma-amd-speedrun-strategy]] — Competition context for this kernel work
- [[MOC-machine-learning]] — Parent map of content
- [[2026-03-17-session-kimi-k2-5]] — Session log for this work
