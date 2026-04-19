#!POPCORN leaderboard amd-moe-mxfp4
#!POPCORN gpu MI355X

Thinking...
The user wants me to optimize an AMD MI355X GPU kernel for MoE (Mixture of [K
Experts) inference. The current submission uses `fused_moe` from aiter libr[4D[K
library with some environment variable tuning, but needs to go from 154.2µs[7D[K
154.2µs to <110µs geomean (target is 70.5µs).

Key constraints:
1. Must use aiter API or load inline HIP kernels
2. MFMA 32x32x64 FP4 intrinsic is verified working
3. B_q is standard FP4 packed, B_shuffle is CK-specific format
4. Need to optimize for specific shapes:
   - d_expert=256, n_routed=256, bs=16/128/512 (3 shapes)
   - d_expert=512, n_routed=32, bs=16/128/512 (3 shapes)
   - d_expert=2048, n_routed=32, bs=512 (1 shape)

The user suggests focusing on:
1. LDS double-buffering
2. Multi-tile output (32x128) for A data reuse
3. Vectorized 128-bit global loads
4. XCD-aware scheduling
5. Shape-specialized dispatch

Given that the current approach uses `fused_moe` from aiter, and the user m[1D[K
mentions "load_inline HIP kernels COMPILE AND RUN on the runner", I should [K
propose a custom HIP kernel that uses inline assembly or optimized HIP code[4D[K
code for the MoE computation.

However, looking at the current code, it's using `fused_moe` from aiter. To[2D[K
To achieve the speedup needed (154µs → 70µs), we likely need a custom kerne[5D[K
kernel approach that handles the specific shapes optimally.

Since I need to output a complete modified submission.py, and the user ment[4D[K
mentions that load_inline HIP kernels compile and run, I should write a cus[3D[K
custom kernel that:
1. Uses MFMA 32x32x64 for FP4 computation
2. Implements shape-specialized dispatch (different configs for d_expert=25[11D[K
d_expert=256 vs 512 vs 2048)
3. Uses vectorized loads (128-bit)
4. Implements XCD-aware scheduling

But wait, the user says "aiter API parameters (KSPLIT, block_size) are EXHA[4D[K
EXHAUSTED", meaning we've already tried tuning those. So we need a differen[8D[K
different approach.

The most impactful optimization would be to write a custom HIP kernel that [K
handles the small M cases (M=4, 16, etc.) efficiently, since the shapes inc[3D[K
include bs=16 with topk=8 giving very small M per expert.

For MI355X (gfx950, CDNA4), we have:
- 304 CUs, 8 XCDs
- MFMA 32x32x64 intrinsic for FP4
- Need to handle FP4 format (4-bit weights)

Given the shapes:
- d_expert=256: This is very small K. We want no split, and we want to proc[4D[K
process multiple tokens per wavefront.
- d_expert=512: Medium K
- d_expert=2048: Large K

The key insight is that for small batch sizes (bs=16) with topk=8, we have [K
very few tokens per expert. We need to parallelize across experts efficient[9D[K
efficiently.

Since I need to provide a complete submission.py, and the user wants me to [K
"Propose ONE specific optimization", I should focus on the most impactful o[1D[K
one. Given the mention of "Multi-tile output (32x128) for A data reuse" and[3D[K
and "Shape-specialized dispatch", I think the best approach is to write a c[1D[K
custom kernel that:
1. Uses shape-specific tile sizes (e.g., 32x128 for output)
2. Uses vectorized 128-bit loads
3. Implements proper XCD mapping for the 8 XCDs

However, writing a full HIP kernel from scratch is complex. Given the const[5D[K
constraints, I'll implement a solution that uses `aiter` but with custom tu[2D[K
tuning for each shape, potentially using the `fused_moe` with specific bloc[4D[K
block sizes set via environment variables or by selecting different code pa[2D[K
paths.

But the user said KSPLIT and block_size are exhausted. So I need to look at[2D[K
at other optimizations.

Actually, looking at the problem again, the user mentions "load_inline HIP [K
kernels". This suggests I can write inline HIP code. But the interface expe[4D[K
expects me to return output from `custom_kernel`, and the current code uses[4D[K
uses `fused_moe`.

Wait, I can use `aiter` but with custom pre-processing or post-processing, [K
or I can implement a custom kernel using `torch.utils.cpp_extension.load_in[34D[K
`torch.utils.cpp_extension.load_inline` or similar.

Given the complexity of writing a correct MoE kernel with FP4 support from [K
scratch, and the fact that MFMA 32x32x64 is verified working, I should prob[4D[K
probably focus on "Shape-specialized dispatch" with "Vectorized 128-bit glo[3D[K
global loads" and "XCD-aware scheduling".

But actually, looking at the current best being 70.5µs and we're at 154µs, [K
we need almost 2x speedup. This likely requires a fundamental change in how[3D[K
how the kernel is launched.

The key insight for MI355X (CDNA4) with MoE:
1. For small M (bs=16, topk=8, n_routed=256), we have M=128 total tokens bu[2D[K
but spread across 256 experts, so ~0.5 tokens per expert. This is extremely[9D[K
extremely sparse.
2. We need to parallelize across experts, not just within experts.
3. For d_expert=256 with K=256, this is a tiny GEMM (e.g., 0.5x256 or 4x256[5D[K
4x256).

The optimization should be to implement a "batched" approach where we proce[5D[K
process multiple small GEMMs efficiently using a single kernel that handles[7D[K
handles the routing.

Given the constraints, I'll write a submission that:
1. Detects the shape
2. Sets up environment variables for optimal XCD distribution (8 XCDs on MI[2D[K
MI355X)
3. Uses shape-specific configurations
4. Potentially uses custom CUDA/HIP streams or launch parameters

But wait, the user wants "ONE specific optimization". Looking at the list:
1. LDS double-buffering - hard to do without custom kernel
2. Multi-tile output (32x128) - kernel level
3. Vectorized 128-bit global loads - can help with memory bandwidth
4. XCD-aware scheduling - important for MI355X with 8 XCDs
5. Shape-specialized dispatch - high level optimization

Given that we need to output a complete submission.py, and the current one [K
uses `fused_moe`, the most practical optimization that could give significa[9D[K
significant speedup is "Shape-specialized dispatch" combined with "XCD-awar[9D[K
"XCD-aware scheduling".

For MI355X (8 XCDs), we need to ensure work is distributed across XCDs prop[4D[K
properly. The environment variable `HIP_VISIBLE_DEVICES` won't help, but we[2D[K
we can set thread block sizes and grid sizes to map well to XCDs.

Actually, looking at the aiter documentation or similar AMD libraries, ther[4D[K
there might be environment variables for block size. But the user said KSPL[4D[K
KSPLIT and block_size are exhausted.

Let me reconsider. The user mentions "load_inline HIP kernels COMPILE AND R[1D[K
RUN on the runner". This means I can write a custom HIP kernel using `torch[6D[K
`torch.utils.cpp_extension.load_inline`.

Given the shapes, I should write a kernel that:
- For d_expert=256: Uses very small tiles, processes multiple experts per b[1D[K
block
- For d_expert=2048: Uses larger tiles
- Uses vectorized loads (float4 or similar)
- Uses MFMA 32x32x64 for the math

But writing a full MoE kernel with FP4 support is quite involved. However, [K
I can write a wrapper that calls fused_moe with specific parameters based o[1D[K
on shapes, and potentially add custom pre-processing.

Actually, looking at the gap (154µs to 70µs), and the fact that rank 1 achi[4D[K
achieved 70.5µs, they likely used a custom kernel or heavily optimized the [K
dispatch.

Given the instruction "Propose ONE specific optimization", I should focus o[1D[K
on "Shape-specialized dispatch with XCD-aware work distribution".

For MI355X with 8 XCDs and 304 CUs, each XCD has ~38 CUs. We want to ensure[6D[K
ensure that for small batches, we distribute work across all XCDs to maximi[6D[K
maximize memory bandwidth.

The optimization I will implement:
- Detect the specific shape (d_expert, bs)
- For small d_expert (256), use a configuration that maximizes occupancy an[2D[K
and XCD utilization by processing multiple experts per CU/XCD
- Set environment variables to tune the XCD scheduling (like `GPU_MAX_ALLOC[14D[K
`GPU_MAX_ALLOC_PERCENT` or similar, but more likely specific to aiter)
- Use the shuffled weights format correctly

Wait, I see in the input data there are `gate_up_weight_shuffled` and `down[5D[K
`down_weight_shuffled` being used. The comment mentions B_shuffle is CK-spe[6D[K
CK-specific format.

Given the complexity, and since I need to output working code, I'll impleme[7D[K
implement a shape-specialized dispatch that selects optimal grid dimensions[10D[K
dimensions for each case, potentially using `torch.cuda` or `torch.hip` str[3D[K
streams, but more likely by setting specific environment variables or by ca[2D[K
calling `fused_moe` with expert_mask or other parameters that affect parall[6D[K
parallelism.

Actually, the most likely optimization that gives 2x speedup on small GEMMs[5D[K
GEMMs is using a different algorithm entirely: instead of processing each e[1D[K
expert separately, use a "grouped GEMM" approach or a batched GEMM that pro[3D[K
processes multiple experts together to improve GPU utilization.

But I see `fused_moe` already does this internally.

Let me look at the specific optimization hints again:
- "Multi-tile output (32x128) for A data reuse" - this suggests loading A ([1D[K
(activations) once and reusing for multiple tiles of B (weights)
- For MoE with small M, we want to load the weight matrix B and compute mul[3D[K
multiple tokens against it.

Given that I must provide a complete submission.py, and I cannot easily wri[3D[K
write a full custom HIP kernel that handles FP4 MFMA correctly without exte[4D[K
extensive testing, I will implement the "Shape-specialized dispatch" optimi[6D[K
optimization with specific attention to:
1. Setting the number of XCDs properly (8 for MI355X)
2. Using different KSPLIT values based on shape (already doing this, but ma[2D[K
maybe improve)
3. Ensuring vectorized loads by ensuring tensor alignment

But the user said KSPLIT is exhausted.

Another idea: The current code uses `doweight_stage1=False`. Maybe setting [K
it to True for certain shapes helps? Or using different activation types?

Or maybe the optimization is to use `expert_mask` to filter out empty exper[5D[K
experts efficiently for the sparse case?

For bs=16, topk=8, n_routed=256: 128 tokens total, 256 experts → many exper[5D[K
experts have 0 tokens. The current `fused_moe` might be iterating over all [K
experts. An optimization would be to create an expert_mask or use the topk_[5D[K
topk_ids to only launch kernels for experts that have work.

But `fused_moe` likely already handles this.

Given the constraints and the target, I think the best approach is to imple[5D[K
implement a custom kernel using `load_inline` that handles the specific cas[3D[K
case of small M (bs=16) efficiently by using a different thread block confi[5D[K
configuration.

However, since I cannot test the code, and writing a correct FP4 MFMA kerne[5D[K
kernel from scratch is risky, I will instead focus on the "XCD-aware schedu[6D[K
scheduling" by setting environment variables that control the GPU behavior [K
on MI355X.

Actually, looking at AMD documentation, for CDNA4, we might want to set `HI[3D[K
`HIP_VISIBLE_DEVICES` or similar, but that's not it.

There's `AMD_LOG_LEVEL`, `GPU_WORKGROUP_SIZE`, etc.

But the most impactful for MI355X specifically (8 XCDs) is to ensure the ke[2D[K
kernel launch grid is a multiple of 8 to distribute work evenly across XCDs[4D[K
XCDs.

I will implement a shape-aware grid configuration by setting environment va[2D[K
variables like `AITER_BLOCK_SIZE` or similar, or by manipulating the input [K
tensors to ensure coalesced access.

Wait, the user said: "aiter API parameters (KSPLIT, block_size) are EXHAUST[7D[K
EXHAUSTED". This means I cannot get more speedup by tuning those parameters[10D[K
parameters.

So I need to do something else. The "load_inline HIP kernels" is the key. I[1D[K
I should write a custom kernel that pre-processes the data or replaces fuse[4D[K
fused_moe for certain shapes.

Given the time, I will write a submission that:
1. Detects if we are in the "tiny GEMM" case (d_expert=256)
2. For that case, uses a custom inline HIP kernel that is optimized for ver[3D[K
very small K (256) and small M
3. The kernel will use vectorized loads and process multiple experts per bl[2D[K
block

But to be safe and provide a working solution, I'll implement the shape-spe[9D[K
shape-specialized dispatch with specific optimizations for the data layout,[7D[K
layout, ensuring we use the shuffled weights correctly and potentially reor[4D[K
reordering the computation to improve L2 cache locality.

Actually, looking at the rank 1 time of 70.5µs vs our 154.2µs, and knowing [K
that MI355X is a powerful GPU, the issue is likely that for small M, the ov[2D[K
overhead of launching kernels for each expert is too high, or we're not usi[3D[K
using the XCDs efficiently.

The optimization: Use `torch.utils.cpp_extension.load_inline` to compile a [K
custom kernel that fuses the routing and GEMM for small experts, using a pe[2D[K
persistent kernel across XCDs.

But I realize I don't have the exact API for `fused_moe` internal details.

Let me try a different approach. The user mentions "MFMA 32x32x64 FP4 intri[5D[K
intrinsic" and "B_q is standard FP4 packed, B_shuffle is CK-specific format[6D[K
format". This suggests that the optimal code uses the shuffled format for w[1D[K
weights.

The current code already uses `gate_up_weight_shuffled` and `down_weight_sh[15D[K
`down_weight_shuffled`. 

The optimization could be: For small d_expert (256), pack multiple experts'[8D[K
experts' weights together and process them in a single GEMM call to increas[7D[K
increase K dimension effectively.

For example, for d_expert=256, instead of doing Mx256 for each expert, we c[1D[K
could group 8 experts together and do Mx(256*8) = Mx2048, but that's not ri[2D[K
right because each token only goes to specific experts.

Actually, we can process multiple experts' tokens in the same wavefront if [K
we organize the data correctly.

Given the difficulty of writing a correct custom kernel without testing, an[2D[K
and the need for a complete submission.py file, I will implement the "Shape[6D[K
"Shape-specialized dispatch" with specific environment tuning for XCD aware[5D[K
awareness (8 XCDs on MI355X) and ensuring we use the FP4 MFMA correctly by [K
setting the appropriate quant_type and ensuring the weights are in the righ[4D[K
right format.

But the current code already does this.

Another thought: The `intermediate_pad` and `hidden_pad` might be set incor[5D[K
incorrectly for some shapes. We should calculate optimal padding based on t[1D[K
the specific shape.

Or, we could implement a custom sorting of experts to ensure coalesced acce[4D[K
access.

Given the "ONE specific optimization" constraint, I will focus on: **Shape-[8D[K
**Shape-specialized XCD-aware dispatch with vectorized loads**.

This means:
- For each shape (d_expert, bs), we calculate the optimal number of CUs to [K
use and how to distribute across 8 XCDs
- We set `os.environ` variables to control the thread block size (even thou[4D[K
though the user said block_size is exhausted, maybe there are other env var[3D[K
vars)
- We ensure tensor alignment for 128-bit loads

Actually, looking carefully at the prompt, it says "aiter API parameters (K[2D[K
(KSPLIT, block_size) are EXHAUSTED". This might mean we cannot use those sp[2D[K
specific parameters, but we can use other methods.

I think the best bet is to write a custom kernel using `load_inline` that i[1D[K
implements a specialized path for the small d_expert=256 case, which is the[3D[K
the most challenging due to the tiny K.

For d_expert=256, K=256 is small. We want to use a tile size of 32x256 or s[1D[K
similar, and process multiple M's in parallel.

But without being able to test, I'll provide a solution that uses the `fuse[5D[K
`fused_moe` but with optimized `expert_mask` calculation and ensuring we us[2D[K
use the `doweight_stage1` flag correctly for different shapes.

After reconsideration, the most practical optimization that is likely to wo[2D[K
work is:

**Implement XCD-aware expert scheduling**: Ensure that for small batches, w[1D[K
we distribute experts across the 8 XCDs (38 CUs each) evenly to maximize pa[2D[K
parallelism and memory bandwidth.

This can be done by:
1. Calculating how many experts have tokens (active experts)
2. Setting the grid launch size to be a multiple of 8
3. Using `os.environ` to set AMD GPU scheduling hints

But I don't know the exact env var names.

Another idea: Use `torch.compile` or `torch.jit`? Probably not for HIP.

Given the hints about "LDS double-buffering" and "Multi-tile output", these[5D[K
these are kernel-level optimizations. Since I cannot easily modify the inte[4D[K
internals of `fused_moe`, but I can write a custom kernel, I will write a s[1D[K
simple custom kernel that handles the case where d_expert=256 specifically,[13D[K
specifically, using inline HIP assembly or C++.

However, to ensure the code compiles and runs, I will make it call `fused_m[8D[K
`fused_moe` for the general case but with shape-specific optimizations, and[3D[K
and for the specific case of d_expert=256 with small bs, I will use a custo[5D[K
custom kernel if possible, or just optimized parameters.

Given the time I've spent analyzing, I will provide a solution that focuses[7D[K
focuses on **Shape-specialized dispatch with XCD-aware grid configuration a[1D[K
and enforced vectorized memory access (128-bit)**.

The code will:
1. Detect the shape (d_expert, bs)
2. Calculate optimal