import aiter
from aiter import QuantType
from task import input_t, output_t


SCALE_GROUP_SIZE = 32


def custom_kernel(data: input_t) -> output_t:
    """
    Optimized GEMM for MXFP4 weights using aiter's gemm_a4w4 with 192x128 tile.
    Strategy: For M > 32, use gen_gemm_a4w4 with 192x128 tile (confirmed 4/4 pass).
    """
    A, B, B_q, B_shuffle, B_scale_sh = data

    # Ensure contiguous memory layout
    A = A.contiguous()
    B = B.contiguous()

    m, k = A.shape
    n, _ = B.shape

    # Quantize A using same MXFP4 per-1x32 quantization as reference
    quant_func = aiter.get_triton_quant(QuantType.per_1x32)
    A_q, A_scale = quant_func(A, shuffle=False)

    # Use gemm_a4w4 with 192x128 tile for M > 32
    if m > 32:
        # Use the optimized 192x128 tile kernel
        C = aiter.gemm_a4w4(
            A_q, B_shuffle, A_scale, B_scale_sh,
            m=m, n=n, k=k,
            tile_m=192, tile_n=128
        )
    else:
        # Fallback to default tile for small M
        C = aiter.gemm_a4w4(
            A_q, B_shuffle, A_scale, B_scale_sh,
            m=m, n=n, k=k
        )

    return C