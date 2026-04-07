#!POPCORN leaderboard amd-moe-mxfp4
#!POPCORN gpu MI355X

Thinking...
The user wants me to optimize an AMD MI355X GPU kernel for MoE (Mixture of [K
Experts) operations. The current submission is using the `aiter` library's [K
`fused_moe` function with some environment variable tuning for KSPLIT.

Current state:
- Target: <110µs geomean (currently at 154.2µs, rank 1 is at 70.5µs)
- GPU: AMD MI355X (gfx950, CDNA4, 304 CUs, 8 XCDs)
- Current approach uses `aiter.fused_moe` with KSPLIT tuning based on exper[5D[K
expert dimension
- The problem mentions that aiter API parameters are exhausted, so I need t[1D[K
to use load_inline HIP kernels
- MFMA 32x32x64 FP4 intrinsic is verified working
- B_q is standard FP4 packed, B_shuffle is CK-specific format

The user asks for ONE specific optimization from the list:
1. LDS double-buffering for coalesced memory access
2. Multi-tile output (32x128) for A data reuse
3. Vectorized 128-bit global loads
4. XCD-aware scheduling with __builtin_amdgcn_s_setprio
5. Shape-specialized dispatch (different tile sizes for M=4 vs M=256)

Given the context:
- The current solution is using high-level `fused_moe` from aiter
- To implement low-level optimizations like LDS double-buffering, multi-til[9D[K
multi-tile output, vectorized loads, or XCD-aware scheduling, I need to wri[3D[K
write custom HIP kernels using `torch.utils.cpp_extension.load_inline`
- The shapes mentioned are tiny (M=16, K=256, N=256) to medium (M=512, K=20[4D[K
K=2048, N=32)
- FP4 quantization is involved

Looking at the options:
1. LDS double-buffering - good for hiding latency but might be complex for [K
first optimization
2. Multi-tile output (32x128) - good for A data reuse, suitable for small M[1D[K
M
3. Vectorized 128-bit global loads - helps with memory bandwidth
4. XCD-aware scheduling - MI355X has 8 XCDs, important for dispatch
5. Shape-specialized dispatch - this is crucial given the wide range of sha[3D[K
shapes (M=16 to M=512)

Given that the current KSPLIT approach is already trying to handle shape sp[2D[K
specialization at a high level, but the user mentions "Shape-specialized di[2D[K
dispatch" as option 5, and the shapes vary wildly (M=4 vs M=256 mentioned i[1D[K
in the options), I think the best approach is to implement a custom HIP ker[3D[K
kernel that handles the FP4 GEMM with shape-specific optimizations.

However, looking at the problem more carefully: the current code uses `aite[5D[K
`aiter.fused_moe` which is a high-level API. The user says "aiter API param[5D[K
parameters are EXHAUSTED", implying we can't squeeze more performance from [K
the high-level API. We need to write a custom kernel using `load_inline`.

For MI355X (CDNA4) with FP4 support, I should write a kernel that:
1. Uses MFMA 32x32x64 for FP4 computation
2. Handles the specific shapes efficiently
3. Uses vectorized loads (128-bit) for the weights
4. Implements proper LDS usage for double buffering

But the user asks for ONE specific optimization. Let me pick the most impac[5D[K
impactful one for the given shapes.

Given shapes:
- d_expert=256, n_routed=256, bs=16/128/512 → M is batch size (16, 128, 512[3D[K
512), K=256, N=256 (number of experts)
- d_expert=512, n_routed=32, bs=16/128/512 → K=512, N=32
- d_expert=2048, n_routed=32, bs=512 → K=2048, N=32, M=512

Wait, I need to understand the MoE dimensions correctly:
- hidden_states shape: [M, K] where K is d_hidden
- gate_up_weight shape: [N, K, 2*d_expert] or similar? Actually for MoE:
  - Input: [M, K]
  - Gate/Up weight: [num_experts, K, intermediate_dim*2] (for gated activat[7D[K
activation)
  - Down weight: [num_experts, intermediate_dim, K]
  
But in the code, `d_expert` seems to be the intermediate dimension. The sha[3D[K
shapes mentioned:
- d_expert=256 with n_routed=256: This suggests K=256 (expert dim), N=256 ([1D[K
(num experts being routed)
- Actually reading the comments: "d_expert=256, n_routed=256" - d_expert is[2D[K
is likely the intermediate dimension, n_routed is the number of experts bei[3D[K
being routed.

For the GEMM inside MoE:
- Typically: X @ W where X is [M, K] and W is [K, N] for each expert
- But in MoE, we have multiple experts, so it's a batched GEMM or grouped G[1D[K
GEMM

Actually, looking at the code: `gate_up_weight_shuffled` and `down_weight_s[14D[K
`down_weight_shuffled` - these are likely pre-shuffled for better access pa[2D[K
patterns.

The key insight is that for small M (16, 128) and small K (256), we need di[2D[K
different strategies than for large M (512) and large K (2048).

Option 5 "Shape-specialized dispatch" seems most appropriate because:
1. The shapes vary significantly (M=16 vs M=512)
2. Different tile sizes are needed for efficiency
3. For tiny M (16), we might want single-wave execution with specific WG si[2D[K
size
4. For larger M (512), we want multi-wave with different tiling

However, to implement this properly with load_inline, I need to write a cus[3D[K
custom kernel that handles the FP4 quantized GEMM with MFMA instructions.

Let me design a kernel that:
1. Detects the shape (M dimension) and dispatches to different tile configu[7D[K
configurations
2. Uses vectorized 128-bit loads (option 3) for the weights
3. Uses MFMA 32x32x64 for computation
4. Implements proper LDS tiling

Actually, the user asks for ONE specific optimization. Let me choose "Shape[6D[K
"Shape-specialized dispatch" with different tile sizes, but implement it wi[2D[K
with a custom HIP kernel that also uses vectorized loads and MFMA.

Wait, I need to be careful. The current code uses `aiter.fused_moe`. If I r[1D[K
replace it entirely with a custom kernel, I need to make sure I handle all [K
the quantization scales and shuffling correctly.

Looking at the parameters:
- `gate_up_weight_shuffled`: shuffled weights for better access
- `gate_up_weight_scale_shuffled`: scales for quantization
- `QuantType.per_1x32`: per-block quantization

For MI355X CDNA4, FP4 MFMA 32x32x64 is native. The format is 4-bit per elem[4D[K
element, packed 2 per byte.

Let me write a custom kernel that:
1. Implements shape-specialized dispatch (different block sizes for M=16 vs[2D[K
vs M=512)
2. Uses vectorized 128-bit loads (4xFP4 or 8xFP4 depending on packing)
3. Uses LDS for double buffering (pipelining the next tile while computing [K
current)
4. Targets MFMA 32x32x64

Actually, for FP4 MFMA 32x32x64:
- A matrix: 32 rows x 64 columns of FP4 (packed as 32 x 32 bytes?)
- Wait, MFMA 32x32x64 for FP4:
  - A is 32x64 elements of FP4 (packed 2 per byte) = 32 x 32 bytes = 1024 b[1D[K
bytes
  - B is 64x32 elements of FP4 = 64 x 16 bytes = 1024 bytes
  - C is 32x32 FP32 = 4096 bytes

But FP4 is 4-bit, so 2 elements per byte.
MFMA 32x32x64 means:
- A: 32 rows, 64 cols (K dimension)
- B: 64 rows, 32 cols (N dimension)  
- C: 32 rows, 32 cols

For FP4, the K dimension in elements is 64, which is 32 bytes per row for A[1D[K
A.

Now, for the kernel structure:
- Each workgroup processes a tile of the output
- For small M (16), we might have only 16 rows, so we need to handle partia[6D[K
partial tiles or use different tile sizes
- For M=16, K=256, N=256: this is a small GEMM

Actually, looking at the MoE structure again:
- `topk_ids` indicates which experts are used
- `topk_weights` are the gating weights
- `n_routed` is the number of experts actually routed (topk)

So the GEMM is: for each token, for each selected expert, do the matmul. Th[2D[K
This is essentially a grouped GEMM or can be seen as a sparse GEMM.

But the `fused_moe` function likely handles the routing and gathering.

Given the complexity of reimplementing the full fused_moe from scratch, and[3D[K
and since the user mentions "load_inline HIP kernels COMPILE AND RUN on the[3D[K
the runner", I should write a kernel that replaces or augments the current [K
approach.

However, looking at the constraints and the fact that aiter is already bein[4D[K
being used, perhaps the best approach is to write a specialized kernel for [K
the specific problematic shapes and fall back to aiter for others? Or write[5D[K
write a fully custom implementation?

Given the target is <110µs and current is 154.2µs, I need a significant spe[3D[K
speedup (~30%).

Let me propose a solution that uses:
- Shape-specialized dispatch with custom tile sizes
- Vectorized 128-bit global loads for the weights
- LDS double buffering to hide latency
- MFMA 32x32x64 for computation

But I can only pick ONE specific optimization focus. The user says: "Focus [K
on: 1. ... 2. ... 3. ... 4. ... 5. ..."

I'll pick option 5 (Shape-specialized dispatch) combined with option 3 (Vec[4D[K
(Vectorized loads) since they work well together, but the primary focus is [K
shape specialization with different tile sizes for different M.

Actually, looking at the MFMA constraint: MFMA 32x32x64.
- For M=16 (small), we can't even fill one MFMA block in the M dimension (3[2D[K
(32).
- This suggests we need to handle small M differently, perhaps by having mu[2D[K
multiple N blocks per workgroup to utilize the compute better, or by using [K
a different layout.

For small M (16) and large N (256), we want to process multiple N tiles per[3D[K
per workgroup to amortize the A matrix loading.
For large M (512) and small N (32), we want different parallelism.

Let me write a custom kernel that:
1. Detects M and dispatches to different configurations
2. Uses inline assembly or HIP intrinsics for MFMA
3. Handles FP4 loading with 128-bit vectors (8 bytes = 16 FP4 elements per [K
load)

The kernel structure:
- For small M (<=32): Use 1 warp per tile, process multiple N tiles, load A[1D[K
A into registers once, reuse across N tiles
- For large M (>32): Use multiple warps, standard tiling

But actually, for MI355X, we have 304 CUs, so occupancy is important.

Let me write the code. I'll use `torch.utils.cpp_extension.load_inline` to [K
compile a custom HIP kernel at runtime.

The kernel will implement a specialized FP4 GEMM for the MoE weights applic[6D[K
application.

Key features:
1. Shape detection and dispatch to specialized paths
2. 128-bit vectorized loads (`float4` or `__attribute__((vector_size(16)))`[34D[K
`__attribute__((vector_size(16)))`)
3. MFMA 32x32x64 intrinsics (`__builtin_amdgcn_mfma_f32_32x32x64_fp4`)
4. LDS double buffering for A matrix (ping-pong buffers)

Wait, I need to check the exact MFMA intrinsic for FP4 on CDNA4. It should [K
be something like:
`__builtin_amdgcn_mfma_f32_32x32x64_fp4_fp4`

Actually, looking up CDNA4/MI355X MFMA instructions:
- FP4 MFMA is 32x32x64 (A: 32x64 FP4, B: 64x32 FP4, C: 32x32x4 F32 accum)
- Intrinsic: `__builtin_amdgcn_mfma_f32_32x32x64_fp4_fp4`

For the FP4 format: packed 2 per byte, [3:0] and [7:4].

Now, for the kernel implementation:

```cpp
extern "C" __global__ void moe_gemm_shape_specialized(
    half* __restrict__ C,
    const half* __restrict__ A,
    const uint8_t* __restrict__ B_q,  // FP4 quantized
    const float* __restrict__ B_scale, // per 1x32 or per 32x32?
    int M, int N, int K,
    int num_experts,
    const int* __restrict__ expert_ids,
    const float* __restrict__ topk_weights,
    int topk
) {
    // Implementation here
}
```

But this is getting complex. Given the time, I should provide a complete, w[1D[K
working submission.py that:
1. Uses load_inline to compile a custom kernel
2. Implements shape-specialized dispatch
3. Uses the optimizations mentioned

Actually, looking at the current code again, it uses `fused_moe` from aiter[5D[K
aiter. To beat 154µs and reach <110µs, I likely need to replace the fused_m[7D[K
fused_moe call with a custom implementation for at least some shapes, or en[2D[K
enhance it.

But given the complexity of reimplementing the entire MoE fusion, and since[5D[K
since the user mentions the shapes specifically, perhaps the best approach [K
is to write a custom kernel for the specific shapes and dispatch accordingl[10D[K
accordingly.

Let me provide a solution that focuses on "Shape-specialized dispatch with [K
vectorized loads and MFMA optimization".

The code will:
1. Check the input shape
2. For small shapes (d_expert=256), use a specialized kernel with small til[3D[K
tiles and no split
3. For large shapes (d_expert=2048), use larger tiles
4. Use inline HIP kernel with 128-bit loads and MFMA intrinsics

Here's my plan for the kernel:
- Tile size: For M<=128, use M_tile=16 or 32. For M>128, use M_tile=64 or 1[1D[K
128.
- K_tile: 64 (to match MFMA K dimension)
- N_tile: 32 (to match MFMA N dimension)
- Load B (weights) using float4 (128 bits) = 32 bytes = 64 FP4 elements
- This matches K_tile=64!

So each load brings in 64 K elements for one N element.
Actually, B is [K, N] or [N, K]?
In standard GEMM C[M, N] = A[M, K] @ B[K, N]
If B is FP4, each column has K elements.
With