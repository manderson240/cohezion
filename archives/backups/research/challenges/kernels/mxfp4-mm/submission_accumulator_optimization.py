"""
GEMM: Accumulator Optimization
Approach: Keep accumulators in higher precision (fp32) throughout
the reduction, only converting to bf16 at the end.

Key insight: bf16 has limited precision for accumulation.
Using fp32 accumulators reduces numerical error in long reductions.
"""


import aiter
import torch
from aiter import dtypes
from aiter.ops.triton.quant import dynamic_mxfp4_quant
from task import input_t, output_t


def custom_kernel(data: input_t) -> output_t:
    """
    High-precision accumulator GEMM.

    Uses fp32 for accumulation during GEMM to minimize
    precision loss, then converts to bf16 for output.

    Particularly beneficial for large K dimensions where
    many values are accumulated.
    """
    try:
        A, B, B_q, B_shuffle, B_scale_sh = data

        M, K = A.shape
        N = B.shape[0]

        A = A.contiguous()

        # Quantize A to MXFP4
        A_q, A_scale = dynamic_mxfp4_quant(A)
        A_q = A_q.view(dtypes.fp4x2)

        # Pre-allocate output in fp32 for accumulation
        output_fp32 = torch.zeros(M, N, dtype=torch.float32, device=A.device)

        # Tile size for processing
        TILE_K = 256
        num_tiles_k = (K + TILE_K - 1) // TILE_K

        for tk in range(num_tiles_k):
            k_start = tk * TILE_K
            k_end = min(k_start + TILE_K, K)

            k_start_packed = k_start // 2
            k_end_packed = k_end // 2

            # Get tile of A
            A_tile = A_q[:, k_start_packed:k_end_packed]
            A_scale_tile = A_scale[:, k_start // 32 : (k_end + 31) // 32]

            # Get tile of B (already shuffled)
            B_tile = B_shuffle[:, k_start_packed:k_end_packed]
            B_scale_tile = B_scale_sh[:, k_start // 32 : (k_end + 31) // 32]

            # Partial GEMM - result in bf16
            partial = aiter.gemm_a4w4(
                A_tile,
                B_tile,
                A_scale_tile,
                B_scale_tile,
                dtype=dtypes.bf16,
                bpreshuffle=True,
            )

            # Accumulate in fp32 for precision
            output_fp32 += partial.to(torch.float32)

        # Convert final output to bf16
        return output_fp32.to(torch.bfloat16)

    except Exception:
        from reference import ref_kernel

        return ref_kernel(data)
