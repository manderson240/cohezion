---
type: pattern
name: gemm-tile-optimization-256x256x128
kernel: gemm
category: tile-optimization
status: success
time_us: 9.8
rank: 2
gpu: MI355X
arch: gfx950
created: 2026-03-17
title: "GEMM 256×256×128 Tile Optimization"
date: 2026-03-17
tags: [pattern, gemm, mi355x, tile-optimization, gpu-optimization, luma-speedrun, mxfp4]
aspect: thinker
---

# GEMM 256×256×128 Tile Optimization

## Overview
Optimal tile configuration for large M shapes (M ≥ 128) on MI355X.

## Parameters
- **BLOCK_M**: 256
- **BLOCK_N**: 256  
- **BLOCK_K**: 128
- **Split-K**: 1 (no split for large M)
- **Kernel**: `_ZN5aiter42f4gemm_bf16_per1x32Fp4_BpreShuffle_192x128E`

## Context
- **Shape**: M=256, N=3072, K=1536
- **Data Type**: MXFP4 (e2m1) with BF16 output
- **Quantization**: per-1x32 block scaling

## Implementation Details

### 8-Wave Ping-Pong Scheduling
```cpp
// 4 waves for memory loads
// 4 waves for MFMA compute
__builtin_amdgcn_sched_barrier(0);  // Memory barrier
__builtin_amdgcn_s_setprio(1);       // High priority for compute
```

### LDS Swizzle Pattern
```cpp
// XOR pattern for 64-bank conflict avoidance
int lds_offset = (threadIdx.x ^ (threadIdx.x >> 4)) * 4;
```

### Direct Global→LDS Transfer
```cpp
// 128-bit transfer bypassing VGPR
extern "C" __device__ void llvm_amdgcn_raw_buffer_load_lds(
    u32x4 rsrc, as3_uint32_ptr lds_ptr, int size, 
    int voffset, int soffset, int offset, int aux
) __asm("llvm.amdgcn.raw.buffer.load.lds");
```

## Key Learnings

1. **256×256×128 optimal for large M** (≥128)
2. **8-wave ping-pong critical** for occupancy on MI355X
3. **LDS swizzle XOR pattern** avoids bank conflicts
4. **Direct global→LDS 128-bit transfers** via llvm intrinsic
5. **Large tile kernel** (192x128) better than small tile for M≥64

## Performance
- **Time**: 9.8µs (vs 9.671µs leader)
- **Gap**: 1.3% (within measurement variance)
- **Rank**: #2

## When to Use
- M ≥ 128
- N ≥ 2048
- K ≥ 512

## When NOT to Use
- M < 64 (use 32×128 tiles instead)
- Very small K (use smaller BLOCK_K)

## Related Patterns
- [[gemm-tile-32x128-small-m]]
- [[gemm-split-k-optimization]]
- [[lds-swizzle-patterns]]

## Code Reference
```python
# Python submission
import aiter
from aiter import dtypes

kernel_name = "_ZN5aiter42f4gemm_bf16_per1x32Fp4_BpreShuffle_192x128E"
log2_ks = 0  # No split for large M

return aiter.gemm_a4w4_asm(
    A_q, B_shuffle, A_scale_sh, B_scale_sh,
    out, kernel_name,
    bpreshuffle=True,
    log2_k_split=log2_ks,
)
```

## References
- [[amd-hip-kernel-development]]
- [[luma-amd-speedrun-strategy]]
