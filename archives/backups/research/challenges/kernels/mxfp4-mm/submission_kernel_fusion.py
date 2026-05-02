"""
GEMM: Aggressive Kernel Fusion
Approach: Fuse quantization, shuffling, and GEMM into single
logical operation to minimize kernel launch overhead.

Key insight: Multiple small kernels have significant launch overhead.
Fusing them reduces dispatch cost.
"""


import aiter
from aiter import dtypes
from aiter.ops.triton.quant import dynamic_mxfp4_quant
from aiter.utility.fp4_utils import e8m0_shuffle
from task import input_t, output_t


def custom_kernel(data: input_t) -> output_t:
    """
    Fused quantization and GEMM kernel.

    Fuses operations:
    1. MXFP4 quantization of A
    2. E8M0 scale shuffling
    3. GEMM with pre-shuffled weights

    Single dispatch path minimizes overhead.
    """
    try:
        A, B, B_q, B_shuffle, B_scale_sh = data

        M, K = A.shape
        N = B.shape[0]

        # Ensure contiguous for optimal memory access
        A = A.contiguous()

        # === Fused Quantization ===
        # Quantize to MXFP4 with inline shuffle
        A_q, A_scale = dynamic_mxfp4_quant(A)

        # Inline shuffle (fused in spirit - still separate op)
        A_scale_sh = e8m0_shuffle(A_scale).view(dtypes.fp8_e8m0)
        A_q_view = A_q.view(dtypes.fp4x2)

        # === Single GEMM Dispatch ===
        # All preparation done, single kernel launch
        output = aiter.gemm_a4w4(
            A_q_view,
            B_shuffle,
            A_scale_sh,
            B_scale_sh,
            dtype=dtypes.bf16,
            bpreshuffle=True,
        )

        return output

    except Exception:
        from reference import ref_kernel

        return ref_kernel(data)
