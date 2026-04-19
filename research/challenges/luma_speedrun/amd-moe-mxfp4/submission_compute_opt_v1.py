Thinking...
We are given a problem: we need to optimize a MoE kernel for AMD MI355X. Th[2D[K
The current submission uses aiter.fused_moe() with AITER_USE_NT=1 and achie[5D[K
achieves 154µs. The target is <110µs and the leader is at 70µs.

We are told that only GPU compute improvements help, and Python dispatch op[2D[K
optimizations hurt on the ranked runner (it caches JIT and reuses tensors).[9D[K
tensors). Therefore, we must focus on improving the GPU kernel performance.[12D[K
performance.

The suggested approaches are:
1. Using a completely different aiter API that runs faster GPU kernels.
2. Finding aiter APIs we haven't tried: fmoe_fp8_blockscale_g1u1, fmoe_g1u1[9D[K
fmoe_g1u1_a16, asm_moe.
3. Reducing the number of GPU kernel launches (fuse sorting + GEMM).
4. Using load_inline to write a custom MoE kernel with MFMA intrinsics.

The current code uses a shape-aware KSPLIT strategy for the ranked shapes.

We note that the current code uses the `fused_moe` function from `aiter.fus[10D[K
`aiter.fused_moe`. We are to explore other APIs or write a custom kernel.

Let's consider the available APIs in the aiter library for MoE. We are give[4D[K
given three specific ones to try: `fmoe_fp8_blockscale_g1u1`, `fmoe_g1u1_a1[13D[K
`fmoe_g1u1_a16`, and `asm_moe`. We should check if these are available in t[1D[K
the aiter module and try them.

Alternatively, we can write a custom kernel using load_inline. However, wri[3D[K
writing a custom MoE kernel with MFMA intrinsics is complex and time-consum[11D[K
time-consuming. We might try the other APIs first.

Let's assume we have access to these functions. We note that the current co[2D[K
code uses `QuantType.per_1x32` and `ActivationType.Silu`. We must ensure th[2D[K
that the alternative APIs support the same quantization and activation.

We are also told that the runner caches JIT and reuses tensors, so we canno[5D[K
cannot rely on changing the environment variables (like AITER_KSPLIT) betwe[5D[K
between runs? But note that the current code sets AITER_KSPLIT based on d_e[3D[K
d_expert. However, the problem says Python dispatch optimizations hurt, mea[3D[K
meaning that any Python-level logic (like setting environment variables) is[2D[K
is already optimized away by the runner. So we must focus on the GPU kernel[6D[K
kernel.

Let's try the following:

1. Try using `fmoe_fp8_blockscale_g1u1` if it is available and if it suppor[6D[K
supports the same quantization (per_1x32) and activation (SiLU). However, n[1D[K
note that the function name suggests it uses FP8 and blockscale, which migh[4D[K
might not match our data (which is MXFP4). We must check the documentation [K
or function signature.

2. Try using `fmoe_g1u1_a16` which might be a version that uses A16 (16-bit[7D[K
(16-bit activations) and group size 1 for the experts. Again, we need to ch[2D[K
check if it supports the quantization type.

3. Try using `asm_moe` which might be an assembly-optimized kernel.

Given the time, let's try to replace the call to `fused_moe` with one of th[2D[K
these functions, if available, and see if it improves performance.

However, note that the problem says we are in a ranked runner, and the code[4D[K
code is being evaluated. We must write a solution that uses one of these ap[2D[K
approaches.

Since we don't have the exact documentation for these functions, we have to[2D[K
to make an educated guess.

Alternatively, we can try to reduce the number of kernel launches by using [K
a different API that fuses more operations.

Another idea: the current code uses `doweight_stage1=False`. Setting it to [K
True might change the kernel launch pattern, but note that the runner might[5D[K
might have optimized for the current setting.

Given the above, let's try to use `asm_moe` if it is available, because it [K
might be the most optimized kernel.

We'll change the function call to use `asm_moe` and adjust the parameters a[1D[K
accordingly.

But first, let's check the current aiter module to see what functions are a[1D[K
available. Since we don't have the module in this environment, we have to r[1D[K
rely on the problem statement.

We are given three function names: `fmoe_fp8_blockscale_g1u1`, `fmoe_g1u1_a[12D[K
`fmoe_g1u1_a16`, and `asm_moe`. We assume they are in the `aiter` module.

Let's try to import and use `asm_moe` if available, otherwise fall back to [K
`fused_moe`.

We'll write the code as follows:

```python
#!POPCORN leaderboard amd-moe-mxfp4
#!POPCORN gpu MI355X

"""M2: Shape-aware KSPLIT for ranked shapes.

Ranked shapes:
  d_expert=256, n_routed=256, bs=16/128/512  (3 shapes — tiny GEMMs!)
  d_expert=512, n_routed=32, bs=16/128/512   (3 shapes)
  d_expert=2048, n_routed=32, bs=512         (1 shape)

For d_expert=256: K=256 is very small. KSPLIT should be 0 (no split)
because splitting tiny K adds overhead.
For d_expert=2048: K=2048 is medium. KSPLIT=1 might help.

Also: for 256 experts with bs=16 and topk=8, only 128 tokens total
routed to 256 experts → ~0.5 tokens/expert. Very sparse!
"""

from __future__ import annotations
import os

os.environ["AITER_USE_NT"] = "1"

import torch
from aiter import ActivationType, QuantType
from aiter.fused_moe import fused_moe
from task import input_t, output_t

# Try to import asm_moe if available
try:
    from aiter.asm_moe import asm_moe
    USE_ASM_MOE = True
except ImportError:
    USE_ASM_MOE = False

def custom_kernel(data: input_t) -> output