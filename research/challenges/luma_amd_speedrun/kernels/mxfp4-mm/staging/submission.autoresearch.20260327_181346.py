import aiter
from aiter import QuantType
from task import input_t, output_t


SCALE_GROUP_SIZE = 32


def custom_kernel(data: input_t) -> output_t:
    """
    Optimized MXFP4 GEMM for MI355X (gfx950).
    Strategy: Fuse A quantization (per-1x32 MXFP4) with GEMM using gemm_a4w4.
    Avoid extra dequant/requant; keep data in fp4 domain as long as possible.
    """
    A, B, B_q, B_shuffle, B_scale_sh = data
    A = A.contiguous()
    B = B.contiguous()
    m, k = A.shape
    n, _ = B.shape

    # Quantize A in-place to MXFP4 per-1x32 (no shuffle needed for A)
    quant_func = aiter.get_triton_quant(QuantType.per_1x32)
    A_q, A_scale = quant_func(A, shuffle=False)

    # Prepare A_scale: ensure correct layout for gemm_a4w4
    # gemm_a4w4 expects A_scale: [m, k//32], which matches per_1x32 output
    A_scale = A_scale.contiguous()

    # Use gemm_a4w4: A (fp4) x B (fp4, shuffled) -> bf16 C
    # gemm_a4w4 signature: gemm_a4w4(A_q, B_shuffle, A_scale, B_scale, M, N, K, alpha=1.0)
    # Note: B_shuffle already shuffled; B_scale_sh is already shuffled scale
    C = aiter.gemm_a4w4(
        A_q,
        B_shuffle,
        A_scale,
        B_scale_sh,
        m, n, k,
        alpha=1.0
    )

    return C