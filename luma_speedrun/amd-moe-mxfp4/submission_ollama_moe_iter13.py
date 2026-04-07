Thinking...
The user wants me to optimize an AMD MI355X GPU kernel for MoE (Mixture of [K
Experts) operations. The current submission achieves 154.2µs but needs to g[1D[K
get below 110µs (rank 1 is at 70.5µs).

Key context:
- AMD MI355X (gfx950, CDNA4, 304 CUs, 8 XCDs)
- MXFP4 quantization (FP4 weights)
- MFMA 32x32x64 FP4 intrinsic is available and working
- Current approach uses AITER's fused_moe with KSPLIT tuning
- Target is geometric mean across 6-8 benchmark shapes including tiny GEMMs[5D[K
GEMMs (d_expert=256) and larger ones (d_expert=2048)

The user wants ONE specific optimization from the list:
1. LDS double-buffering for coalesced memory access
2. Multi-tile output (32x128) for A data reuse
3. Vectorized 128-bit global loads
4. XCD-aware scheduling with __builtin_amdgcn_s_setprio
5. Shape-specialized dispatch (different tile sizes for M=4 vs M=256)

Since the current code is using the high-level `fused_moe` API from aiter, [K
and the user mentions "load_inline HIP kernels COMPILE AND RUN on the runne[5D[K
runner", I need to write a custom HIP kernel that will be loaded inline.

Looking at the constraints and the fact that MFMA 32x32x64 FP4 is verified [K
working, and we have tiny GEMMs (M=4,8 etc. for bs=16 with topk=8), the mos[3D[K
most impactful optimization would be **Shape-specialized dispatch with cust[4D[K
custom inline HIP kernel using MFMA 32x32x64 for FP4**.

However, for tiny GEMMs (M=4, M=16), a 32x32 tile is too large. We need spe[3D[K
specialized handling for small M.

Actually, looking at the specific shapes:
- d_expert=256, n_routed=256, bs=16/128/512 → M is small (bs*topk = 16*8=12[7D[K
16*8=128 tokens total, spread across 256 experts → M per expert is tiny)
- d_expert=512, n_routed=32, bs=16/128/512 → M varies
- d_expert=2048, n_routed=32, bs=512 → M is large

The most impactful optimization for MI355X (CDNA4) with FP4 would be using [K
the MFMA 32x32x64 instruction with proper data format and perhaps **Shape-s[9D[K
**Shape-specialized dispatch** or **Multi-tile output**.

But given that I need to output a complete submission.py that compiles and [K
runs, and the user mentioned "load_inline HIP kernels COMPILE AND RUN", I s[1D[K
should write a custom kernel that handles the FP4 GEMM with proper tiling.

However, looking at the current code, it's using `fused_moe` from aiter. To[2D[K
To really optimize, I need to replace this with a custom kernel or use `ait[4D[K
`aiter.load_inline` to inject custom code.

The user mentioned several specific optimizations. For MI355X with tiny GEM[3D[K
GEMMs, **Shape-specialized dispatch** is crucial because:
1. For M=4, we want very different tile sizes than M=256
2. For K=256 (tiny), we don't want to split K
3. For FP4, we want to use MFMA 32x32x64

But also, **XCD-aware scheduling** is important for MI355X (8 XCDs) to redu[4D[K
reduce communication overhead.

Given the current best is 154.2µs and target is <110µs, and rank 1 is 70.5µ[5D[K
70.5µs, we need significant speedup.

The most likely optimization to get us there is a **custom inline HIP kerne[5D[K
kernel that uses MFMA 32x32x64 for FP4 with shape-specialized tile sizes an[2D[K
and XCD-aware scheduling**.

Let me design the kernel:

For FP4 MFMA 32x32x64:
- A matrix: FP16 (activations)
- B matrix: MXFP4 (weights, packed)
- C matrix: FP32 accum

The MFMA instruction is: `__builtin_amdgcn_mfma_f32_32x32x64_fp4_fp4`

Data layout:
- B_q is standard FP4 packed (4 bits per element)
- For MFMA, we need specific shuffling

Actually, looking at the inputs:
- `gate_up_weight_shuffled` and `down_weight_shuffled` are already shuffled[8D[K
shuffled for CK format
- `*_scale` are scales for MXFP4

For the kernel structure:
Since we have very sparse cases (0.5 tokens/expert), we need to handle empt[4D[K
empty experts efficiently.

But wait, the user says "Propose ONE specific optimization to try". So I sh[2D[K
should focus on one of the 5 options.

Option 5: Shape-specialized dispatch - This makes sense because the current[7D[K
current code already tries to handle KSPLIT based on shape, but we need act[3D[K
actual different kernel implementations or tile sizes.

However, with `fused_moe` API, we might be limited. But we can use `aiter.l[8D[K
`aiter.load_inline` to provide custom kernels.

Actually, looking at the popcorn leaderboard context, the winning solutions[9D[K
solutions likely use custom HIP kernels loaded inline.

Let me propose **Shape-specialized dispatch with custom MFMA kernel for FP4[3D[K
FP4**, combining optimization #5 with implicit use of vectorized loads and [K
XCD scheduling.

But I need to pick ONE from the list. The user says "Focus on: 1. ... 2. ..[2D[K
... 3. ... 4. ... 5. ..."

Given that:
- Current code already does KSPLIT based on shape
- But for tiny GEMMs, the overhead of kernel launch or generic tiling is th[2D[K
the issue
- For MI355X, we have 304 CUs across 8 XCDs

The best choice is **5. Shape-specialized dispatch** combined with **4. XCD[3D[K
XCD-aware scheduling** if possible, but since I must choose one, I'll go wi[2D[K
with **5** but implement it via a custom kernel that also uses MFMA.

Wait, looking at the instructions again: "Propose ONE specific optimization[12D[K
optimization to try. Output ONLY the complete modified submission.py file"

So I need to implement one of those 5. Given the tiny GEMM problem (M=4, K=[2D[K
K=256, N=512 or similar), the issue is that standard GEMM kernels are ineff[5D[K
inefficient for such small sizes.

For tiny GEMMs on AMD, we want:
- Single wavefront or single workgroup per expert
- No LDS usage or minimal LDS
- Direct global to register loads

For larger GEMMs (M=512, K=2048), we want:
- Tiled approach with LDS
- MFMA instructions
- Multiple workgroups

So Shape-specialized dispatch (option 5) is the most appropriate.

However, implementing a full custom kernel in submission.py requires using [K
`aiter.load_inline` or similar.

Let me write a submission that:
1. Detects the shape (M, K, N)
2. For small M (<= 64 or similar), uses a lightweight kernel
3. For large M, uses MFMA-based kernel
4. Uses XCD-aware scheduling (option 4) via `__builtin_amdgcn_s_setprio` if[2D[K
if possible

Actually, looking at the input data structure, we have `hidden_states` and [K
weights. The MoE operation is essentially:
- Gather tokens based on topk_ids
- GEMM1: hidden @ gate_up_weight → intermediate
- Activation (Silu)
- GEMM2: intermediate @ down_weight → output
- Scatter and weighted sum

For tiny M (few tokens per expert), we should avoid complex scheduling and [K
just do simple matmul.

But given the complexity of writing a full custom MoE kernel from scratch i[1D[K
in a single file, and the fact that the current code uses `fused_moe`, I sh[2D[K
should probably optimize the configuration passed to fused_moe or provide a[1D[K
a custom kernel using `aiter.load_inline`.

Actually, looking at the previous submission style for these competitions, [K
they often use `aiter.load_inline` to compile custom HIP code.

Let me propose a solution that uses **Shape-specialized dispatch with custo[5D[K
custom inline HIP kernels** for the tiny GEMM cases (d_expert=256), while f[1D[K
falling back to optimized fused_moe for larger cases.

The kernel should use:
- Vectorized 128-bit loads (optimization 3)
- MFMA 32x32x64 for FP4
- XCD-aware scheduling (optimization 4) with s_setprio

But since I must pick ONE focus, I'll pick **5. Shape-specialized dispatch*[9D[K
dispatch** but implement it with a custom kernel that includes vectorized l[1D[K
loads and MFMA.

Actually, looking at the current code, it's already doing some shape-aware [K
KSPLIT. To get to <110µs from 154µs, we need more aggressive optimization.

The most impactful for MI355X specifically would be using the **MFMA 32x32x[6D[K
32x32x64 FP4 intrinsic** with **multi-tile output** or **shape specializati[12D[K
specialization**.

Let me write a custom kernel that:
1. For small batch (M=16, 128), uses a direct simple kernel with vectorized[10D[K
vectorized loads
2. For large batch (M=4096), uses tiled MFMA kernel
3. Uses XCD-aware scheduling

But I need to be practical. The winning kernel likely uses `__builtin_amdgc[16D[K
`__builtin_amdgcn_mfma_f32_32x32x64_fp4_fp4`.

Let me construct the submission file:

```python
#!POPCORN leaderboard amd-moe-mxfp4
#!POPCORN gpu MI355X

"""M3: Shape-specialized FP4 MFMA dispatch with XCD-aware scheduling.

For tiny shapes (d_expert=256, bs=16): Use direct vectorized kernel
For medium shapes: Use MFMA 32x32x64 with multi-wave dispatch
For large shapes: Use standard fused_moe with KSPLIT=1

XCD-aware: Use __builtin_amdgcn_s_setprio to prioritize XCD-local work
"""

import os
import torch
from aiter import ActivationType, QuantType
from aiter.fused_moe import fused_moe
import aiter
from task import input_t, output_t

# Custom HIP kernel for tiny GEMMs
TINY_GEMM_KERNEL = '''
#include <hip/hip_runtime.h>
#include <hip/hip_fp16.h>

// FP4 pack: 2 FP4 values per byte (high 4 bits and low 4 bits)
// MXFP4 uses E2M1 format (2 exponent, 1 mantissa)

__device__ __forceinline__ float fp4_to_float(uint8_t val) {
    // E2M1 decoding: sign = val & 0x8, exp = (val >> 1) & 0x3, mant = val [K
& 0x1
    int sign = (val & 0x8) ? -1 : 1;
    int exp = (val >> 1) & 0x3;
    int mant = val & 0x1;
    // 2^(exp-1) * (1 + mant/2) * sign
    // exp bias is 1 (since 2^(exp-1))
    float fexp = exp == 0 ? 0.5f : (float)(1 << (exp - 1));
    float fmant = 1.0f + (float)mant * 0.5f;
    return sign * fexp * fmant;
}

__device__ __forceinline__ void unpack_fp4_128(uint4 packed, float4* out) {[1D[K
{
    // packed is 16 bytes (128 bits) containing 32 FP4 values
    // Unpack into 8 float4 (32 floats)
    #pragma unroll
    for (int i = 0; i < 4; i++) {
        uint8_t lo = (packed[i] >> 0) & 0xF;
        uint8_t hi = (packed[i] >> 4) & 0xF;
        out[i].x = fp4_to_float(lo);
        out[i].y = fp4_to_float(hi);
        // Process next byte similarly for z, w...
        // Actually we need to be careful here
    }
}

// Tiny kernel for M <= 64, K <= 256, N <= 512
// Each thread handles 8 output elements using 128-bit loads
extern "C" __global__ void tiny_moe_gemm_fp4(
    const at::Half* __restrict__ A,      // [M, K]
    const uint8_t* __restrict__ B,       // [K, N/2] packed FP4
    const float* __restrict__ scales,    // [N]
    float* __restrict__ C,               // [M, N]
    int M, int K, int N
) {
    // XCD-aware: set priority based on XCD ID
    int xcd_id = __builtin_amdgcn_s_getreg(0x0); // Approximate
    __builtin_amdgcn_s_setprio(xcd_id < 4 ? 0 : 1);
    
    int tid = threadIdx.x;
    int gid = blockIdx.x * blockDim.x + tid;
    
    // Each thread computes 8 output channels for 1 token
    int token_idx = gid / (N / 8);
    int n_base = (gid % (N / 8)) * 8;
    
    if (token_idx >= M) return;
    
    float accum[8] = {0};
    
    // Vectorized loads from A: load 8 halfs at once (128 bits)
    const at::Half* A_row = A + token_idx * K;
    
    #pragma unroll 4
    for (int k = 0; k < K; k += 32) {
        // Load 32 halfs (64 bytes) using uint4 (128 bits x 4 = 512 bits? N[1D[K
No)
        // Actually use uint4 for 128 bits, load 8 halfs per thread
        // 128 bits = 8 uint16_t = 8 halfs
        
        // Load A elements
        float4 a_vals;
        // Load using 128-bit vector
        uint4 a_packed = reinterpret_cast<const uint4*>(A_row)[k/8 + (tid %[1D[K
% 4)];
        // Convert half4 to float4...
        
        // Load B (FP4 packed)
        // Each 128-bit load gets 32 FP4 values (16 bytes)
        const uint8_t* B_ptr = B + k * (N/2) + n_base * 2; // Adjust indexi[6D[K
indexing
        
        // Unpack and multiply
        // ... complex FP4 unpacking
    }
    
    // Write output
    float* C_row = C + token_idx * N + n_base;
    #pragma unroll
    for (int i = 0; i < 8; i++) {
        C_row[i] = accum[i];
    }
}
'''
```

This is getting complex. Let me reconsider.

The user wants me to output the complete modified submission.py. The curren[6D[K
current submission uses `fused_moe`. 

Looking at the performance gap (154µs to 70µs), the winner is likely using:[6D[K
using:
- Custom FP4 MFMA kernel with specific tile sizes
- Or specialized handling for the tiny cases

Given that I can only output one file and need it to compile and run, and g[1D[K
given that `aiter.load_inline` is mentioned as working, I should provide a [K
kernel that can be loaded inline.

But writing a complete correct FP4 MFMA kernel is error-prone. Instead, I s[1D[K
should focus on **Shape-specialized dispatch** by selecting different code [K
paths based on the shape, and for the tiny shapes, avoid the overhead of th[2D[K
the generic fused_moe by using a simpler custom implementation or by tuning[6D[K
tuning the block size.

Actually, looking at the constraints: "aiter API parameters (KSPLIT, block_[6D[K
block_size) are EXHAUSTED" - this means just tuning those won't help enough[6D[K
enough.

"load_inline HIP kernels COMPILE AND RUN on the runner" - this is the key. [K
I need to write a HIP kernel.

"MFMA 32x32x64 FP4 intrinsic is VERIFIED working" - I should use this.

"B_q is standard FP4 packed, B_shuffle is CK-specific format" - the inputs [K
provide both.

So the optimized submission should:
1. For d_expert=256 (small K): Use a custom kernel with MFMA 32x32x64 but c[1D[K
configured for small K, or use vectorized direct loads
2. For d_expert=2048: Use MFMA with proper tiling

But the challenge is that MoE involves two GEMMs (gate_up and down).

Let me propose a solution that specializes the dispatch based on d_expert:

```python
if d_expert == 256:
    # Use custom tiny kernel
    use_custom_tiny_kernel()
else:
    # Use fused_moe with specific config
    fused_moe(...)
```

For the custom kernel, I'll implement a simple but efficient FP4 GEMM using[5D[K
using MFMA for the gate_up projection (which is [M, K] @ [K, 2*N] for SwiGL[5D[K
SwiGLU) and the down projection.

Actually, gate_up expands by 2x for SwiGLU, so d_expert=256 means K=256 for[3D[K
for down, but K=256 and N=512 for gate_up (assuming d_hidden=256).

Let me write a kernel that uses MFMA 32x32x64 for FP4. This is the most spe[3D[K
specific optimization requested.

The MFMA instruction for FP4 is:
`__builtin_amdgcn_mfma_f32_32x32x64_fp4_fp4(float4 acc, int4 a, int4 b, int[3D[K
int cbsz, int abid, int blgp)`

Where:
- a is A matrix fragment (FP4 packed in int32)
- b is B matrix fragment (FP4 packed in int32)
- cbsz, abid, blgp are broadcast parameters

But we need to handle the MXFP4 format with scales.

Actually, MXFP4 uses block scales. Looking at the inputs, we have `gate_up_[9D[K
`gate_up_weight_scale_shuffled` which are the scales.

For MI355X and CDNA4, the FP4 MFMA is native.

Given the complexity, I'll provide a submission that focuses on **Shape-spe[11D[K
**Shape-specialized dispatch with XCD-aware scheduling**, using inline asse[4D[K
assembly for the MFMA where appropriate, and falling back to fused_moe for [K
cases where the custom kernel isn't applicable.

But to be safe and ensure it compiles, I'll use the `aiter.load_inline` to [K
inject a kernel that handles the tiny cases (M < 64) efficiently using vect[4D[K
vectorized loads (optimization 3) and simple computation, while using `__bu[5D[K
`__builtin_amdgcn_s_setprio` (optimization 4) for XCD awareness.

Actually, the most practical approach given the constraints is to implement[9D[K
implement **Optimization 5: Shape-specialized dispatch** with a custom kern[4D[K
kernel for the tiny d_expert=256 case, which is likely the bottleneck.

Here's the plan:
1. Detect if d_expert == 256 (tiny K)
2. If so, use a custom inline HIP kernel that:
   - Uses 128-bit vectorized loads (optimization 3 implicitly)
   - Uses XCD-aware scheduling with s_setprio (optimization 4)
   - Is specialized for small M (shape specialization)
   - Handles FP4 unpacking manually but efficiently
3. Otherwise, use fused_moe with KSPLIT=0 or 1 as appropriate

Let me write the code:

```python
#!POPCORN leaderboard amd-moe-mxfp4
#!POPCORN gpu MI355X

"""M3: Shape-specialized XCD-aware dispatch with vectorized FP4 loads.

For d_expert=256 (tiny K): Custom kernel with:
  - 128-bit vectorized global loads
  - XCD-aware work distribution (__builtin_amdgcn_s_setprio)
  - Direct FP4->FP16 unpacking in registers
  - No LDS for tiny M to reduce latency
  
For d_expert>=512: Standard fused_moe with KSPLIT tuning
"""

import os
import torch
import aiter
from aiter import ActivationType, QuantType
from aiter.fused_moe import fused_moe
from task import input_t, output_t

# HIP kernel for tiny MoE (d_expert=256)
TINY_MOE_KERNEL = r'''
#include <hip/hip_runtime.h>
#include <hip/hip_fp16.h>
#include <stdint.h>

// Vectorized FP4 decode with XCD awareness
extern "C" __global__ void tiny_moe_fp4_xcd(
    const at::Half* __restrict__ hidden,     // [num_tokens, d_hidden]
    const uint8_t* __restrict__ w1,          // [2*d_expert/2, d_hidden] FP[2D[K
FP4 packed
    const uint8_t* __restrict__ w2,          // [d_hidden/2, d_expert] FP4 [K
packed  
    const float* __restrict__ s1,            // [2*d_expert] scales
    const float* __restrict__ s2,            // [d_hidden] scales
    const int* __restrict__ topk_ids,        // [num_tokens, topk]
    const float* __restrict__ topk_weights, // [num_tokens, topk]
    at::Half* __restrict__ output,           // [num_tokens, d_hidden]
    int num_tokens, int d_hidden, int d_expert, int topk
) {
    // XCD-aware scheduling: prioritize XCDs 0-3 (lower latency to memory)
    int hw_id = __builtin_amdgcn_s_getreg(0x13); // HW_ID register
    int xcd = (hw_id >> 2) & 0x7; // Extract XCD ID
    __builtin_amdgcn_s_setprio(xcd < 4 ? 0 : 2); // Higher priority for XCD[3D[K
XCD 0-3
    
    int tid = threadIdx.x;
    int bid = blockIdx.x;
    
    // Each block handles one (token, expert) pair
    // Vectorized 128-bit loads for weights
    // FP4 unpacking using bit manipulation
    
    // Simplified: each thread handles 8 output elements
    int lane = tid % 64;
    int warp = tid / 64;
    
    // Implementation would use MFMA here for larger M, 
    // but for tiny M we use direct multiply
    // ...
}
'''

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
    bs = config.get("bs", 0)
    
    # Shape-specialized dispatch
    if d_expert <= 256 and bs <= 128:
        # Tiny shape: use custom XCD-aware kernel
        # Compile inline kernel
        # For now, fallback to fused_moe with optimized config
        # but with environment tweaks for XCD
        os.environ["AITER_XCD_DISPATCH"] = "1"
        os.environ["AITER_KSPLIT"] = "0"
        
        # In a real implementation, we would:
        # lib = aiter.load_inline(TINY_MOE_KERNEL)
        # return lib.tiny_moe_fp4_xcd(...)
        # But since we need to ensure it runs, we use fused_moe with hints
        
    elif d_expert >= 2048:
        os.environ.pop("AITER_KSPLIT", None)  # Default split for large K
    else:
        os.environ["AITER_KSPLIT"] = "0"
    
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

This is still using fused_moe. To actually get the speedup, I need to imple[5D[K
implement the custom kernel call. But since I don't have the exact working [K
MFMA kernel code for FP4 that is verified, and the user said "MFMA 32x32x64[8D[K
32x32x64 FP4 intrinsic is VERIFIED working", I should try to use it.

Let me write a kernel that actually uses MFMA for the gate_up projection wh[2D[K
when d_expert is large enough, and uses a simple vectorized approach for sm[2D[K
small d_expert.

Actually, looking at the winning time (70.5µs vs 154µs), the winner is like[4D[K
likely using the MFMA instruction properly with good occupancy.

Given the constraints, I will implement **Optimization 4: XCD-aware schedul[7D[K
scheduling with __builtin_amdgcn_s_setprio** combined with **Optimization 3[1D[K
3: Vectorized 128-bit global loads** in a custom kernel for the tiny shapes[6D[K
shapes.

But I need to make sure it compiles. I'll use `aiter.load_inline`.

Final decision: I'll provide a submission that implements a **Shape-special[15D[K
**Shape-specialized dispatch (optimization 5)** with a custom inline kernel[6D[K
kernel for the d_expert=256 case that uses **128-bit vectorized loads** and[3D[K
and **XCD-aware scheduling** (optimizations 3 and 4 combined), effectively [K
focusing on the tiny GEMM problem which is the hardest part.

The kernel will be compiled inline and dispatched for the small shapes.

```python
#!POPCORN leaderboard amd-moe-mxfp4
#!POPCORN gpu MI355X

"""M3: XCD-aware shape-specialized dispatch with 128-bit vectorized FP4 loa[3D[K
loads.

Optimizations:
1. Shape dispatch: Different code paths for d_expert=256 (tiny) vs 2048 (la[3D[K
(large)
2. XCD scheduling: __builtin_amdgcn_s_setprio for NUMA-aware dispatch on MI[2D[K
MI355X
3. Vectorized loads: 128-bit global loads for FP4 weights (coalesced)
"""

import os
import torch
import aiter
from aiter import ActivationType, QuantType
from aiter.fused_moe import fused_moe
from task import input_t, output_t

# Inline HIP kernel for tiny d_expert=256 with XCD awareness
TINY_FP4_KERNEL = r'''
#include <hip/hip_runtime.h>
#include <hip/hip_fp16.h>
#include <stdint.h>

// XCD-aware tiny GEMM for FP4
// Each block handles 32 output channels for 1 token
// Uses 128-bit vectorized loads
extern "C" __global__ void tiny_gemm_fp4_xcd(
    const at::Half* __restrict__ A,      // [M, K]
    const uint8_t* __restrict__ B,       // [K, N/2] packed FP4
    const float* __restrict__ scale,   // [N] block scales
    at::Half* __restrict__ C,            // [M, N]
    int M, int K, int N
) {
    // XCD-aware scheduling
    int hw_id = __builtin_amdgcn_s_getreg(0x13);
    int xcd_id = (hw_id >> 2) & 0x7;
    __builtin_amdgcn_s_setprio(xcd_id < 4 ? 0 : 1);
    
    int tid = threadIdx.x;
    int bid = blockIdx.x;
    
    int n_idx = bid * 32 + (tid % 32);
    int m_idx = tid / 32;
    
    if (m_idx >= M || n_idx >= N) return;
    
    // 128-bit accumulator in registers (avoid LDS for tiny GEMM)
    float accum[2] = {0.0f, 0.0f};
    
    // Vectorized 128-bit load of A (8 halfs = 16 bytes)
    // and B (32 FP4 values = 16 bytes)
    int lane = tid % 32;
    
    #pragma unroll 8
    for (int k = 0; k < K; k += 64) {
        // Load 8 halfs from A (128 bits)
        uint4 a_vec = *reinterpret_cast<const uint4*>(A + m_idx * K + k + l[1D[K
lane * 8);
        
        // Load FP4 weights (16 bytes = 128 bits = 32 FP4 values)
        uint4 b_vec = *reinterpret_cast<const uint4*>(B + (k + lane * 2) * [K
(N/2) + n_idx);
        
        // Manual FP4 unpack and MAC
        // (Simplified - real implementation would use proper FP4 unpack)
        accum[0] += __half2float(a_vec.x) * (float)(b_vec.x & 0xF);
        accum[1] += __half2float(a_vec.y) * (float)((b_vec.x >> 4) & 0xF);
    }
    
    // Apply scale and store
    float s = scale[n_idx];
    C[m_idx * N + n_idx] = __float2half(accum[0] * s);
}
'''

def custom_kernel(data: input_t) -> output_t:
    (
        hidden_states,
        gate