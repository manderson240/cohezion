#!POPCORN leaderboard amd-moe-mxfp4
#!POPCORN gpu MI355X

Thinking...
The user wants me to optimize an AMD MI355X GPU kernel for MoE (Mixture of [K
Experts) operations. The current submission uses AITER's fused_moe but is a[1D[K
achieving 154.2µs while the target is <110µs and rank 1 is at 70.5µs.

Key observations:
1. The shapes involve tiny GEMMs (d_expert=256, n_routed=256, bs=16/128/512[13D[K
bs=16/128/512)
2. Very sparse scenarios (0.5 tokens/expert)
3. Using MXFP4 quantization
4. MI355X has specific architecture: gfx950, CDNA4, 304 CUs, 8 XCDs
5. MFMA 32x32x64 FP4 intrinsic works
6. B_q is standard FP4 packed, B_shuffle is CK-specific format

The user wants ONE specific optimization from the list:
1. LDS double-buffering for coalesced memory access
2. Multi-tile output (32x128) for A data reuse
3. Vectorized 128-bit global loads
4. XCD-aware scheduling with __builtin_amdgcn_s_setprio
5. Shape-specialized dispatch (different tile sizes for M=4 vs M=256)

Given the context:
- Current code uses AITER's fused_moe which is a high-level API
- To implement low-level optimizations like LDS double-buffering, multi-til[9D[K
multi-tile output, vectorized loads, or XCD-aware scheduling, I need to wri[3D[K
write custom HIP kernels using load_inline
- The constraint says "load_inline HIP kernels COMPILE AND RUN on the runne[5D[K
runner"
- The shapes are very small (M can be as small as 4 or 16, K=256, N=256 or [K
similar)

For tiny GEMMs and sparse MoE, the main bottleneck is likely:
1. Launch overhead
2. Memory coalescing 
3. Work distribution across CUs (load balancing for sparse cases)

Option 4 (XCD-aware scheduling) seems promising for the MI355X specifically[12D[K
specifically since it has 8 XCDs and the problem is sparse. Using __builtin[9D[K
__builtin_amdgcn_s_setprio can help with scheduling.

However, looking at the problem more carefully:
- The current approach uses AITER's fused_moe which likely uses CK (Composa[8D[K
(Composable Kernel) implementations
- For the rank 1 performance of 70.5µs vs current 154.2µs, we need ~2.2x sp[2D[K
speedup
- The key insight in the comments is that for d_expert=256, K=256 is very s[1D[K
small, and KSPLIT=0 helps
- But also for sparse cases (bs=16, topk=8, 256 experts), we have very few [K
tokens per expert

The most impactful optimization for MI355X (CDNA4) with tiny GEMMs and spar[4D[K
sparse patterns would likely be **Shape-specialized dispatch with custom ti[2D[K
tile sizes**, particularly:
- For M=4 or small M: use different tile dimensions (e.g., 4x128 or 8x128 i[1D[K
instead of 32x32)
- For M=128/512: use larger tiles
- Use vectorized loads (128-bit) to maximize memory bandwidth
- Use XCD-aware scheduling to distribute sparse work efficiently across the[3D[K
the 8 XCDs

But I need to write this as a custom kernel using load_inline since the AIT[3D[K
AITER API is exhausted.

Actually, looking at the constraints again: "aiter API parameters (KSPLIT, [K
block_size) are EXHAUSTED" - this suggests we cannot tune AITER parameters [K
further and need to write custom inline HIP code.

The most promising single optimization for MI355X with MXFP4 and tiny GEMMs[5D[K
GEMMs is **Shape-specialized dispatch with custom MFMA-based kernel**, spec[4D[K
specifically optimizing for the tiny M cases (M=4, M=16) which are problema[8D[K
problematic for standard GEMM implementations.

However, given the complexity of writing a full custom MoE kernel from scra[4D[K
scratch in a single response, and the fact that the user wants the complete[8D[K
complete modified submission.py, I should write a kernel that:
1. Handles the MoE routing manually
2. Uses MFMA 32x32x64 for FP4 computation
3. Uses vectorized 128-bit loads
4. Implements proper LDS usage
5. Uses shape-specific tile sizes

But wait, the user said "Propose ONE specific optimization". So I should fo[2D[K
focus on one of the 5 listed. 

Given the MI355X architecture (CDNA4) and the tiny GEMM sizes, **Shape-spec[12D[K
**Shape-specialized dispatch (option 5)** is likely the best choice because[7D[K
because:
- M=4 and M=16 are too small for standard 32x32 tiles
- We need different tile configurations for different batch sizes
- We can dispatch to optimized kernels based on the actual M size per exper[5D[K
expert

However, implementing shape specialization requires writing multiple kernel[6D[K
kernel variants or a kernel template that handles different sizes efficient[9D[K
efficiently.

Let me reconsider the XCD-aware scheduling (option 4). For sparse MoE where[5D[K
where experts get very few tokens (0.5 tokens/expert), the distribution of [K
work across the 8 XCDs (304 CUs total) is crucial. If we don't distribute p[1D[K
properly, many CUs will be idle. Using __builtin_amdgcn_s_setprio can help [K
the scheduler.

But actually, for FP4 tiny GEMMs, the memory access pattern is critical. **[2D[K
**Vectorized 128-bit global loads (option 3)** combined with proper LDS usa[3D[K
usage would help the memory bandwidth.

Given that the user mentions "MFMA 32x32x64 FP4 intrinsic is VERIFIED worki[5D[K
working" and "B_q is standard FP4 packed, B_shuffle is CK-specific format",[8D[K
format", I should write a custom kernel that:
1. Manually handles the FP4 dequantization
2. Uses the MFMA instruction
3. Optimizes for the specific shapes

Let me choose **Shape-specialized dispatch with multi-tile output and vecto[5D[K
vectorized loads** as the primary optimization, since the shapes vary signi[5D[K
significantly (M=4/16 vs M=512).

Actually, looking at the rank 1 time (70.5µs) vs current (154.2µs), we need[4D[K
need a 2.2x improvement. This is substantial. The current code uses AITER's[7D[K
AITER's fused_moe which is likely not optimally handling the tiny M cases.

I will write a custom inline HIP kernel that:
1. Uses shape-specialized dispatch (different block sizes for different M)
2. Implements vectorized 128-bit loads (4xFP4 = 16 bytes = 128 bits)
3. Uses LDS for weights
4. Handles the MFMA 32x32x64 for accumulation

But given the complexity, I'll focus on the dispatch logic and a specialize[10D[K
specialized kernel for the tiny M case (M <= 32) which is likely the bottle[6D[K
bottleneck.

Wait, I should reconsider the constraints. The submission uses `fused_moe` [K
from aiter. The user says "aiter API parameters (KSPLIT, block_size) are EX[2D[K
EXHAUSTED". This means we cannot get more performance from tuning those par[3D[K
parameters.

The user wants me to propose a specific optimization from the list and outp[4D[K
output the complete modified submission.py.

Given that:
1. The current code uses Python environment variables to control KSPLIT
2. The rank 1 is at 70.5µs (much faster)
3. We need to write load_inline HIP kernels

The best approach is to write a custom kernel that replaces fused_moe for s[1D[K
specific shapes, or augment it.

However, writing a full custom MoE kernel that beats AITER's optimized CK i[1D[K
implementation is very challenging. But the comment says "load_inline HIP k[1D[K
kernels COMPILE AND RUN on the runner", which suggests we can write custom [K
kernels.

Let me look at the shapes again:
- d_expert=256, n_routed=256, bs=16/128/512
- d_expert=512, n_routed=32, bs=16/128/512  
- d_expert=2048, n_routed=32, bs=512

For the first shape (256, 256), if bs=16 and topk=8, we have 128 tokens rou[3D[K
routed to 256 experts. That's extremely sparse.

For such sparse cases, a "persistent kernel" or "tile-based" approach where[5D[K
where we process multiple experts per block might be better than launching [K
separate blocks per expert.

The optimization **XCD-aware scheduling with __builtin_amdgcn_s_setprio** ([1D[K
(option 4) is specifically for distributing work across the 8 XCDs to avoid[5D[K
avoid starvation and improve occupancy for sparse workloads.

But **Shape-specialized dispatch** (option 5) is more general and likely mo[2D[K
more impactful.

Given the instruction "Propose ONE specific optimization", I will go with *[1D[K
**Shape-specialized dispatch with vectorized loads and optimized tile sizes[5D[K
sizes for tiny M**, which combines aspects of options 3 and 5.

Actually, looking at the MFMA 32x32x64 FP4 instruction: this processes 32x3[4D[K
32x32 output tiles with 64 K accumulation. For FP4, each lane holds 2xFP4 e[1D[K
elements in a 32-wide wavefront? No, for FP4 MFMA 32x32x64:
- A is 32x64 (FP4)
- B is 64x32 (FP4)  
- C is 32x32 (FP32)

Given that K=256 for the first shape, we need 4 iterations of K (256/64=4).[11D[K
(256/64=4).

For tiny M (e.g., M=4), using a 32x32 output tile is wasteful (28 rows unus[4D[K
unused). We should use M=4 specialized tiles or accumulate multiple experts[7D[K
experts.

Given the complexity, I'll provide a submission that:
1. Detects small M cases
2. Uses a custom inline kernel for those cases with vectorized loads and sp[2D[K
specific unroll factors
3. Falls back to fused_moe for large M

But I need to actually write the HIP kernel code using load_inline.

Let me draft the kernel:

For the tiny M case (M <= 32), we can:
- Use