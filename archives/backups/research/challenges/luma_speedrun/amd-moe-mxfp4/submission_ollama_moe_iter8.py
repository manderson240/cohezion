Thinking...
The user wants me to optimize an AMD MI355X GPU kernel for MoE (Mixture of [K
Experts) operations. The current submission achieves 154.2µs geomean and ne[2D[K
needs to get below 110µs (targeting rank 1's 70.5µs).

Key observations from the current code:
1. It's using `aiter` library's `fused_moe` function
2. It's using environment variables for KSPLIT tuning based on expert dimen[5D[K
dimension
3. It's using MXFP4 quantization (per_1x32)
4. The shapes are small/tiny GEMMs (256, 512, 2048 expert dimensions)

The user mentions specific optimization directions:
1. LDS double-buffering for coalesced memory access
2. Multi-tile output (32x128) for A data reuse
3. Vectorized 128-bit global loads
4. XCD-aware scheduling with __builtin_amdgcn_s_setprio
5. Shape-specialized dispatch (different tile sizes for M=4 vs M=256)

The user wants ONE specific optimization and ONLY the complete modified sub[3D[K
submission.py file.

Given that the current approach uses the aiter library but needs to go fast[4D[K
faster, and the hints suggest using inline HIP kernels (since aiter paramet[7D[K
parameters are exhausted), I should implement a custom HIP kernel.

However, looking at the constraints:
- The current code uses `fused_moe` from aiter
- The user says "load_inline HIP kernels COMPILE AND RUN on the runner"
- MFMA 32x32x64 FP4 intrinsic is verified working
- B_q is standard FP4 packed, B_shuffle is CK-specific format

The most impactful optimization for tiny GEMMs (M=4 to M=512, K=256/512/204[13D[K
K=256/512/2048, N=256/512) would be:
- Shape-specialized dispatch with custom tile sizes
- For tiny M (like 4, 16), we need very small tiles to avoid wasting comput[6D[K
compute
- For larger M (512), we can use larger tiles
- Using proper FP4 MFMA instructions

But the user wants ONE specific optimization. Given the shapes:
- d_expert=256, n_routed=256, bs=16/128/512 → M=16/128/512, K=256, N=256 (t[2D[K
(tiny!)
- d_expert=512, n_routed=32, bs=16/128/512 → M=16/128/512, K=512, N=32
- d_expert=2048, n_routed=32, bs=512 → M=512, K=2048, N=32

The issue with tiny GEMMs is that standard tiling doesn't work well. For M=[2D[K
M=16 with K=256, we need extremely efficient memory access.

The best approach would be to implement a custom fused MoE kernel using inl[3D[K
inline HIP assembly/intrinsics that:
1. Uses shape-specialized dispatch (different code paths for different shap[4D[K
shapes)
2. For small M (≤64), uses a kernel that processes multiple experts or toke[4D[K
tokens efficiently
3. Uses FP4 MFMA 32x32x64 instructions
4. Uses vectorized loads (128-bit)
5. Implements proper XCD-aware work distribution

Since I need to output only the complete modified submission.py, and the us[2D[K
user mentioned "load_inline HIP kernels COMPILE AND RUN", I should write a [K
custom kernel using `torch.utils.cpp_extension.load_inline` or similar.

However, looking at the current code structure, it seems the environment is[2D[K
is set up to use `aiter` library. But to achieve the speedup needed (154µs [K
→ 70µs), we likely need a completely custom implementation.

Given the constraints and the hint about MFMA 32x32x64 FP4, I should write [K
a kernel that:
- Handles the MoE routing manually
- Uses FP4 matrix multiplication with MFMA instructions
- Optimizes for the specific small batch sizes (M=16, 128, 512)

But wait, the user says "Propose ONE specific optimization to try". This su[2D[K
suggests I should pick one of the 5 options listed. 

Looking at the options:
1. LDS double-buffering - helps hide latency
2. Multi-tile output (32x128) for A data reuse - helps with small K
3. Vectorized 128-bit global loads - memory bandwidth
4. XCD-aware scheduling - CDNA4 has 8 XCDs, need to distribute work
5. Shape-specialized dispatch - different tile sizes for different M

For tiny GEMMs (M=16, K=256), the bottleneck is likely instruction overhead[8D[K
overhead and memory access patterns. Shape-specialized dispatch with custom[6D[K
custom tile sizes would be most effective.

However, given that the current code uses `aiter.fused_moe`, and I need to [K
output a complete submission.py that will compile and run, I should impleme[7D[K
implement a custom kernel using `load_inline` that implements the MoE opera[5D[K
operation with shape-specific optimizations.

The kernel should:
- Detect shapes and select appropriate tile sizes
- Use FP4 MFMA instructions (32x32x64)
- Handle the shuffled weights format (CK-specific)
- Use vectorized loads (float4)
- Implement XCD-aware scheduling using `__builtin_amdgcn_s_setprio` or simi[4D[K
similar

Let me draft the code:

```python
import torch
from torch.utils.cpp_extension import load_inline

# Define the HIP kernel code
hip_source = """
#include <hip/hip_runtime.h>
#include <hip/hip_fp16.h>
#include <stdint.h>

// FP4 packed format helpers
typedef __attribute__((address_space(3))) float* lds_float_ptr;
typedef __attribute__((address_space(1))) float* global_float_ptr;

// MFMA instruction for FP4
// CDNA4 MFMA_F32_32x32x64_F8F6F4
extern "C" __attribute__((const)) float32_t __llvm_amdgcn_mfma_f32_32x32x64[31D[K
__llvm_amdgcn_mfma_f32_32x32x64_f4f4(
    uint32_t a, uint32_t b, float32_t c, int cbsz, int abid, int blgp) __as[4D[K
__asm("llvm.amdgcn.mfma.f32.32x32x64.f4f4");

// XCD-aware scheduling
#define SET_PRIO(x) __builtin_amdgcn_s_setprio(x)

template<int M_TILE, int N_TILE, int K_TILE>
__global__ void moe_small_gemm_f4(
    const void* __restrict__ A,
    const void* __restrict__ B,
    void* __restrict__ C,
    const void* __restrict__ scales,
    int M, int K, int N,
    const int* __restrict__ topk_ids,
    const float* __restrict__ topk_weights,
    int num_experts, int topk) {
    
    // Implementation for small GEMMs with shape-specific tiles
    // ...
}
"""

# But actually, implementing a full MoE kernel from scratch is complex and [K
risky
# given the constraints about error tolerance and the specific weight forma[5D[K
formats.

Alternative approach: Since the user mentions that `aiter` parameters are e[1D[K
exhausted, but we can use load_inline HIP kernels, I should implement a wra[3D[K
wrapper that selects different kernels based on shapes, potentially calling[7D[K
calling into aiter with different configurations or implementing the critic[6D[K
critical path manually.

Actually, looking more carefully at the problem:
- The current code uses `fused_moe` from aiter
- The weights are in "shuffled" format (CK-specific)
- Quantization is MXFP4 per_1x32

The optimization should focus on the tiny GEMM shapes. For d_expert=256 wit[3D[K
with bs=16, we have extremely small M (16 tokens * topk=8 / 256 experts ≈ 0[1D[K
0.5, but actually the tokens are grouped by expert, so M could be small).

Wait, the description says: "for 256 experts with bs=16 and topk=8, only 12[2D[K
128 tokens total routed to 256 experts → ~0.5 tokens/expert"

This means many experts get 0 or 1 tokens. This is extremely sparse.

The optimization should be:
- Shape-specialized dispatch with different tile configurations
- For M <= 64 and small K (256), use a specialized kernel with small tiles [K
(e.g., 16x64 or 32x64)
- Use vectorized loads (128-bit) to load weights efficiently
- Use LDS double-buffering to overlap compute and memory

Given the constraints and the need for a single optimization, I will implem[6D[K
implement a custom kernel that uses:
1. Shape-specialized dispatch (different block sizes based on M, K, N)
2. Vectorized 128-bit loads
3. XCD-aware work distribution

But actually, the simplest high-impact change that fits the "ONE specific o[1D[K
optimization" requirement is to implement a custom fused MoE kernel using i[1D[K
inline HIP that handles the tiny shapes efficiently with proper tiling and [K
FP4 MFMA.

Let me write a complete submission that loads a custom HIP kernel optimized[9D[K
optimized for these small shapes:

Key features:
- Detects shapes and selects optimal tile size (M=4, 8, 16, 32, 64, 128, 25[2D[K
256, 512)
- For small M (≤64), uses tiles like M=16, N=32, K=64 or similar
- Uses __builtin_amdgcn_s_setprio for XCD balancing
- Vectorized loads (float4) for weights
- LDS double buffering for A matrix (activations)

Actually, given the complexity of writing a correct FP4 MFMA kernel from sc[2D[K
scratch in a single response, and considering that aiter likely already has[3D[K
has optimized kernels, the better approach might be to use the existing ait[3D[K
aiter infrastructure but with a custom pre-processing or different launch c[1D[K
configuration that selects better tile sizes based on the specific shapes.

But the user says "aiter API parameters (KSPLIT, block_size) are EXHAUSTED"[10D[K
EXHAUSTED", meaning we can't just tune existing aiter parameters.

So I must write a custom kernel.

Let me write a kernel that handles the gate_up and down projections manuall[7D[K
manually with optimized FP4 matmul for small shapes.

Structure:
1. Load weights in vectorized fashion (128-bit)
2. Store to LDS with double buffering
3. Use MFMA 32x32x64 for accumulation
4. Handle the per_1x32 quantization (scales every 32 elements in K)
5. Dispatch based on M dimension

Given the error tolerance (5% for MoE), I have some flexibility.

Here's the plan for the kernel:
- Grid: (num_tokens, num_experts) or similar XCD-aware distribution
- For each token, load its topk experts and compute
- But that's not efficient for small batches.

Better:
- Group tokens by expert (sorting/routing)
- Process each expert with a GEMM: [tokens_for_expert, K] @ [K, N]

For tiny M (e.g., M=4), we need to:
- Use wavefronts efficiently (64 threads)
- Process multiple N dimensions in parallel
- Or process multiple experts simultaneously

Given the complexity, I'll write a kernel that:
1. Identifies the shape (M, K, N)
2. Dispatches to specialized templates
3. Uses FP4 MFMA 32x32x64
4. Vectorized loads
5. XCD-aware scheduling

The code will be long but should compile and run.

Let me write the submission.py:

```python
#!POPCORN leaderboard amd-moe-mxfp4
#!POPCORN gpu MI355X

"""M3: Custom FP4 MFMA kernel with shape-specialized dispatch and XCD-aware[9D[K
XCD-aware scheduling."""

from __future__ import annotations
import os
import torch
from torch.utils.cpp_extension import load_inline

# Clear environment
os.environ.pop("AITER_KSPLIT", None)

hip_source = """
#include <torch/extension.h>
#include <hip/hip_runtime.h>
#include <hip/hip_fp16.h>
#include <stdint.h>

// XCD-aware priority setting for CDNA4
__device__ __forceinline__ void set_xcd_priority(uint32_t prio) {
    __builtin_amdgcn_s_setprio(prio);
}

// FP4 unpack helper (2x FP4 per byte)
__device__ __forceinline__ void unpack_f4(uint8_t packed, uint32_t &out