Thinking...
The user wants me to optimize an AMD MI355X GPU kernel for MoE (Mixture of [K
Experts) inference. The current submission uses aiter's fused_moe with shap[4D[K
shape-aware KSPLIT, but the performance is 154.2µs vs the target of <110µs [K
(rank 1 is at 70.5µs).

Key constraints:
1. Must use `load_inline` HIP kernels that compile and run on the runner
2. MFMA 32x32x64 FP4 intrinsic is verified working
3. B_q is standard FP4 packed, B_shuffle is CK-specific format
4. Target is geometric mean across 6-8 benchmark shapes
5. Current approach uses AITER environment variables for KSPLIT

The user is asking for ONE specific optimization from the list:
1. LDS double-buffering for coalesced memory access
2. Multi-tile output (32x128) for A data reuse
3. Vectorized 128-bit global loads
4. XCD-aware scheduling with __builtin_amdgcn_s_setprio
5. Shape-specialized dispatch (different tile sizes for M=4 vs M=256)

Given the context:
- MI355X is CDNA4 (gfx950) with MFMA 32x32x64 support for FP4
- The problem involves tiny GEMMs (M=4 to M=256) with varying K (256, 512, [K
2048)
- The current submission is using aiter's high-level API which may not be o[1D[K
optimal for these tiny sizes

The most impactful optimization for tiny GEMMs (M=4,16,128,512) with small [K
K would likely be shape-specialized dispatch with custom inline kernels, si[2D[K
since the default GEMM tiling may be too large for these small M cases.

However, looking at the constraints, I need to write a complete submission.[11D[K
submission.py that uses `load_inline` to compile and run custom HIP kernels[7D[K
kernels.

Let me think about the optimization strategy:

For MI355X (CDNA4), FP4 MFMA is 32x32x64. This means we process 32x64 chunk[5D[K
chunks of A and 64x32 chunks of B to produce 32x32 C tiles.

Given the shapes:
- d_expert=256 (K=256): Very small K, M can be 16/128/512
- d_expert=512 (K=512): Small K, M can be 16/128/512  
- d_expert=2048 (K=2048): Medium K, M=512

For tiny M (like 16) and tiny K (like 256), a standard GEMM approach has to[2D[K
too much overhead. We need:
1. Vectorized 128-bit loads (4xFP4 or 8xFP4 per load)
2. Shape-specialized tile sizes (e.g., for M=4, use different strategy than[4D[K
than M=256)
3. XCD-aware scheduling to distribute work across 8 XCDs

The most promising single optimization given the "tiny GEMM" nature is **Sh[4D[K
**Shape-specialized dispatch with custom inline kernels using MFMA 32x32x64[8D[K
32x32x64 and vectorized loads**, combined with XCD-aware scheduling.

But I need to pick ONE from the list. Let me reconsider:

Option 5 (Shape-specialized dispatch) is the most appropriate because:
- The problem explicitly mentions "tiny GEMMs"
- Different shapes (M=16 vs M=512) need different tile strategies
- We can write custom HIP kernels that use MFMA 32x32x64 directly for the l[1D[K
larger cases and simpler vectorized dot products for tiny cases

Actually, looking at the current code, it's using `fused_moe` from aiter. T[1D[K
To really optimize, I need to replace this with custom kernels using `torch[6D[K
`torch.utils.cpp_extension.load_inline`.

Let me design a kernel:

For FP4 MoE on MI355X:
- Input activation: BF16/FP16 (let's assume BF16 based on typical MI300X/MI[9D[K
MI300X/MI355X usage)
- Weights: FP4 (packed 2 weights per byte)
- MFMA: 32x32x64 for FP4

The MoE operation is essentially:
1. Gate/Up projection: [M, K] @ [K, N] -> [M, N]
2. Activation (SiLU/Swish)
3. Down projection: [M, N] @ [N, K] -> [M, K]

Given the constraint about B_q (standard FP4) vs B_shuffle (CK-specific), a[1D[K
and the note that "MFMA 32x32x64 FP4 intrinsic is VERIFIED working", I shou[4D[K
should write a kernel that uses this intrinsic.

However, writing a full MoE kernel from scratch in the submission is comple[6D[K
complex. But the user says "load_inline HIP kernels COMPILE AND RUN on the [K
runner", so I can provide a complete inline kernel.

Let me think about the specific optimization: **Shape-specialized dispatch [K
with XCD-aware scheduling**.

For MI355X with 8 XCDs and 304 CUs:
- We need to distribute the M dimension across XCDs
- For small M (16), we need to be careful not to underutilize
- For large M (512), we can use full tiles

The kernel should:
1. Detect the shape (M, K, N)
2. Choose appropriate tile size (e.g., M=4 uses different config than M=256[5D[K
M=256)
3. Use __builtin_amdgcn_s_setprio for XCD balancing
4. Use vectorized 128-bit loads
5. Use LDS double-buffering

But I need to output ONLY the complete modified submission.py.

Let me draft a solution that uses `torch.utils.cpp_extension.load_inline` t[1D[K
to compile a custom HIP kernel for the MoE operation, specialized for the d[1D[K
different shapes mentioned.

The shapes are:
1. d_expert=256, n_routed=256, bs=16/128/512 (3 shapes)
2. d_expert=512, n_routed=32, bs=16/128/512 (3 shapes)  
3. d_expert=2048, n_routed=32, bs=512 (1 shape)

Total 7 shapes.

For the tiny shapes (d_expert=256, bs=16), we have very small work. We need[4D[K
need to ensure the kernel launches enough warps to saturate the GPU.

Given the complexity, I'll focus on providing a kernel that:
- Uses shape-specialized constants
- Employs MFMA 32x32x64 for the compute
- Uses vectorized loads (128-bit)
- Implements XCD-aware scheduling

Actually, looking at the target time (70.5µs vs current 154.2µs), we need ~[1D[K
~2.2x speedup. This likely requires avoiding the overhead of the aiter API [K
and going straight to inline assembly/optimal HIP.

Let me write a submission that:
1. Uses `torch.utils.cpp_extension.load_inline` to compile a custom MoE ker[3D[K
kernel
2. The kernel uses `__builtin_amdgcn_mfma_f32_32x32x64_f16` (or the FP4 var[3D[K
variant)
3. Implements shape specialization via template parameters or runtime switc[5D[K
switches
4. Uses XCD-aware scheduling with `__builtin_amdgcn_s_setprio`

Wait, the user mentions "B_q is standard FP4 packed, B_shuffle is CK-specif[9D[K
CK-specific format". This suggests that the weights might need to be conver[6D[K
converted or accessed in a specific way.

Let me reconsider the single optimization to propose. Given the options:
- Option 2 (Multi-tile output 32x128 for A data reuse) seems good for keepi[5D[K
keeping activation data in registers/LDS while computing multiple tiles
- Option 5 (Shape-specialized dispatch) is crucial for handling M=4 efficie[7D[K
efficiently vs M=256

I'll go with **Option 5: Shape-specialized dispatch**, but implement it wit[3D[K
with inline HIP using MFMA and vectorized loads, which effectively covers O[1D[K
Option 3 as well.

The code structure:
```python
import torch
from torch.utils.cpp_extension import load_inline

# Define the HIP kernel source
hip_source = """
#include <hip/hip_runtime.h>
#include <hip/hip_fp16.h>
#include <hip/hip_bfloat16.h>
#include <amd_device_functions.h>

// FP4 unpacking and MFMA implementation
// ...

template<int M_TILE, int K_TILE, int N_TILE>
__global__ void moe_gemm_kernel(...) {
    // Shape-specialized implementation
    // Use MFMA 32x32x64 for FP4
    // Vectorized loads
    // XCD scheduling
}
"""

# Compile inline
moe_kernel = load_inline(
    name="moe_specialized",
    cpp_sources=[hip_source],
    extra_cuda_cflags=["-O3", "--offload-arch=gfx950"],
    functions=["moe_gemm_dispatch"]
)

def custom_kernel(data):
    # ... extract data
    # Determine shape category
    if bs <= 16 and d_expert <= 256:
        # Tiny shape path
        moe_kernel.moe_gemm_dispatch_tiny(...)
    elif d_expert >= 2048:
        # Large K path  
        moe_kernel.moe_gemm_dispatch_large(...)
    else:
        # Medium path
        moe_kernel.moe_gemm_dispatch_medium(...)
```

But this is quite complex to write correctly without knowing the exact data[4D[K
data layout. However, the user says "load_inline HIP kernels COMPILE AND RU[2D[K
RUN on the runner", so I should provide a complete, compilable kernel.

Given the time constraints, I'll provide a solution that:
1. Uses inline HIP with shape specialization
2. Implements the MFMA 32x32x64 FP4 matmul
3. Uses vectorized 128-bit loads (uint4)
4. Includes XCD-aware scheduling via thread block distribution

Let me draft the kernel:

Key aspects:
- FP4 weights: packed as 2 4-bit values per byte
- MFMA 32x32x64: each MFMA instruction computes a 32x32 output tile from 32[2D[K
32x64 A and 64x32 B
- For FP4, the input format is specific: each thread holds 8 FP4 values (32[3D[K
(32 bits) for the MFMA

Actually, looking at CDNA4 documentation, FP4 MFMA 32x32x64 means:
- A matrix: 32 rows x 64 cols, each thread holds 8 FP4 values (4 bytes) per[3D[K
per row? 
- Wait, FP4 is 4-bit, so 64 elements = 32 bytes per row.
- With 32 threads in a wave, each thread loads 32 bytes for the A tile.
- Actually, standard MFMA 32x32x64 for FP4: each wave processes 32x64 of A [K
and 64x32 of B.

Let me write a simplified but correct kernel that focuses on shape speciali[8D[K
specialization and efficient memory access.

Given the complexity of writing a full FP4 MFMA kernel from scratch in this[4D[K
this context, and the fact that the user mentioned "aiter API parameters ar[2D[K
are EXHAUSTED", the optimization should probably still use aiter but with c[1D[K
custom environment settings or a wrapper that calls specialized kernels.

But the user explicitly asks for "load_inline HIP kernels", so I must provi[5D[K
provide that.

Let me provide a kernel that handles the MoE routing and GEMM efficiently:

```python
#!POPCORN leaderboard amd-moe-mxfp4
#!POPCORN gpu MI355X

from __future__ import annotations
import os
import torch
from torch.utils.cpp_extension import load_inline
from task import input_t, output_t

# HIP kernel with shape specialization
hip_source = """
#include <hip/hip_runtime.h>
#include <hip/hip_fp16.h>
#include <hip/hip_bfloat16.h>

typedef __hip_bfloat16 bf16;
typedef __hip_fp16 fp16;

// FP4 unpacking: 8 x FP4 per 32-bit word
// Each nibble represents one FP4 value
__device__ __forceinline__ void unpack_fp4(uint32_t packed, float out[8]) {[1D[K
{
    // Unpack 8 nibbles and convert to float
    #pragma unroll
    for (int i = 0; i < 8; i++) {
        uint32_t nibble = (packed >> (i * 4)) & 0xF;
        // FP4 to float conversion table
        // Simplified: map 0-15 to linear scale for now
        // Real implementation would use proper FP4 decoding
        out[i] = __builtin_bit_cast(float, (nibble << 28)); // Placeholder
    }
}

// MFMA 32x32x64 for FP4
__device__ __forceinline__ void mfma_f32_32x32x64_fp4(
    float32_t& acc,
    uint32_t a,
    uint32_t b,
    uint32_t c
) {
    // asm volatile("v_mfma_f32_32x32x64_fp4 %0, %1, %2, %3" : "=v"(acc) : [K
"v"(a), "v"(b), "v"(c));
    // Using builtin if available
    acc = __builtin_amdgcn_mfma_f32_32x32x64_fp4(a, b, c, 0, 0, 0);
}

// Shape specialized kernel for small M (16, 128)
template <int BS, int D_EXPERT>
__global__ __launch_bounds__(256) void moe_small_kernel(
    const bf16* __restrict__ hidden_states,
    const uint32_t* __restrict__ gate_up_weight, // FP4 packed
    const uint32_t* __restrict__ down_weight,
    const float* __restrict__ topk_weights,
    const int32_t* __restrict__ topk_ids,
    bf16* __restrict__ output,
    int num_tokens,
    int num_experts,
    int topk
) {
    // XCD-aware scheduling: distribute blocks across XCDs
    int xcd_id = blockIdx.x % 8;
    __builtin_amdgcn_s_setprio(xcd_id < 4 ? 1 : 0);
    
    // Implementation for small batch sizes
    // Uses vectorized loads and MFMA
}

// Shape specialized kernel for large M (512)
__global__ __launch_bounds__(512) void moe_large_kernel(...) {
    // Optimized for M=512, can use larger tiles
}

extern "C" __global__ void dispatch_kernel(...) {
    // Runtime dispatch based on size
}
"""

# Compile the inline module
moe_cuda = load_inline(
    name="moe_specialized",
    cpp_sources=[hip_source],
    extra_cuda_cflags=[
        "-O3",
        "--offload-arch=gfx950",
        "-std=c++17",
        "-D__HIP_PLATFORM_AMD__",
    ],
    extra_include_paths=[],
    functions=["moe_small_kernel", "moe_large_kernel"],
)

def custom_kernel(data: input_t) -> output_t:
    (
        hidden_states,
        gate_up_weight,
        down_weight,
        gate_up_weight_scale,
        down_weight_scale,
        gate_up_weight_shuffled,
        down_weight_shuffled,
        gate_up_weight_scale_shuffled,
        down_weight_scale_shuffled,
        topk_weights,
        topk_ids,
        config,
    ) = data

    bs = config["bs"]
    d_expert = config["d_expert"]
    
    # Shape-specialized dispatch
    if d_expert <= 256 and bs <= 128:
        # Tiny path: use custom kernel with small tiles
        grid = ( (bs + 15) / 16, 1, 1)
        moe_cuda.moe_small_kernel[grid](...)
    else:
        # Fallback to optimized aiter or large kernel
        return fused_moe(...)
```

This is getting too complex and might not compile without proper FP4 MFMA s[1D[K
syntax. Let me look for a simpler but effective optimization.

Actually, looking at the prompt again, the user says "Propose ONE specific [K
optimization to try" and lists 5 options. I should pick one and implement i[1D[K
it well.

**Option 4: XCD-aware scheduling with __builtin_amdgcn_s_setprio** combined[8D[K
combined with shape specialization.

MI355X has 8 XCDs. For tiny GEMMs, we need to ensure work is evenly distrib[7D[K
distributed and avoid tail effects.

But actually, **Option 2: Multi-tile output (32x128) for A data reuse** is [K
very promising for MoE because:
- In MoE, we read the same hidden states (A) multiple times for different e[1D[K
experts
- By computing multiple output tiles (32x128 instead of 32x32), we reuse th[2D[K
the loaded A data in registers/LDS
- This reduces memory bandwidth pressure on A

However, for FP4 with MFMA 32x32x64, extending to 32x128 means computing 4 [K
output tiles along the N dimension, which allows reusing the A tile (32x64)[7D[K
(32x64) across 4 B tiles (64x32 each).

But given the shapes (d_expert=256, 512, 2048), for d_expert=256, N=256, so[2D[K
so 32x128 covers half the expert.
For d_expert=2048, N=2048, so we can do multiple tiles.

Let me go with **Option 5: Shape-specialized dispatch**, as it's the most c[1D[K
comprehensive and can incorporate the other optimizations.

Final plan:
- Write a submission.py that uses `torch.utils.cpp_extension.load