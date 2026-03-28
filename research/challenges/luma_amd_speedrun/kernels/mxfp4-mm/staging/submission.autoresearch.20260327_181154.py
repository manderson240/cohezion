import torch
import aiter
from aiter import QuantType
from task import input_t, output_t


SCALE_GROUP_SIZE = 32


def custom_kernel(data: input_t) -> output_t:
    """
    Optimized MXFP4 GEMM kernel for AMD MI355X (gfx950).
    Minimizes geomean latency across 6 shapes using fused quant+GEMM strategy.
    """
    A, B, B_q, B_shuffle, B_scale_sh = data
    m, k = A.shape
    n, _ = B.shape

    # Ensure contiguous memory layout
    A = A.contiguous()
    B = B.contiguous()

    # 1) Quantize A with per-1x32 MXFP4 (same as B) - minimal overhead
    quant_func = aiter.get_triton_quant(QuantType.per_1x32)
    A_q, A_scale = quant_func(A, shuffle=False)

    # 2) Use gemm_a4w4 with pre-shuffled B for optimal memory access pattern
    #    gemm_a4w4 expects:
    #    - A_q: [m, k//2] fp4x2
    #    - B_q: [n, k//2] fp4x2 (shuffled layout)
    #    - A_scale: [m, k//32] e8m0
    #    - B_scale: [n, k//32] e8m0
    #    - out_dtype: bf16
    C = aiter.gemm_a4w4(
        A_q,
        B_shuffle,
        A_scale,
        B_scale_sh,
        out_dtype=torch.bfloat16,
    )

    # Ensure output shape correctness
    assert C.shape == (m, n), f"Expected shape ({m}, {n}), got {C.shape}"
    return C