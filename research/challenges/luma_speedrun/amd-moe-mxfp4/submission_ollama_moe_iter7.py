#!POPCORN leaderboard amd-moe-mxfp4
#!POPCORN gpu MI355X

Thinking...
The user wants me to optimize an AMD MI355X GPU kernel for MoE (Mixture of [K
Experts) inference. The current submission uses AITER's fused_moe with envi[4D[K
environment variable KSPLIT tuning, achieving 154.2µs with a target of <110[4D[K
<110µs (rank 1 is 70.5µs).

Key details:
- GPU: AMD MI355X (gfx950, CDNA4, 304 CUs, 8 XCDs)
- Data format: MXFP4 (microscaling FP4)
- Current approach: Using AITER fused_moe with KSPLIT tuning
- Problem: Need to get from 154.2µs to <110µs (need ~28% improvement)
- The user mentions that AITER API parameters are exhausted, and I should f[1D[K
focus on specific optimizations like LDS double-buffering, multi-tile outpu[5D[K
output, vectorized loads, XCD-aware scheduling, or shape-specialized dispat[6D[K
dispatch.

Looking at the constraints:
1. AITER API parameters are EXHAUSTED - meaning I can't just tune the exist[5D[K
existing API more
2. load_inline HIP kernels COMPILE AND RUN - I can write custom HIP kernels[7D[K
kernels
3. MFMA 32x32x64 FP4 intrinsic is VERIFIED working - I can use MFMA [K
instructions
4. B_q is standard FP4 packed, B_shuffle is CK-specific format - need to ha[2D[K
handle tensor layouts correctly

The prompt asks for ONE specific optimization. Looking at the options:
1. LDS double-buffering for coalesced memory access
2. Multi-tile output (32x128) for A data reuse  
3. Vectorized 128-bit global loads
4. XCD-aware scheduling with __builtin_amdgcn_s_setprio
5. Shape-specialized dispatch (different tile sizes for M=4 vs M=256)

Given that this is a tiny GEMM problem (M is small: 4, 32, 64 tokens potent[6D[K
potentially, with K=256 or 2048, N=256/512/2048), the main issue is probabl[7D[K
probably:
- For small M (4, 32), we need different tile sizes than for larger M
- Memory access patterns are critical
- FP4 quantization adds complexity

Since the current submission uses the AITER fused_moe API, but the user say[3D[K
says "aiter API parameters are EXHAUSTED", they want me to write a custom k[1D[K
kernel using load_inline.

Looking at the problem sizes:
- d_expert=256, n_routed=256, bs=16/128/512 (3 shapes — tiny GEMMs!)
- d_expert=512, n_routed=32, bs=16/128/512 (3 shapes)
- d_expert=2048, n_routed=32, bs=512 (1 shape)

The critical insight is that for d_expert=256 with bs=16 and topk=8, only 1[1D[K
128 tokens are routed to 256 experts, so ~0.5 tokens/expert. This means M ([1D[K
(batch size per expert) is very small (0-1 effectively, but actually the to[2D[K
tokens are grouped).

For tiny M (like M=1,2,4), standard GEMM tiles perform poorly. We need:
1. Vectorized loads to saturate memory bandwidth
2. Special handling for small M
3. FP4 MFMA instructions for computation

The most impactful optimization would be **shape-specialized dispatch with [K
custom inline HIP kernels using MFMA and vectorized loads**, specifically h[1D[K
handling the tiny M cases (M<=4, M<=32) differently from larger M.

However, looking at the request: "Propose ONE specific optimization to try"[4D[K
try". And the options given include "Shape-specialized dispatch (different [K
tile sizes for M=4 vs M=256)".

Given that the problem has both tiny shapes (d_expert=256) and larger ones [K
(d_expert=2048), and the batch sizes vary, shape-specialized dispatch is li[2D[K
likely the highest impact.

But I need to write actual HIP kernel code using load_inline. The kernel sh[2D[K
should:
1. Use MFMA 32x32x64 FP4 instructions (as mentioned they're verified workin[6D[K
working)
2. Handle the FP4 data format (packed)
3. Use vectorized 128-bit loads (load 4xFP32 or 8xFP16 at once, but for FP4[3D[K
FP4 it's different)
4. Optimize for the specific shapes

Wait, looking at the current code, it's using fused_moe from aiter. The use[3D[K
user says "load_inline HIP kernels COMPILE AND RUN on the runner". This sug[3D[K
suggests I should write a custom kernel.

But the input data includes shuffled weights (gate_up_weight_shuffled, etc.[4D[K
etc.), which suggests the data is already prepared for CK (Composed Kernel)[7D[K
Kernel) format.

For MI355X (CDNA4), we have:
- MFMA 32x32x64 for FP4 (as stated)
- 304 CUs across 8 XCDs
- Need to handle memory coalescing well

Given the tiny GEMM nature (M is small), the bottleneck is likely memory ba[2D[K
bandwidth and launch overhead. We need:
- Vectorized loads (128-bit) to saturate HBM bandwidth
- Software pipelining with double buffering
- Specialized tiles for small M (e.g., M4, M16, M32, M64)

Since I need to provide ONE optimization, and looking at the constraints, I[1D[K
I think **shape-specialized dispatch with a custom kernel using MFMA and ve[2D[K
vectorized loads** is the way to go.

However, writing a full custom MoE kernel is complex. The kernel needs to:
- Gather tokens based on topk_ids
- Do GEMM1 (hidden @ gate_up_weight)
- Apply activation (Silu)
- Do GEMM2 (intermediate @ down_weight)
- Scatter back with topk_weights

Given the complexity, and that AITER is already being used, maybe the optim[5D[K
optimization is to call a different AITER path or use a custom kernel just [K
for the tiny shapes.

But the user says "aiter API parameters are EXHAUSTED", implying we need to[2D[K
to go lower level.

Let me think about the specific optimization. The prompt mentions "B_q is s[1D[K
standard FP4 packed, B_shuffle is CK-specific format". The weights are prov[4D[K
provided in both formats.

For tiny M (like M=4), we want to:
- Load A (activations) with vectorized loads (128-bit = 4 floats or 8 halfs[5D[K
halfs)
- Since it's FP4, each 128-bit load gets us 32 FP4 values (4 bits each = 12[2D[K
128 bits / 4 bits = 32 values)
- Use MFMA 32x32x64 to compute
- For M=4, we need to handle the fact that we don't fill the MFMA input A ([1D[K
(which expects 32 rows)

Actually, looking at MFMA 32x32x64:
- It multiplies A (32x64) @ B (64x32) -> C (32x32)
- For FP4, the K dimension is 64 (64 FP4 values = 32 bytes per row)
- But our K is 256 or 2048, which are multiples of 64.

For M=4, we only have 4 rows, but MFMA expects 32 rows. We can either:
- Zero-pad to 32 rows (wasteful)
- Use a different tile size
- Use multiple MFMAs with accumulation

But wait, for tiny M, we should probably use a smaller tile or handle multi[5D[K
multiple experts in parallel differently.

Actually, for MoE with many experts and few tokens, we want to process mult[4D[K
multiple experts in a workgroup to keep the SIMDs busy.

The most practical optimization given the constraints is to implement a **c[3D[K
**custom kernel for small M using inline assembly with MFMA and vectorized [K
loads**, with shape-specific tile selection.

But I need to write this as a complete submission.py file. The file should:[7D[K
should:
1. Check the shape (M, N, K)
2. For tiny shapes (d_expert=256), use a custom kernel
3. For larger shapes, use the standard fused_moe

Or, I could write a kernel that handles all cases but with different tile c[1D[K
configurations selected at runtime based on the actual token counts per exp[3D[K
expert.

Given that I need to output ONLY the complete modified submission.py file, [K
and it needs to compile and run, I should write a kernel using `load_inline[12D[K
`load_inline` (PyTorch's inline CUDA/HIP assembly).

The kernel structure:
```python
import torch
from torch.utils.cpp_extension import load_inline

# Define the HIP kernel source
hip_source = """
#include <hip/hip_runtime.h>
#include <hip/hip_fp16.h>
#include <hip/amd_detail/amd_hip_bf16.h>

// MFMA intrinsic for FP4 on CDNA4
// extern "C" void llvm_amdgcn_mfma_f32_32x32x64_fp4_fp4(...) or similar
// Actually, the intrinsic is __builtin_amdgcn_mfma_f32_32x32x64_f16_f16 or[2D[K
or specific for FP4
// For FP4, we need to use the specific intrinsic: __builtin_amdgcn_mfma_f3[24D[K
__builtin_amdgcn_mfma_f32_32x32x64_fp4_fp4

// Actually, looking up CDNA4/MI355X, the FP4 MFMA is:
// mfma_f32_32x32x64_fp4_fp4

// Vectorized load using float4 or uint4
// FP4 is packed, so 32 FP4 = 128 bits = 1 uint4

// Kernel for small M (M <= 32)
__global__ void tiny_moe_kernel(...) {
    // Implement gather + GEMM + scatter
}
"""
```

But this is quite involved. Let me think about what specific optimization i[1D[K
is most likely to give the ~28% speedup needed.

Given that the current code uses `AITER_KSPLIT` and the problem mentions "S[2D[K
"Shape-aware KSPLIT", but also mentions that AITER parameters are exhausted[9D[K
exhausted, I should look at the other optimizations.

Option 2: Multi-tile output (32x128) for A data reuse - this means computin[8D[K
computing multiple output tiles from the same A matrix data loaded into LDS[3D[K
LDS, improving data reuse.

Option 3: Vectorized 128-bit global loads - critical for memory bandwidth.

Option 4: XCD-aware scheduling - MI355X has 8 XCDs, scheduling work across [K
them properly can reduce inter-XCD communication.

Option 5: Shape-specialized dispatch - different code paths for M=4 vs M=25[4D[K
M=256.

Given the description mentions "tiny GEMMs" and the specific shape issues ([1D[K
(0.5 tokens/expert), the **shape-specialized dispatch** with custom tile si[2D[K
sizes is probably the most impactful. For M=4, we want very different tile [K
sizes than for M=256.

But I need to implement this. Since I can't easily modify the internal AITE[4D[K
AITER GEMM tiles without recompiling, and the prompt says to use load_inlin[10D[K
load_inline HIP kernels, I should write a custom kernel that replaces fused[5D[K
fused_moe for the tiny shapes.

Actually, looking at the input data, it seems like the data is already prep[4D[K
prepared for AITER (shuffled weights, etc.). If I write a custom kernel, I [K
need to handle the FP4 dequantization and shuffled layout myself.

Given the complexity, and that this is a competition entry, the optimizatio[11D[K
optimization is likely to add a **custom inline kernel for the specific tin[3D[K
tiny shapes** while falling back to fused_moe for larger ones.

However, implementing a full MoE kernel inline is risky for compilation tim[3D[K
time and correctness. 

Alternative interpretation: The user wants me to modify the submission to u[1D[K
use specific AITER features that are not just environment variables, but ma[2D[K
maybe different function calls or parameters that are shape-specific.

But the comment says "aiter API parameters are EXHAUSTED".

Let me reconsider. The prompt says: "load_inline HIP kernels COMPILE AND RU[2D[K
RUN on the runner". This is a strong hint that I should write a custom kern[4D[K
kernel.

The optimization I will propose is: **Shape-specialized dispatch with custo[5D[K
custom HIP inline kernels using MFMA 32x32x64 and vectorized 128-bit loads [K
for tiny M (<=32), while using standard fused_moe for larger M.**

This addresses the specific pain point mentioned: "For d_expert=256: K=256 [K
is very small... only 128 tokens total routed to 256 experts → ~0.5 tokens/[7D[K
tokens/expert."

For M=0.5 average (but actually some experts get 1, some 0), we need to han[3D[K
handle small batch sizes efficiently.

Actually, looking at the code structure, `fused_moe` likely groups tokens b[1D[K
by expert internally. So if there are 256 experts and 128 tokens, it create[6D[K
creates a sparse computation where each expert processes 0 or 1 tokens.

For M=1, standard GEMM is inefficient. We want to process multiple experts [K
in parallel within a single workgroup.

So my optimization will be:
1. Detect when the expert capacity is small (few tokens per expert)
2. Use a custom kernel that processes multiple experts per wavefront/workgr[16D[K
wavefront/workgroup using MFMA
3. Use vectorized loads for the weights (since weights are read many times)[6D[K
times)

Wait, for M=1 and K=256, N=512:
- A is 1x256 (FP16/BF16?)
- B is 256x512 (FP4)
- We want to compute A @ B

With MFMA 32x32x64:
- We can load 32 rows of B (but B is KxN, so 32 rows is 32x512)
- But we only have 1 row of A.

Actually, for GEMM with small M, we should transpose the multiplication or [K
use a different approach.

In MoE, typically:
- GEMM1: hidden_states [M, K] @ gate_up_weight [K, N] -> [M, N]
- Here M is tokens per expert (small), K is d_hidden (e.g., 256), N is inte[4D[K
intermediate (e.g., 512)

For M=1, this is a matrix-vector multiplication, which is memory bandwidth [K
bound. We want to maximize bandwidth utilization with vectorized loads and [K
process multiple experts or multiple tokens concurrently.

Given the constraints, I will implement a **custom kernel for the d_expert=[9D[K
d_expert=256 case** (the tiny GEMM case) using:
- 128-bit vectorized loads for weights
- MFMA 32x32x64 for computation
- Processing multiple experts in parallel
- Explicit XCD-aware work distribution

But writing this correctly requires knowing the exact data layouts. Since t[1D[K
the weights are provided in "shuffled" format for CK, and FP4 packed, I'll [K
assume the custom kernel needs to handle this.

Actually, to be safe and compile-able, I should write a kernel that uses th[2D[K
the standard torch.matmul but with optimized paths, but that's not a kernel[6D[K
kernel optimization.

Given the instruction "Output ONLY the complete modified submission.py file[4D[K
file", and the need for it to compile and run, I will provide a file that:
1. Includes a custom HIP kernel using load_inline
2. Detects the small shapes (d_expert <= 512 and small batch)
3. Uses the custom kernel for those
4. Falls back to fused_moe for others

The custom kernel will focus on **vectorized 128-bit loads and multi-tile o[1D[K
output** to improve memory bandwidth and A data reuse.

Actually, looking at the options again, **Multi-tile output (32x128) for A [K
data reuse** seems like a specific optimization where we load A into LDS on[2D[K
once and compute multiple output tiles (different N dimensions) from it, am[2D[K
amortizing the load cost of A.

For MoE with small M, A is small (MxK), and B is large (KxN). Loading A int[3D[K
into LDS and reusing it across multiple B tiles makes sense.

But with M small, A is not the bottleneck, B is (the weights). Weight strea[5D[K
streaming is the issue.

For small M, the bottleneck is reading the weights B. Since B is in FP4, we[2D[K
we want to read it with 128-bit loads (32 FP4 values at once) and decompres[9D[K
decompress.

The MFMA 32x32x64 instruction consumes 64 K values per row, so we want K ti[2D[K
tile of 64.

Given the complexity, and since this is a competition where rank 1 is at 70[2D[K
70.5µs (much faster), they are likely using custom MFMA kernels.

I will propose the **shape-specialized dispatch with custom MFMA kernel for[3D[K
for small M**, implementing the multi-tile optimization and vectorized load[4D[K
loads.

The code structure:
- Use torch.utils.cpp_extension.load_inline to compile a HIP kernel at runt[4D[K
runtime
- The kernel will handle the d_expert=256 case specifically
- It will use uint4 (128-bit) loads for the FP4 weights
- It will use MFMA 32x32x64 for accumulation
- It will handle the Silu activation and second GEMM (down projection) fuse[4D[K
fused

Given the token count sparsity, the kernel should be designed to process mu[2D[K
multiple experts or handle the scatter-gather efficiently.

Actually, a simpler approach that might still help: **XCD-aware scheduling*[11D[K
scheduling**. On MI355X with 8 XCDs, ensuring that workgroups working on th[2D[K
the same expert or adjacent memory are on the same XCD can improve L2 cache[5D[K
cache hit rates.

This can be done using `__builtin_amdgcn_s_setprio` for priority hints or b[1D[K
by customizing the launch grid.

But the most standard optimization is the shape-specialized dispatch.

Let me write the code focusing on:
1. Shape detection
2. Custom kernel for d_expert=256 (the tiny case)
3. Using vectorized loads and MFMA

The kernel will be written in HIP C++ and loaded via load_inline.

Key aspects of the custom kernel:
- For d_expert=256, K=256. With MFMA 32x32x64, we need 4 iterations in K (2[2D[K
(256/64=4).
- For M small, we pack multiple experts into one workgroup.
- Use 128-bit loads for weights.

Given the complexity of writing a full correct FP4 MFMA kernel without test[4D[K
testing, and since the user said "MFMA 32x32x64 FP4 intrinsic is VERIFIED w[1D[K
working", I can use it.

The intrinsic signature for FP4 MFMA on CDNA4 is likely:
`__builtin_amdgcn_mfma_f32_