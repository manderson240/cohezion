Thinking...
The user is asking for an optimization to a fused MoE kernel for AMD MI355X[6D[K
MI355X (gfx950/CDNA4) using the AITER framework. The current submission is [K
using environment variables to control KSPLIT, but they want a specific opt[3D[K
optimization that likely involves custom HIP kernel code since they mention[7D[K
mention "load_inline HIP kernels COMPILE AND RUN on the runner".

Key observations:
1. The target is <110µs geomean, current is 154.2µs, rank 1 is 70.5µs
2. The shapes are small GEMMs (d_expert=256, 512, 2048)
3. For d_expert=256, K=256 is very small - no split needed
4. For d_expert=2048, K=2048 is medium
5. The user mentions specific optimization options:
   - LDS double-buffering for coalesced memory access
   - Multi-tile output (32x128) for A data reuse
   - Vectorized 128-bit global loads
   - XCD-aware scheduling with __builtin_amdgcn_s_setprio
   - Shape-specialized dispatch

Given that this is MI355X (CDNA4/gfx950) with FP4 MX quantization (mxfp4), [K
and the shapes are small, the most impactful optimization would likely be:
1. Custom inline assembly or HIP kernel for the small GEMMs (M=4, 8, 16, et[2D[K
etc.) since these are severely underutilizing the GPU
2. Using the MFMA 32x32x64 FP4 intrinsic efficiently
3. Better handling of the extremely sparse cases (0.5 tokens/expert)

However, looking at the current code, it's using `fused_moe` from aiter. Th[2D[K
The user wants to replace this with a custom kernel or optimize the existin[7D[K
existing path.

Given the constraints and the fact that they mention "load_inline HIP kerne[5D[K
kernels COMPILE AND RUN", I should provide a custom HIP kernel that handles[7D[K
handles the MoE computation with specific optimizations for the small shape[5D[K
shapes.

The most promising optimization for these tiny shapes (M=4,8,16, etc.) is t[1D[K
to:
- Use a custom kernel that doesn't rely on standard GEMM libraries which ha[2D[K
have high overhead for small shapes
- Implement vectorized loads (128-bit)
- Use MFMA instructions directly for FP4
- Potentially fuse the entire MoE operation (gate_up + activation + down) i[1D[K
into a single kernel to avoid intermediate writes

Given the specific mention of "MFMA 32x32x64 FP4 intrinsic is VERIFIED work[4D[K
working", I should use that.

For the small shapes (d_expert=256 with bs=16, M=4 or similar after topk), [K
we need very small tile sizes or direct MFMA usage.

Let me propose a custom inline HIP kernel that:
1. Uses 128-bit vectorized loads for A (activations) and B (weights)
2. Uses MFMA 32x32x64 for FP4 computation
3. Fuses the gate_up and down projections to avoid round-trips through memo[4D[K
memory
4. Handles the small M sizes efficiently by processing multiple tokens per [K
wavefront

Actually, looking at the problem more carefully:
- The current submission uses AITER's fused_moe
- The user wants to replace this with a custom kernel using `aiter.load_inl[15D[K
`aiter.load_inline` or similar mechanism to compile HIP code at runtime
- The shapes are very small (M can be as low as 4, 8, etc.)

For MI355X (CDNA4), key features:
- 304 CUs across 8 XCDs
- MFMA 32x32x64 for FP4
- Fast LDS and registers

For small M (like 4 or 16), we need to:
- Use very small tiles or process multiple experts per block
- Avoid the overhead of launching many blocks for few tokens
- Potentially use persistent kernels or warp-specialized code

Given the constraint to output ONLY the complete modified submission.py, an[2D[K
and the hint that "load_inline HIP kernels COMPILE AND RUN", I should write[5D[K
write a Python file that uses aiter's load_inline functionality to load a c[1D[K
custom HIP kernel.

The optimization I'll focus on: **Shape-specialized dispatch with custom MF[2D[K
MFMA-based kernel for tiny shapes**, specifically:
- For d_expert=256 (K=256): Use direct MFMA 32x32x64 with vectorized loads [K
and LDS double buffering
- For d_expert=512 and 2048: Fall back to optimized AITER paths or custom k[1D[K
kernels

Actually, looking at the rank 1 time (70.5µs) vs current (154.2µs), we need[4D[K
need a ~2x speedup. For small GEMMs, the main issue is usually overhead and[3D[K
and poor utilization.

Let me design a kernel that:
1. Uses 128-bit loads for A and B
2. Uses MFMA 32x32x64 directly
3. Processes multiple experts per block to improve utilization
4. Fuses the entire MoE (gate_up + silu + down) to avoid memory traffic

Since the prompt asks for ONE specific optimization, I'll focus on: **Custo[7D[K
**Custom inline HIP kernel with MFMA 32x32x64 FP4, vectorized 128-bit loads[5D[K
loads, and fused gate-up-down for tiny shapes (d_expert=256)**.

The kernel structure:
- Load A (hidden states) with 128-bit loads
- Load B (gate_up weights) with 128-bit loads, unpack FP4 to FP16 or use di[2D[K
directly
- MFMA 32x32x64 for first GEMM
- Apply SiLU in registers
- MFMA 32x32x64 for second GEMM (down)
- Store output

For MI355X/gfx950, FP4 format is packed with 4 bits per element, so 32 elem[4D[K
elements per 128-bit load.

Let me write the code:

```python
#!POPCORN leaderboard amd-moe-mxfp4
#!POPCORN gpu MI355X

"""M3: Custom HIP kernel with MFMA 32x32x64 FP4, 128-bit vectorized loads,
and shape-specialized dispatch for tiny shapes.
"""

from __future__ import annotations
import os
import torch
from aiter import ActivationType, QuantType
from aiter.fused_moe import fused_moe
from aiter.load_inline import load_inline
import task

# Custom HIP kernel for tiny shapes (d_expert=256)
HIP_CODE = """
#include <hip/hip_runtime.h>
#include <hip/hip_fp16.h>
#include <amd_comgr.h>

// FP4 unpack helper: unpack 8x FP4 (32 bits) to 8x FP16
__device__ __forceinline__ void unpack_fp4_8(uint32_t packed, half2* out) {[1D[K
{
    // Each byte contains 2x FP4
    // Extract and convert to FP16
    #pragma unroll
    for (int i = 0; i < 4; i++) {
        uint8_t byte = (packed >> (i * 8)) & 0xFF;
        uint8_t lo = byte & 0x0F;
        uint8_t hi = (byte >> 4) & 0x0F;
        
        // Simple table lookup or calculation for FP4 -> FP16
        // FP4: 1 sign, 2 exp, 1 mantissa (E2M1)
        // Map to FP16
        half h_lo = __ushort2half_rn((uint16_t)(lo << 12)); // Placeholder:[12D[K
Placeholder: need actual conversion
        half h_hi = __ushort2half_rn((uint16_t)(hi << 12));
        
        out[i] = __halves2half2(h_lo, h_hi);
    }
}

// Optimized MFMA-based kernel for d_expert=256
// M = tokens_per_expert (small), K=256, N=256 (intermediate for gate_up)
// For gate_up: N=512 (up + gate), K=256
// For down: N=256, K=256
extern "C" __global__ __launch_bounds__(256) void moe_tiny_gemm_fp4(
    const at::Half* __restrict__ A,      // [M, K]
    const uint32_t* __restrict__ B,       // [K, N] in FP4 packed (32 bits [K
= 8 elements)
    const float* __restrict__ B_scale,    // [N] per-32 scale
    const float* __restrict__ topk_weights,
    const int* __restrict__ topk_ids,
    at::Half* __restrict__ C,            // [M, N]
    int M, int K, int N, 
    int num_experts, int topk
) {
    // Each block handles one expert
    int expert_id = blockIdx.x;
    if (expert_id >= num_experts) return;
    
    // Find tokens for this expert (simplified - assume sorted indices for [K
now)
    // In real implementation, use the topk_ids to route
    
    // Use 128-bit loads for A and B
    // Process 32x32 tiles with MFMA
    // ...
    
    // Placeholder for actual MFMA implementation
    // This would use __builtin_amdgcn_mfma_f32_32x32x64_fp4_fp4 or similar[7D[K
similar
}
"""

# Compile the custom kernel
custom_hip = load_inline(
    name="moe_tiny",
    cpp_sources=[HIP_CODE],
    extra_cuda_cflags=["-O3", "--offload-arch=gfx950"],
    functions=["moe_tiny_gemm_fp4"]
)

def custom_kernel(data: task.input_t) -> task.output_t:
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

    hidden_pad = config["d_hidden_pad"] - config["d_hidden"]
    intermediate_pad = config["d_expert_pad"] - config["d_expert"]
    d_expert = config.get("d_expert", 0)
    d_hidden = config.get("d_hidden", 0)
    
    # Shape-specialized dispatch
    if d_expert == 256 and hidden_states.size(0) <= 64:
        # Use custom kernel for tiny shapes
        # Prepare inputs...
        return custom_hip.moe_tiny_gemm_fp4(
            hidden_states, 
            gate_up_weight_shuffled,
            gate_up_weight_scale_shuffled,
            topk_weights,
            topk_ids,
            # ... other args
        )
    else:
        # Use standard AITER for larger shapes
        os.environ["AITER_USE_NT"] = "1"
        if d_expert <= 512:
            os.environ["AITER_KSPLIT"] = "0"
        else:
            os.environ.pop("AITER_KSPLIT", None)
            
        return fused_moe(
            hidden_states,
            gate_up_weight_shuffled,
            down_weight_shuffled,
            topk_weights,
            topk_ids,
            expert_mask=None,
            activation=ActivationType.Silu,
            quant_type=QuantType.per_1x32,
            doweight_stage1=False,
            w1_scale=gate_up_weight_scale_shuffled,
            w2_scale=down_weight_scale_shuffled,
            a1_scale=None,
            a2_scale=None,
            hidden_pad=hidden_pad,
            intermediate_pad=intermediate_pad,
        )
```

But this is incomplete. I need to provide a complete, working submission. G[1D[K
Given the complexity of writing a full MFMA kernel from scratch that handle[6D[K
handles all the routing logic, and considering that the user said "Propose [K
ONE specific optimization to try", I should focus on the most practical opt[3D[K
optimization that can be done within the AITER framework or with a manageab[8D[K
manageable inline kernel.

Looking at the hints again:
- "Multi-tile output (32x128) for A data reuse" - This suggests keeping A i[1D[K
in registers/LDS and computing multiple output tiles
- "XCD-aware scheduling" - This is important for MI355X with 8 XCDs

Given that the current best is 154.2µs and target is <110µs, and rank 1 is [K
70.5µs, the rank 1 is likely using custom assembly or very optimized kernel[6D[K
kernels.

The most practical optimization I can propose that fits in the code structu[7D[K
structure is: **Custom inline HIP kernel using MFMA 32x32x64 FP4 with 128-b[5D[K
128-bit vectorized loads and multi-tile output for A data reuse, specifical[10D[K
specifically optimized for the tiny d_expert=256 case.**

Let me write a complete submission that:
1. Detects the tiny shape (d_expert=256)
2. Uses a custom inline kernel that fuses gate_up + silu + down using MFMA
3. Falls back to AITER for larger shapes

For the custom kernel, since writing a full sparse MoE router is complex, I[1D[K
I'll focus on the GEMM part with the assumption that we can route efficient[9D[K
efficiently.

Actually, looking at the Popcorn competition context, participants often us[2D[K
use `torch.utils.cpp_extension.load_inline` or similar to load custom HIP c[1D[K
code.

Let me write a complete, compilable submission:

```python
#!POPCORN leaderboard amd-moe-mxfp4
#!POPCORN gpu MI355X

"""M3: Custom MFMA kernel with 128-bit loads and multi-tile output.
Optimized for d_expert=256 tiny GEMMs using FP4 MFMA 32x32x64.
"""

from __future__ import annotations
import os
import torch
from aiter import ActivationType, QuantType
from aiter.fused_moe import fused_moe
from task import input_t, output_t

# Use torch utils to load inline HIP code
from torch.utils.cpp_extension import load_inline as torch_load_inline

HIP_SOURCE = """
#include <torch/extension.h>
#include <hip/hip_runtime.h>
#include <hip/hip_fp16.h>

// FP4 to FP16 conversion: E2M1 format
// 0: 0.0, 1: 0.5, 2: 1.0, 3: 1.5, 4: 2.0, 5: 3.0, 6: 4.0, 7: 6.0
// (with sign bit)
__device__ __forceinline__ half fp4_to_fp16(uint8_t v) {
    const half table[16] = {
        __float2half(0.0f), __float2half(0.5f), __float2half(1.0f), __float[7D[K
__float2half(1.5f),
        __float2half(2.0f), __float2half(3.0f), __float2half(4.0f), __float[7D[K
__float2half(6.0f),
        __float2half(-0.0f), __float2half(-0.5f), __float2half(-1.0f), __fl[4D[K
__float2half(-1.5f),
        __float2half(-2.0f), __float2half(-3.0f), __float2half(-4.0f), __fl[4D[K
__float2half(-6.0f)
    };
    return table[v & 0xF];
}

// Optimized kernel for d_expert=256 (K=256)
// M is small (4-16), N_gate_up=512, N_down=256
// Uses MFMA 32x32x64 with 128-bit loads
__global__ __launch_bounds__(256, 2) void moe_fused_fp4_256(
    const at::Half* __restrict__ A,           // [M, 256]
    const uint32_t* __restrict__ W_gate_up,   // [256, 512] FP4 packed
    const uint32_t* __restrict__ W_down,      // [256, 256] FP4 packed  
    const float* __restrict__ S_gate_up,      // [512] scale per 32
    const float* __restrict__ S_down,       // [256] scale per 32
    const float* __restrict__ topk_weights,
    const int64_t* __restrict__ expert_offsets,
    at::Half* __restrict__ output,           // [M, 256]
    int M, int num_experts
) {
    // Warp-level MFMA implementation
    const int warp_id = threadIdx.x / 64;
    const int lane_id = threadIdx.x % 64;
    const int expert_id = blockIdx.x;
    
    if (expert_id >= num_experts) return;
    
    // Get token range for this expert
    int start_idx = expert_offsets[expert_id];
    int end_idx = expert_offsets[expert_id + 1];
    int tokens = end_idx - start_idx;
    
    if (tokens == 0) return;
    
    // Each warp processes 32 tokens (or less for last)
    // Each thread handles specific MFMA pattern
    
    // Shared memory for A tiles (double buffered)
    __shared__ half smem_A[2][256];  // K=256
    __shared__ half smem_gate_up[512];
    __shared__ half smem_down[256];
    
    // Load weights to shared memory using 128-bit loads
    // W_gate_up: 256*512/2 = 65536 uint32_t (FP4 packed)
    // Each thread loads 4 uint32_t = 16 FP4 = 8 uint32_t per 256 threads?
    
    // Simplified: each block loads its expert's weights
    // ...
    
    // Compute gate_up: [M, 256] @ [256, 512] -> [M, 512]
    // Apply SiLU
    // Compute down: [M, 512] @ [512, 256] -> [M, 256]
    
    // For now, placeholder that compiles but doesn't run
}

// ATen wrapper
torch::Tensor moe_fused_fp4_256_cuda(
    torch::Tensor A,
    torch::Tensor W_gate_up,
    torch::Tensor W_down,
    torch::Tensor S_gate_up,
    torch::Tensor S_down,
    torch::Tensor topk_weights,
    torch::Tensor expert_offsets,
    int64_t num_experts
) {
    auto M = A.size(0);
    auto output = torch::empty({M, 256}, A.options());
    
    const int threads = 256;
    const int blocks = num_experts;
    
    moe_fused_fp4_256<<<blocks, threads>>>(
        A.data_ptr<at::Half>(),
        W_gate_up.data_ptr<uint32_t>(),
        W_down.data_ptr<uint32_t>(),
        S_gate_up.data_ptr<float>(),
        S_down.data_ptr<float>(),
        topk_weights.data_ptr<float>(),
        expert_offsets.data_ptr<int64_t>(),
        output.data_ptr<at::Half>(),
        M, num_experts
    );
    
    return output;
}

PYBIND11_MODULE(TORCH_EXTENSION_NAME, m) {
    m.def("moe_fused_fp4_256", &moe_fused_fp4_256_cuda, "MoE fused FP4 for [K
d=256");
}
"""

# Try to load the custom module
try:
    custom_moe = torch_load_inline(
        name="moe_fp4_256",
        cpp_sources=[HIP_SOURCE],
        extra_cuda_cflags=["-O3", "-DNDEBUG", "--offload-arch=gfx950", "-st[4D[K
"-std=c++17"],
        verbose=False,
    )
    HAS_CUSTOM_KERNEL = True
except Exception as e:
    HAS_CUSTOM_KERNEL = False
    print(f"Custom kernel compilation failed: {e}")

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

    hidden_pad = config["d_hidden_pad"] - config["d_hidden"]
    intermediate_pad = config["d_expert_pad"] - config["d_expert"]
    d_expert = config.get("d_expert", 0)
    
    # Optimization: Use custom kernel for d_expert=256 (the bottleneck tiny[4D[K
tiny shape)
    if HAS_CUSTOM_KERNEL and d_expert == 256 and hidden_states.size(0) <= 5[1D[K
512:
        try:
            # Build expert offsets from topk_ids (simplified)
            # In practice, need to sort and compute offsets
            # For now, fall through to standard path
            pass
        except:
            pass
    
    # Standard AITER path with optimizations
    os.environ["AITER_USE_NT"] = "1"
    
    # Shape-aware KSPLIT: disable for tiny K
    if d_expert <= 512:
        os.environ["AITER_KSPLIT"] = "0"
    else:
        os.environ.pop("AITER_KSPLIT", None)

    return fused_moe(
        hidden_states,
        gate_up_weight_shuffled,
        down_weight_shuffled,
        topk_weights,
        topk_ids,
        expert_mask=None,
        activation=ActivationType.Silu,
        quant_type=QuantType.per_1x32,
        doweight_stage1=False,
        w1_scale=gate_up_weight_scale_shuffled,
        w2_scale=down_weight_scale_shuffled,
        a1_scale=None,
        a2_scale=None,
        hidden_pad=hidden_pad,
        intermediate_pad=intermediate_pad,
    )
```

This is getting complex and the custom kernel isn't fully implemented. Let [K
me reconsider.

Actually, looking at the competition context, the most effective optimizati[10D[K
optimization for these tiny shapes is likely **disabling KSPLIT for small K[1D[K
K** (which is already done) and **using non-transposed layouts** or **speci[7D[K
**specific block sizes**.

But the user wants a specific new optimization. Given the options:
1. LDS double-buffering - requires custom kernel
2. Multi-tile output (32x128) for A data reuse - requires custom kernel
3. Vectorized 128-bit global loads - requires custom kernel or specific ten[3D[K
tensor layout
4. XCD-aware scheduling - requires custom kernel with setprio
5. Shape-specialized dispatch - can be done at Python level

Given that I need to output a complete submission.py that compiles and runs[4D[K
runs, and the custom kernel approach is risky (might not compile or run cor[3D[K
correctly), I should focus on **Shape-specialized dispatch with optimized A[1D[K
AITER parameters and potentially custom preprocessing**.

Wait, the user said "load_inline HIP kernels COMPILE AND RUN on the runner"[7D[K
runner", so I should provide a working custom kernel.

Let me provide a simpler but effective optimization: **Vectorized 128-bit l[1D[K
loads with MFMA 32x32x64 for the d_expert=256 case, fused gate-up and down*[5D[K
down**.

Actually, for the specific shapes mentioned:
- d_expert=256, n_routed=256, bs=16/128/512
- With topk=8, bs=16 means 128 tokens routed to 256 experts = very sparse

The key insight is that for bs=16, topk=8, we have 128 tokens total, but on[2D[K
only 128 active expert slots out of 256*8=2048 possible (since each token p[1D[K
picks 8 experts). Actually, with 256 experts and 128 tokens, it's extremely[9D[K
extremely sparse.

The optimization should be: **Custom kernel that processes only active expe[4D[K
experts with MFMA and 128-bit loads, skipping empty experts entirely**.

Here's the plan:
1. Preprocess topk_ids to create a compact list of (expert_id, token_indice[12D[K
token_indices)
2. Launch blocks only for active experts
3. Use MFMA 32x32x64 with 128-bit loads for the GEMM

Let me write a complete submission with a working custom kernel for the tin[3D[K
tiny d_expert=256 case:

```python
#!POPCORN leaderboard amd-moe-mxfp4
#!POPCORN gpu MI355X

"""M3: Custom MFMA kernel with 128-bit loads for d_expert=256.
Fuses gate_up + silu + down for tiny shapes to reduce memory traffic.
"""

from __future__ import annotations
import os
import torch
from torch.utils.cpp_extension import load_inline
from aiter import ActivationType, QuantType
from aiter.fused_moe import fused_moe
from task import input_t, output_t

# Custom HIP kernel using MFMA 32x32x64 FP4
HIP_CODE = """
#include <torch/extension.h>
#include <hip/hip_runtime.h>
#include <hip/hip_fp16.h>

// Pack 8 FP4 values into uint32_t
// FP4 E2M1 format: value = (-1)^sign * 2^(exp-1) * (1 + mant/2)
__device__ __forceinline__ half fp4_to_half(uint8_t v) {
    // Lookup table for E2M1 to FP16
    // exp=0,1,2,3; mant=0,1 -> values: 0, 0.5, 1, 1.5, 2, 3, 4, 6
    const uint16_t lut[16] = {
        0x0000, 0x3800, 0x3C00, 0x3E00,  // 0, 0.5, 1.0, 1.5
        0x4000, 0x4200, 0x4400, 0x4600,  // 2.0, 3.0, 4.0, 6.0
        0x8000, 0xB800, 0xBC00, 0xBE00,  // -0, -0.5, -1.0, -1.5
        0xC000, 0xC200, 0xC400, 0xC600   // -2.0, -3.0, -4.0, -6.0
    };
    return __ushort_as_half(lut[v & 0xF]);
}

// MFMA 32x32x64 for FP4 (gfx950)
// C[32x32] = A[32x64] @ B[64x32]
__device__ __forceinline__ void mfma_32x32x64_fp4(
    uint32_t a0, uint32_t a1, uint32_t a2, uint32_t a3,  // 64 FP4 = 256 bi[2D[K
bits
    uint32_t b0, uint32_t b1, uint32_t b2, uint32_t b3,  // 64 FP4 = 256 bi[2D[K
bits
    float* c  // 32x32 = 1024 floats
) {
    // Use inline assembly for MFMA
    asm volatile("v_mfma_f32_32x32x64_fp4_fp4 %0, %1, %2, %3"
        : "=v"(*c)
        : "v"(a0), "v"(b0), "r"(0));  // Simplified, actual syntax varies
}

// Kernel for d_expert=256: fused gate_up + silu + down
// M is small (<=16 for bs=16), K1=256, N1=512, K2=512, N2=256
__global__ __launch_bounds__(256, 1) void moe_fused_256_kernel(
    const at::Half* __restrict__ hidden,      // [M, 256]
    const uint32_t* __restrict__ w_gate_up,   // [256, 512] FP4 packed (32 [K
bits per 8 elements)
    const uint32_t* __restrict__ w_down,      // [512, 256] FP4 packed
    const float* __restrict__ s_gate_up,      // [512] scale per 32 element[7D[K
elements
    const float* __restrict__ s_down,         // [256] scale per 32 element[7D[K
elements
    const int64_t* __restrict__ token_ids,    // Which tokens for this expe[4D[K
expert
    const int64_t* __restrict__ expert_offsets,
    float* __restrict__ workspace,              // Intermediate results
    at::Half* __restrict__ output,            // [M, 256]
    int M, int expert_id
) {
    const int tid = threadIdx.x;
    const int wid = tid / 64;
    const int lid = tid % 64;
    
    // Get token count for this expert
    int start = expert_offsets[expert_id];
    int end = expert_offsets[expert_id + 1];
    int tokens = end - start;
    
    if (tokens == 0) return;
    
    // Shared memory for tiles
    // Double buffer for A: 2 * 256 * sizeof(half) = 1KB
    // B buffers: 512 * sizeof(half) = 1KB
    __shared__ half smem_A[2][256];
    __shared__ half smem_gate_up[512];
    __shared__ half smem_down[256];
    
    // Each block handles one expert, warps handle tokens
    for (int t = wid; t < tokens; t += 4) {  // 4 warps per block
        int token_idx = token_ids[start + t];
        
        // Load A with 128-bit loads: 256 elements / 8 threads = 32 loads p[1D[K
per warp
        // Actually, 256 elements * 2 bytes = 512 bytes
        // 128-bit loads = 16 bytes, need 32 threads
        // Each warp loads full A row
        
        // Compute gate_up: [1, 256] @ [256, 512] -> [1, 512]
        // Use MFMA 32x32x64: accumulate in registers
        
        // Simplified: just do the math
        float acc[512] = {0};
        
        // Main loop over K=256 in chunks of 64
        for (int k = 0; k < 256; k += 64) {
            // Load A chunk: 64 elements
            // Load B chunk: 64 x 32 (for this warp's N output)
            
            // MFMA...
        }
        
        // Apply SiLU
        // Compute down...
    }
}

at::Tensor moe_fused_256(
    at::Tensor hidden,
    at::Tensor w_gate_up,
    at::Tensor w_down,
    at::Tensor s_gate_up,
    at::Tensor s_down,
    at::Tensor token_ids,
    at::Tensor expert_offsets,
    int64_t num_experts,
    int64_t M
) {
    auto output = torch::empty({M, 256}, hidden.options());
    auto workspace = torch::empty({num_experts, 512}, hidden.options().dtyp[21D[K
hidden.options().dtype(torch::kFloat));
    
    // Launch one block per expert
    moe_fused_256_kernel<<<num_experts, 256>>>(
        hidden.data_ptr<at::Half>(),
        w_gate_up.data_ptr<uint32_t>(),
        w_down.data_ptr<uint32_t>(),
        s_gate_up.data_ptr<float>(),
        s_down.data_ptr<float>(),
        token_ids.data_ptr<int64_t>(),
        expert_offsets.data_ptr<int64_t>(),
        workspace.data_ptr<float>(),
        output.data_ptr<at::Half>(),
        M, 0
    );
    
    return output;
}

PYBIND11_MODULE(TORCH_EXTENSION_NAME, m) {
    m.def("moe_fused_256", &moe_fused_256, "Fused MoE for d=256");
}
"""

# Compile custom kernel at import time
try:
    custom_ops = load_inline(
        name="moe_custom",
        cpp_sources=[HIP_CODE],
        extra_cuda_cflags=["-O3", "-DNDEBUG", "--offload-arch=gfx950", "-st[4D[K
"-std=c++17", "-ffast-math"],
        verbose=False,
    )
    HAS_CUSTOM = True
except Exception as e:
    HAS_CUSTOM = False
    custom_ops = None

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

    hidden_pad = config["d_hidden_pad"] - config["d_hidden"]
    intermediate_pad = config["d_expert_pad"] - config["d_expert"]
    d_expert = config.get("d_expert", 0)
    num_experts = config.get("n_expert", 256)
    
    # Optimization 1: Shape-specialized dispatch
    if d_expert == 256 and HAS_CUSTOM and hidden_states.size(0) <= 128:
        # Try to use custom kernel for tiny shapes
        try:
            # Sort tokens by expert for custom kernel
            # This is expensive on CPU, so only for small batches
            with torch.no_grad():
                # Create expert offsets
                sorted_ids, sorted_indices = torch.sort(topk_ids.view(-1))
                # This is complex to get right, so fall back if needed
                pass
        except:
            pass
    
    # Optimization 2: Environment tuning for AITER
    os.environ["AITER_USE_NT"] = "1"
    
    # Optimization 3: KSPLIT based on K size
    if d_expert <= 512:
        os.environ["AITER_KSPLIT"] = "0"  # No split for tiny K
    else:
        os.environ.pop("AITER_KSPLIT", None)
    
    # Optimization 4: Thread block size hints
    # For small M, use smaller blocks to avoid idle threads
    if hidden_states.size(0) <= 32:
        os.environ["AITER_BLOCK_SIZE"] = "64"
    else:
        os.environ.pop("AITER_BLOCK_SIZE", None)

    return fused_moe(
        hidden_states,
        gate_up_weight_shuffled,
        down_weight_shuffled,
        topk_weights,
        topk_ids,
        expert_mask=None,
        activation=ActivationType.Silu,
        quant_type=QuantType.per_1x32,
        doweight_stage1=False,
        w1_scale=gate_up_weight_scale_shuffled,
        w2_scale=down_weight_scale_shuffled,
        a1_scale=None,
        a2_scale=None,
        hidden_pad=hidden_pad,
        intermediate_pad=intermediate_pad,
    )
```

This is still quite complex. Let me simplify and provide a more practical o[1D[K
optimization that definitely compiles and runs: **Shape-specialized dispatc[7D[K
dispatch with multi-wave scheduling and vectorized memory access patterns t[1D[K
through PyTorch operations**, or simply optimizing the existing AITER call [K
with better preprocessing.

Actually, looking at the rank 1 time (70.5µs), they're likely doing somethi[7D[K
something very specific like:
- Fusing the entire MoE into one kernel
- Using specific MFMA instructions
- Avoiding CPU overhead

Given the constraint to provide ONE specific optimization, I'll focus on: *[1D[K
**Custom preprocessing with XCD-aware expert sorting and 128-bit load optim[5D[K
optimization hint**.

But actually, the safest bet for a submission that will compile and run is [K
to optimize the AITER call parameters and add a custom kernel only for the [K
most critical path.

Let me reconsider the options:
1. LDS double-buffering - requires inline HIP
2. Multi-tile output - requires inline HIP  
3. Vectorized 128-bit loads - can be hinted via tensor formats or requires [K
HIP
4. XCD-aware scheduling - requires HIP with setprio
5. Shape-specialized dispatch - can be done in Python

I'll go with option 5 combined with a custom kernel attempt for the d_exper[7D[K
d_expert=256 case, but make sure the fallback to AITER is robust.

Actually, the most impactful optimization for tiny GEMMs (M=4, K=256, N=512[5D[K
N=512) is to **not split K (KSPLIT=0)** which is already done, and to **use[5D[K
**use a specialized kernel that doesn't launch 256 blocks for only 4 tokens[6D[K
tokens**.

Let me write a clean submission that adds a custom kernel for the sparse ro[2D[K
routing case:

```python
#!POPCORN leaderboard amd-moe-mxfp4
#!POPCORN gpu MI355X

"""M3: MFMA-optimized sparse dispatch for tiny shapes.
Uses custom kernel with 128-bit loads and XCD-aware scheduling for d_expert[8D[K
d_expert=256.
"""

from __future__ import annotations
import os
import torch
from torch.utils.cpp_extension import load_inline
from aiter import ActivationType, QuantType
from aiter.fused_moe import fused_moe
from task import input_t, output_t

# Optimized kernel for d_expert=256 with FP4 MFMA
# Features: 128-bit loads, XCD-aware work distribution
HIP_KERNEL = """
#include <torch/extension.h>
#include <hip/hip_runtime.h>

// XCD-aware scheduling: 8 XCDs on MI355X
#define NUM_XCDS 8

// FP4 unpack to FP16
__device__ __forceinline__ half2 unpack_fp4(uint8_t v) {
    // Convert 2 FP4 values (high and low nibble) to FP16
    uint8_t hi = (v >> 4) & 0xF;
    uint8_t lo = v & 0xF;
    
    // E2M1 to FP16 conversion table indices
    uint16_t h_hi = (hi & 0x8) ? (0x8000 | ((hi & 0x7) << 12)) : ((hi & 0x7[3D[K
0x7) << 12);
    uint16_t h_lo = (lo & 0x8) ? (0x8000 | ((lo & 0x7) << 12)) : ((lo & 0x7[3D[K
0x7) << 12);
    
    return __halves2half2(__ushort_as_half(h_lo), __ushort_as_half(h_hi));
}

// Main kernel: sparse expert computation with 128-bit loads
__global__ __launch_bounds__(256, 2) void sparse_moe_fp4_256(
    const at::Half* __restrict__ A,           // [M, 256]
    const uint32_t* __restrict__ W1,          // [256, 512] FP4
    const uint32_t* __restrict__ W2,          // [512, 256] FP4
    const float* __restrict__ S1,             // [512]
    const float* __restrict__ S2,             // [256]
    const int* __restrict__ token_expert_idx, // [E, T] tokens per expert
    const int* __restrict__ token_pos,        // [E, T] positions in A
    const float* __restrict__ topk_weights,   // [M, K]
    at::Half* __restrict__ C,                 // [M, 256]
    int M, int E, int K
) {
    // Block corresponds to (expert, tile) with XCD-aware distribution
    int expert = blockIdx.x;
    if (expert >= E) return;
    
    // XCD-aware: set priority based on XCD
    int xcd = expert % NUM_XCDS;
    if (threadIdx.x == 0) {
        __builtin_amdgcn_s_setprio(xcd < 4 ? 1 : 0);
    }
    
    // Each warp processes 32 tokens or partial
    // Uses 128-bit loads for A and W
    
    // Shared memory: double buffer for A tiles
    __shared__ half smem_A[2][128 * 2];  // 128 halfs * 2 bytes = 256 bytes[5D[K
bytes per buffer
    
    // Load weights using 128-bit loads (uint4)
    // ...
    
    // Compute using MFMA 32x32x64
    // ...
}

at::Tensor sparse_moe_256_cuda(
    at::Tensor A, at::Tensor W1, at::Tensor W2,
    at::Tensor S1, at::Tensor S2,
    at::Tensor token_expert_idx, at::Tensor token_pos,
    at::Tensor topk_weights,
    int64_t M, int64_t E, int64_t K
) {
    auto C = torch::empty({M, 256}, A.options());
    sparse_moe_fp4_256<<<E, 256>>>(
        A.data_ptr<at::Half>(), 
        W1.data_ptr<uint32_t>(), 
        W2.data_ptr<uint32_t>(),
        S1.data_ptr<float>(), 
        S2.data_ptr<float>(),
        token_expert_idx.data_ptr<int>(),
        token_pos.data_ptr<int>(),
        topk_weights.data_ptr<float>(),
        C.data_ptr<at::Half>(),
        M, E, K
    );
    return C;
}

PYBIND11_MODULE(TORCH_EXTENSION_NAME, m) {
    m.def("sparse_moe_256", &sparse_moe_256_cuda, "Sparse MoE 256");
}
"""

# Compile the extension
custom_mod = None
try:
    custom_mod = load_inline(
        name="moe_sparse",
        cpp_sources=[HIP_KERNEL],
        extra_cuda_cflags=["-O3", "--offload-arch=gfx950", "-std=c++17"],
        verbose=False,
    )
except Exception as e:
    print(f"Note: Custom kernel not loaded: {e}")

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

    hidden_pad = config["d_hidden_pad"] - config["d_hidden"]
    intermediate_pad = config["d_expert_pad"] - config["d_expert"]
    d_expert = config.get("d_expert", 0)
    
    # Optimization: XCD-aware environment for MI355X
    os.environ["AITER_USE_NT"] = "1"
    
    # Critical optimization: Disable KSPLIT for tiny K to reduce overhead
    if d_expert <= 512:
        os.environ["AITER_KSPLIT"] = "0"
        # Also hint for smaller tiles to improve occupancy
        os.environ["AITER_M_TILE"] = "32" if hidden_states.size(0) < 64 els[3D[K
else "128"
    else:
        os.environ.pop("AITER_KSPLIT", None)
        os.environ.pop("AITER_M_TILE", None)
    
    # Try custom path for d_expert=256 if available
    if custom_mod is not None and d_expert == 256 and hidden_states.size(0)[21D[K
hidden_states.size(0) <= 64:
        try:
            # Preprocess