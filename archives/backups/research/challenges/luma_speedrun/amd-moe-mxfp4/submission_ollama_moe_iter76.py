#!POPCORN leaderboard amd-moe-mxfp4
#!POPCORN gpu MI355X

Thinking...
The user wants me to optimize an AMD MI355X GPU kernel for MoE (Mixture of [K
Experts) operations. The current submission is at 154.2µs and needs to get [K
below 110µs, with the best at 70.5µs.

Key observations from the prompt:
1. The current approach uses AITER's fused_moe with environment variable KS[2D[K
KSPLIT tuning
2. The shapes are:
   - d_expert=256, n_routed=256, bs=16/128/512 (tiny GEMMs, K=256)
   - d_expert=512, n_routed=32, bs=16/128/512 (medium, K=512)
   - d_expert=2048, n_routed=32, bs=512 (large, K=2048)
3. Very sparse scenarios: 256 experts with bs=16 and topk=8 means only ~0.5[4D[K
~0.5 tokens/expert

The prompt mentions:
- MFMA 32x32x64 FP4 intrinsic is working
- B_q is standard FP4 packed, B_shuffle is CK-specific format
- Need to propose ONE specific optimization from the list:
  1. LDS double-buffering for coalesced memory access
  2. Multi-tile output (32x128) for A data reuse
  3. Vectorized 128-bit global loads
  4. XCD-aware scheduling with __builtin_amdgcn_s_setprio
  5. Shape-specialized dispatch (different tile sizes for M=4 vs M=256)

Given the shapes, especially the tiny M values (bs=16 with topk=8 means M c[1D[K
can be very small, like M=16*8/256=0.5 average, but actually M is the token[5D[K
token count per expert which varies), the biggest issue is likely:
- For small M (like M=4 or M=16), we need different tile sizes
- For tiny GEMMs (K=256, M small), standard tiling is inefficient

The user wants me to output ONLY the complete modified submission.py file. [K
But wait, the current submission uses `fused_moe` from aiter library. To im[2D[K
implement low-level optimizations like LDS double-buffering, multi-tile out[3D[K
output, vectorized loads, or XCD-aware scheduling, I would need to write cu[2D[K
custom HIP kernels.

However, the prompt says: "load_inline HIP kernels COMPILE AND RUN on the r[1D[K
runner". This suggests I can write custom inline HIP code.

But looking at the current code, it uses `from aiter.fused_moe import fused[5D[K
fused_moe`. To implement the optimizations mentioned (especially LDS double[6D[K
double-buffering, multi-tile, vectorized loads), I likely need to write a c[1D[K
custom kernel using `aiter.load_inline` or similar.

Wait, the prompt says: "aiter API parameters (KSPLIT, block_size) are EXHAU[5D[K
EXHAUSTED". This means tuning existing parameters won't help. I need to wri[3D[K
write a custom kernel.

The prompt mentions: "MFMA 32x32x64 FP4 intrinsic is VERIFIED working". Thi[3D[K
This suggests using inline assembly or HIP intrinsics for matrix multiplica[10D[K
multiplication.

Given the shapes:
- d_expert=256 (K=256): Very small K, M can be tiny (0.5 to 16 tokens)
- d_expert=512 (K=512): Small K
- d_expert=2048 (K=2048): Medium K, but bs=512

The most impactful optimization for these tiny GEMMs would be:
1. Shape-specialized dispatch - using different tile configurations for dif[3D[K
different M sizes (M=4 vs M=256)
2. For tiny M (like M<=16), we should use small tiles or even direct vector[6D[K
vectorized loads
3. For the d_expert=256 case with very sparse routing, standard GEMM is ine[3D[K
inefficient

Actually, looking at the hint list, option 5 "Shape-specialized dispatch (d[2D[K
(different tile sizes for M=4 vs M=256)" seems most relevant for handling t[1D[K
the extreme sparsity (0.5 tokens/expert).

But wait, the user wants me to implement ONE specific optimization. Given t[1D[K
that the current best is 70.5µs and current is 154.2µs, I need a substantia[10D[K
substantial optimization.

Let me think about what would work best for MI355X (gfx950, CDNA4):
- CDNA4 has 304 CUs across 8 XCDs
- MFMA 32x32x64 for FP4 means we can do 32x32 tiles with 64 accumulators
- For tiny M and K, we need to minimize overhead

Actually, the most practical approach given the constraints is to implement[9D[K
implement a custom kernel using `aiter.load_inline` (which is a common patt[4D[K
pattern in these competitions) that:
1. Detects the shape
2. Uses specialized code paths

But I need to be careful. The prompt says the current submission uses `fuse[5D[K
`fused_moe`. If I'm to propose a custom kernel, I need to replace that call[4D[K
call.

However, looking at the problem description again, the user says "Propose O[1D[K
ONE specific optimization to try" and lists 5 options. I should pick one of[2D[K
of those 5.

Given the tiny GEMM nature (K=256, M very small), the most impactful would [K
be:
- Shape-specialized dispatch: Use different tile sizes or even different al[2D[K
algorithms for different shapes
- For M <= 16 and small K, we might want to use a different approach than s[1D[K
standard tiling

But actually, for MI355X and the specific shapes mentioned, I should consid[6D[K
consider:
- XCD-aware scheduling (option 4): Since there are 8 XCDs and we have many [K
small GEMMs, distributing work across XCDs efficiently matters
- Multi-tile output (option 2): For reusing A matrix data when M is very sm[2D[K
small but we have many experts

Wait, I need to look at what the Popcorn CLI format expects. The user wants[5D[K
wants ONLY the complete modified submission.py file.

Given that the user mentioned "load_inline HIP kernels COMPILE AND RUN", I [K
should write a custom kernel. But I need to make sure it compiles.

Let me think about the specific optimization. The current bottleneck is lik[3D[K
likely:
1. For d_expert=256: K=256 is too small for standard MFMA efficiency, and M[1D[K
M is tiny (0.5-2 tokens per expert on average)
2. The standard fused_moe might not be optimized for these tiny sizes

The optimization I should implement is **Shape-specialized dispatch with cu[2D[K
custom tiny GEMM kernels for small M and K**.

Specifically:
- For d_expert=256 (K=256): Use a specialized kernel with smaller tiles or [K
even direct computation without complex tiling
- For different batch sizes: Use different configurations

But actually, looking at the list again, option 1 (LDS double-buffering) is[2D[K
is good for hiding latency, option 2 (Multi-tile output) helps with data re[2D[K
reuse, option 3 (Vectorized loads) is basic, option 4 (XCD-aware scheduling[10D[K
scheduling) helps with 8 XCDs, option 5 (Shape-specialized dispatch) is hig[3D[K
high-level.

Given the sparsity (0.5 tokens/expert), the issue is that we have many tiny[4D[K
tiny GEMMs. The standard approach launches one GEMM per expert or uses grou[4D[K
grouped GEMM. With only 0.5 tokens per expert on average for the first case[4D[K
case, we need extreme specialization.

I think the best approach is **Shape-specialized dispatch (option 5)** comb[4D[K
combined with **vectorized loads (option 3)** for the tiny cases.

But I need to output a complete submission.py. Since the current code uses [K
`fused_moe`, and I want to use custom inline kernels, I should check if I c[1D[K
can use `aiter.load_inline`.

Actually, looking at typical Popcorn solutions for AMD GPUs, they often use[3D[K
use `torch_custom_op` or `aiter.load_inline` to load HIP code.

Let me draft a solution that:
1. Uses shape-specialized dispatch
2. For small d_expert (256) and small batch sizes, uses a custom kernel wit[3D[K
with vectorized loads and optimized for tiny M
3. For larger d_expert, uses standard fused_moe or a different configuratio[12D[K
configuration

But wait, the user says "aiter API parameters (KSPLIT, block_size) are EXHA[4D[K
EXHAUSTED". This suggests that further tuning of the existing API won't hel[3D[K
help, so I need a custom implementation.

Let me propose a solution that implements **LDS double-buffering with shape[5D[K
shape-specialized dispatch** for the tiny GEMM cases.

Actually, for MI355X and the specific problem of tiny GEMMs (M=1-16, K=256,[6D[K
K=256, N=256), the most impactful optimization is to recognize that these a[1D[K
are vector-matrix multiplications and should be treated as such, not as mat[3D[K
matrix-matrix multiplications.

But I need to write this as a complete submission.py file.

Given the complexity of writing a full MFMA-based kernel in a single respon[6D[K
response, and the fact that the user wants it to compile and run, I should [K
use a practical approach:

The optimization I'll implement is **Shape-specialized dispatch with XCD-aw[6D[K
XCD-aware work distribution and vectorized memory access for tiny GEMMs**.

Wait, I should look at what the error tolerance implies. GEMM=1% means I ne[2D[K
need accurate computation.

Let me reconsider. The user wants ONE specific optimization from the list. [K
I should pick the one that gives the most benefit for the specific shapes.

For MI355X with tiny GEMMs:
- Option 4 (XCD-aware scheduling) is important because with 8 XCDs and tiny[4D[K
tiny work items, we need to distribute efficiently
- Option 5 (Shape-specialized dispatch) is essential because M varies from [K
1 to 512
- Option 2 (Multi-tile output) helps reuse A matrix in LDS when M is small

I think Option 5 is the most comprehensive: **Shape-specialized dispatch (d[2D[K
(different tile sizes for M=4 vs M=256)**.

This makes sense because:
- For bs=16 with topk=8 on 256 experts: M per expert is ~0.5, but we batch [K
by expert, so M is tiny (0-2)
- For bs=512: M per expert is ~16
- For bs=512 with d_expert=2048: M=16, K=2048

So I should implement a custom kernel that:
1. Detects M (batch size per expert)
2. For small M (M <= 16): Uses small tiles, maybe M=4 or M=8
3. For larger M: Uses standard tiles

But to actually implement this, I need to write a custom MoE kernel using i[1D[K
inline HIP.

Let me structure the code:

```python
import torch
import aiter
from aiter import ActivationType, QuantType
from task import input_t, output_t
import os

# Define the custom kernel using load_inline
custom_moe_code = '''
#include <torch/extension.h>
#include <hip/hip_runtime.h>
#include <hip/hip_fp16.h>
#include <hip/hip_bf16.h>

// Shape-specialized kernel for tiny GEMMs
template <int BLOCK_M, int BLOCK_K, int BLOCK_N>
__global__ void moe_gemm_tiny_kernel(...) {
    // Implementation with LDS double-buffering and vectorized loads
    // Specialized for small M (4, 8, 16)
}

// Shape-specialized kernel for medium GEMMs
template <int BLOCK_M, int BLOCK_K, int BLOCK_N>
__global__ void moe_gemm_medium_kernel(...) {
    // Standard MFMA-based implementation
}

torch::Tensor custom_fused_moe(...) {
    // Dispatch based on M and K sizes
    if (M <= 16 && K == 256) {
        // Use tiny kernel with BLOCK_M=4, BLOCK_K=64, etc.
    } else if (M <= 64) {
        // Use medium kernel
    } else {
        // Use large kernel
    }
}
'''

def custom_kernel(data: input_t) -> output_t:
    # ... unpack data
    # Call custom kernel instead of fused_moe
```

But writing a full competitive MFMA kernel is complex and might have bugs. [K


Alternative: The user mentions "MFMA 32x32x64 FP4 intrinsic is VERIFIED wor[3D[K
working" and "B_shuffle is CK-specific format". This suggests that the exis[4D[K
existing `fused_moe` might be using these, but I can optimize the dispatch [K
logic