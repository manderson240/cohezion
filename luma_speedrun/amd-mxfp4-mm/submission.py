"""MXFP4 GEMM submission — optimized for MI355X (gfx950).

Optimizations over reference:
1. Use gemm_a4w4 ASM path (bpreshuffle=True) — 7-10µs vs Triton's 68% slower
2. Pre-shuffled B weights from generate_input (skip shuffle_weight)
3. Fused quant+shuffle: dynamic_mxfp4_quant + e8m0_shuffle in minimal ops
4. Contiguous A ensured once (reference calls it too, but we're explicit)

Current: ~13.4µs | Leader: ~4.3µs | Gap: 3.1x
Bottleneck: quantization dispatch (~26-84µs) exceeds GEMM compute (~7-10µs)

The only path to beating the API ceiling is fusing quant into the GEMM kernel,
which requires custom HIP compilation (blocked by runner source scanning).
"""

import aiter
from aiter import dtypes
from aiter.ops.triton.quant import dynamic_mxfp4_quant
from aiter.utility.fp4_utils import e8m0_shuffle
from task import input_t, output_t


def custom_kernel(data: input_t) -> output_t:
    A, B, B_q, B_shuffle, B_scale_sh = data
    # Quantize A to MXFP4 with shuffled E8M0 scales
    A_q, A_scale_e8m0 = dynamic_mxfp4_quant(A.contiguous())
    A_scale_sh = e8m0_shuffle(A_scale_e8m0).view(dtypes.fp8_e8m0)
    A_q = A_q.view(dtypes.fp4x2)
    # ASM GEMM — uses pre-compiled .co kernels on MI355X
    return aiter.gemm_a4w4(
        A_q, B_shuffle, A_scale_sh, B_scale_sh,
        dtype=dtypes.bf16, bpreshuffle=True,
    )
